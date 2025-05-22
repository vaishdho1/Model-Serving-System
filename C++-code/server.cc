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
#include "worker-service.grpc.pb.h"
#include "headnode-service.grpc.pb.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;
using grpc::ClientContext;
using grpc::Channel;
using grpc::InsecureChannelCredentials;
using grpc::ClientAsyncResponseReader;
using worker::WorkerService;
using worker::WorkerRequest;
using worker::WorkerReply;
using raylet::HeadNodeService;
using raylet::HeadNodeRequest;
using raylet::HeadNodeReply;
using namespace std;

class WorkerServiceImpl final : public WorkerService::Service {
public:
    Status ProcessData(ServerContext* context, const WorkerRequest* request, WorkerReply* reply) override {
        // Process the request and set the response
        string input = request->data_to_process();
        
        std::cout << "[START] Thread ID: " << std::this_thread::get_id() 
              << " | Received: " << input
              << " | Time: " << std::chrono::system_clock::now().time_since_epoch().count() 
              << std::endl;
        
        cout<<"Processing data:" << input << endl;
        std::this_thread::sleep_for(std::chrono::seconds(5));  // Simulate processing delay
        
        reply->set_processed_data("Processed:"+input);
        reply->set_success(true);
        std::cout << "[END] Thread ID: " << std::this_thread::get_id() 
        << " | Time: " << std::chrono::system_clock::now().time_since_epoch().count() 
        << std::endl;
        return Status::OK;
    }
};
void RunServer() {
    string server_address("0.0.0.0:50054");
    WorkerServiceImpl service;
    ServerBuilder builder;
    
    int num_cpus = std::thread::hardware_concurrency();  
    int server_threads = std::min(std::max(2, num_cpus / 4), 8);  
    
    
    builder.SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::NUM_CQS, server_threads);  
    builder.SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::MIN_POLLERS, server_threads);  
    builder.SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::MAX_POLLERS, server_threads);
    
    builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
   

    std::unique_ptr<Server> server(builder.BuildAndStart());
    std::cout << "Server listening on " << server_address << std::endl;
    server->Wait();
  }
int main()
{
    RunServer();
    return 0;
}
