#pragma once

#include <agrpc/asio_grpc.hpp>
#include <boost/asio/awaitable.hpp>
#include <grpcpp/channel.h>

#include <expected>
#include <functional> // Required for std::function
#include <generator>

// Include the generated protobuf header that defines DeploymentInfoMessage
#include "src/generated/headnode-service.pb.h"

#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace asio = boost::asio;

// Forward-declare other generated protobuf types
namespace protos {
class ReplicaRequest;
class ReplicaReply;
class WorkerService;
}  // namespace protos

struct ReplicaInfo {
    std::string replica_id;
    std::string address;
    std::string state;
    int active_requests;
    enum Health{Healthy,Unhealthy};
    Health health_status{Healthy};
    std::chrono::steady_clock::time_point last_failure_time;
};

struct ReplicaConnection {
    std::shared_ptr<ReplicaInfo> info;
    std::shared_ptr<grpc::Channel> channel;
};

class DeploymentHandle {
public:
    DeploymentHandle(agrpc::GrpcContext& grpc_context,
                     const protos::DeploymentInfoMessage& deployment_info);

    // MODIFIED: Takes a callback to handle each token asynchronously.
    // The callback itself returns an awaitable to allow the caller to perform async work.
    asio::awaitable<void> send_request(
        std::string message,
        std::function<asio::awaitable<void>(
            std::expected<std::string, grpc::Status>)> on_token);

    void add_replicas(const protos::DeploymentInfoMessage& deployment_info);

private:
    // RAII-style helper to ensure replicas are always released.
    struct ReplicaReleaser {
        std::shared_ptr<ReplicaInfo> replica_info;
        ~ReplicaReleaser() { replica_info->active_requests--; }
    };
    
    std::optional<ReplicaConnection> pick_next_replica();
    void mark_replica_unhealthy(const std::string& replica_id);

    agrpc::GrpcContext& grpc_context_;
    std::string deployment_id_;
    std::string deployment_name_;
    std::vector<std::shared_ptr<ReplicaInfo>> replicas_;
    //std::set<std::pair<int,std::string>>active_requests;
    std::unordered_map<std::string, std::shared_ptr<grpc::Channel>> channel_cache_;
    //std::unordered_map<std::string, int>count_;
    size_t next_replica_idx_{0};
    std::mutex mtx_;
};  


