#include "deployment_handle.h"

#include <grpcpp/create_channel.h>

#include "src/generated/replica_service.grpc.pb.h"
#include "src/generated/replica_service.pb.h"

#include <print>
#include <unordered_set>

DeploymentHandle::DeploymentHandle(
    agrpc::GrpcContext& grpc_context,
    const protos::DeploymentInfoMessage& deployment_info)
    : grpc_context_(grpc_context),
      deployment_id_(std::to_string(deployment_info.deployment_id())),
      deployment_name_(deployment_info.deployment_name()) {
    add_replicas(deployment_info);
}

void DeploymentHandle::add_replicas(
    const protos::DeploymentInfoMessage& deployment_info) {
    std::lock_guard<std::mutex> lock(mtx_);
    for (const auto& replica_proto : deployment_info.replicas()) {
        auto replica_info = std::make_shared<ReplicaInfo>(ReplicaInfo{
            .replica_id = replica_proto.replica_id(),
            .address = replica_proto.address(),
            .state = replica_proto.state(),
            .active_requests = 0});
        replicas_.push_back(replica_info);
        channel_cache_[replica_proto.replica_id()] = grpc::CreateChannel(
                replica_proto.address(), grpc::InsecureChannelCredentials());
            
    }
}

std::optional<ReplicaConnection> DeploymentHandle::pick_next_replica() {
    std::lock_guard<std::mutex> lock(mtx_);
    const auto now =std::chrono::steady_clock::now();
    std::shared_ptr<ReplicaInfo> least_loaded = nullptr;
    for(auto& replica:replicas_)
    {
        if(replica->health_status == ReplicaInfo::Health::Unhealthy && now - replica->last_failure_time > std::chrono::seconds(15))    
            replica->health_status = ReplicaInfo::Health::Healthy;
        if(replica->health_status == ReplicaInfo::Health::Healthy)
        {
            if(least_loaded == nullptr || replica->active_requests < least_loaded->active_requests)
                least_loaded = replica;
        }
    }
    if(least_loaded == nullptr)
        return std::nullopt;
    least_loaded->active_requests++;
    auto channel = channel_cache_[least_loaded->replica_id];
    return ReplicaConnection{least_loaded,channel};
}



void DeploymentHandle::mark_replica_unhealthy(const std::string& replica_id) {
    std::lock_guard<std::mutex> lock(mtx_);
    for(auto replica:replicas_)
    {
        if(replica->replica_id == replica_id)
        {
            replica->health_status = ReplicaInfo::Health::Unhealthy;
            replica->last_failure_time = std::chrono::steady_clock::now();
            break;
        }
    }
}
asio::awaitable<void> DeploymentHandle::send_request(
    std::string message,
    std::function<asio::awaitable<void>(
        std::expected<std::string, grpc::Status>)> on_token) {
    auto connection_opt = pick_next_replica();
    if (!connection_opt) {
        co_await on_token(std::unexpected(grpc::Status(grpc::StatusCode::UNAVAILABLE, "No replicas available")));
        co_return;
    }

    ReplicaReleaser releaser{connection_opt->info};
 
    auto stub = protos::WorkerService::NewStub(connection_opt->channel);
 
    protos::ReplicaRequest request;
    request.set_prompt(std::move(message));

        agrpc::ClientRPC<&protos::WorkerService::Stub::PrepareAsyncSendRequest> rpc(grpc_context_);
    rpc.context().set_wait_for_ready(false);
    rpc.context().set_deadline(std::chrono::system_clock::now() +
                                 std::chrono::seconds(120));

    if (!co_await rpc.start(*stub, request, asio::use_awaitable)) {
        mark_replica_unhealthy(connection_opt->info->replica_id);
        grpc::Status status = co_await rpc.finish(asio::use_awaitable);
        co_await on_token(std::unexpected(status));
        co_return;
    }

    protos::ReplicaReply reply;
    while (co_await rpc.read(reply, asio::use_awaitable)) {
        co_await on_token(reply.text());
    }

    grpc::Status status = co_await rpc.finish(asio::use_awaitable);
    if (!status.ok()) {
        // If the stream finishes with an error, the replica is likely unhealthy.
        mark_replica_unhealthy(connection_opt->info->replica_id);
        co_await on_token(std::unexpected(status));
    }
}