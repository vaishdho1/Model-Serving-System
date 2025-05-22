// raylet_worker_rpc_demo.cpp

#include <grpcpp/grpcpp.h>
#include <iostream>
#include <thread>
#include <mutex>
#include <unordered_map>
#include <queue>
#include <atomic>
#include <chrono>
#include <memory>
#include <cstdlib>
#include <csignal>
#include <unistd.h>
#include <sys/wait.h>

#include "worker_service.grpc.pb.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;
using grpc::ClientContext;
using grpc::Channel;
using grpc::InsecureChannelCredentials;

using worker::WorkerService;
using worker::PushTaskRequest;
using worker::PushTaskReply;

std::mutex queue_mutex;
std::unordered_map<std::string, std::queue<PushTaskRequest>> actor_queues;
std::unordered_map<std::string, std::shared_ptr<WorkerService::Stub>> stub_pool;
std::unordered_map<std::string, std::atomic<bool>> actor_ready;
std::unordered_map<std::string, grpc::CompletionQueue*> actor_cq;

class WorkerServiceImpl final : public WorkerService::Service {
public:
    explicit WorkerServiceImpl(std::string actor_id) : actor_id_(std::move(actor_id)) {}

    Status PushTask(ServerContext* context, const PushTaskRequest* request,
                    PushTaskReply* reply) override {
        std::cout << "[" << actor_id_ << "] Task: " << request->task_id()
                  << " | Data: " << request->task_data() << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        reply->set_success(true);
        reply->set_message("Completed");
        return Status::OK;
    }

private:
    std::string actor_id_;
};

void RunWorkerServer(const std::string& actor_id, const std::string& port) {
    std::string server_address = "0.0.0.0:" + port;
    WorkerServiceImpl service(actor_id);

    ServerBuilder builder;
    builder.AddListeningPort(server_address, InsecureChannelCredentials());
    builder.RegisterService(&service);

    std::unique_ptr<Server> server(builder.BuildAndStart());
    std::cout << "[" << actor_id << "] Worker running on port: " << port << std::endl;
    server->Wait();
}

void ActorDispatcher(const std::string& actor_id, const std::string& address) {
    while (true) {
        if (!actor_ready[actor_id]) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }

        std::lock_guard<std::mutex> lock(queue_mutex);
        if (!actor_queues[actor_id].empty()) {
            auto task = actor_queues[actor_id].front();
            actor_queues[actor_id].pop();

            grpc::ClientContext ctx;
            PushTaskReply reply;
            auto stub = stub_pool[actor_id];
            Status status = stub->PushTask(&ctx, task, &reply);

            if (status.ok()) {
                std::cout << "[Raylet → " << actor_id << "] Sent task: " << task.task_id() << std::endl;
                actor_ready[actor_id] = false;
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                actor_ready[actor_id] = true;
            }
        }
    }
}

class RayletNodeManagerServiceImpl final : public WorkerService::Service {
public:
    Status PushTask(ServerContext* context, const PushTaskRequest* request,
                    PushTaskReply* reply) override {
        std::string actor_id = request->actor_id();

        {
            std::lock_guard<std::mutex> lock(queue_mutex);
            actor_queues[actor_id].push(*request);
        }

        reply->set_success(true);
        reply->set_message("Task enqueued for actor " + actor_id);
        return Status::OK;
    }
};

void RunRayletServer(const std::string& port) {
    std::string address = "0.0.0.0:" + port;
    RayletNodeManagerServiceImpl service;

    ServerBuilder builder;
    builder.AddListeningPort(address, InsecureChannelCredentials());
    builder.RegisterService(&service);

    std::unique_ptr<Server> server(builder.BuildAndStart());
    std::cout << "Raylet listening on port: " << port << std::endl;
    server->Wait();
}

void SpawnWorkerProcess(const std::string& actor_id, const std::string& port) {
    pid_t pid = fork();
    if (pid == 0) {
        execl("./worker_binary", "./worker_binary", actor_id.c_str(), port.c_str(), NULL);
        exit(1);
    }
}

int main() {
    std::vector<std::string> ports = {"50051", "50052"};
    std::vector<std::string> actor_ids = {"actor_0", "actor_1"};

    std::thread raylet_listener(RunRayletServer, "60000");

    for (size_t i = 0; i < ports.size(); ++i) {
        SpawnWorkerProcess(actor_ids[i], ports[i]);
    }

    std::this_thread::sleep_for(std::chrono::seconds(2));

    for (size_t i = 0; i < actor_ids.size(); ++i) {
        std::string addr = "localhost:" + ports[i];
        stub_pool[actor_ids[i]] = WorkerService::NewStub(
            grpc::CreateChannel(addr, InsecureChannelCredentials()));
        actor_ready[actor_ids[i]] = true;
    }

    std::vector<std::thread> dispatchers;
    for (size_t i = 0; i < actor_ids.size(); ++i) {
        dispatchers.emplace_back(ActorDispatcher, actor_ids[i], "localhost:" + ports[i]);
    }

    {
        std::lock_guard<std::mutex> lock(queue_mutex);
        for (int i = 0; i < 5; ++i) {
            for (const auto& actor_id : actor_ids) {
                PushTaskRequest req;
                req.set_actor_id(actor_id);
                req.set_task_id("task_" + std::to_string(i));
                req.set_task_data("do something");
                actor_queues[actor_id].push(req);
            }
        }
    }

    for (auto& t : dispatchers) t.join();
    raylet_listener.join();
    return 0;
}
