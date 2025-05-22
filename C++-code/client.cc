#include <grpcpp/grpcpp.h>
#include "worker-service.grpc.pb.h"
#include<thread>
using grpc::Channel;
using grpc::ClientContext;
using grpc::Status;
using worker::WorkerService;
using worker::WorkerRequest;
using worker::WorkerReply;
using namespace std;
class WorkerClient {
    public:
     WorkerClient(std::shared_ptr<Channel> channel)
         : stub_(WorkerService::NewStub(channel)) {}
   
     void SendTask(const string &data) {
       WorkerRequest request;
       request.set_data_to_process(data);
   
       WorkerReply reply;
       ClientContext context;
   
       Status status = stub_->ProcessData(&context, request, &reply);
   
       if (status.ok()) {
         std::cout << "Reply: " << reply.processed_data()
                   << ", success: " << reply.success() << std::endl;
       } else {
         std::cerr << "RPC failed: " << status.error_message() << std::endl;
       }
     }
   
    private:
     std::unique_ptr<WorkerService::Stub> stub_;
   };
   int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "Usage: client <message>" << std::endl;
        return 1;
    }
    
    std::string message = argv[1];
    
   
    WorkerClient client(grpc::CreateChannel("localhost:50054", grpc::InsecureChannelCredentials()));
    for(int i=0;i<10;i++)
    {
        client.SendTask(message);
        std::this_thread::sleep_for(std::chrono::seconds(2));  // Simulate processing delay
    }
    
    return 0;
   }