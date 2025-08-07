#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <chrono>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <optional>
#include <grpcpp/grpcpp.h>
#include <pybind11/embed.h>
#include <pybind11/stl.h>
#include <unistd.h>
#include <climits>
#include <libgen.h>
#include <pybind11/pybind11.h>
#include "src/generated/replica_service.grpc.pb.h"
#include "src/generated/worker-service.grpc.pb.h"
#include <prometheus/exposer.h>
#include <prometheus/registry.h>
#include <prometheus/counter.h>
#include <prometheus/histogram.h>
#include <map>


namespace py = pybind11;
using namespace std;

std::shared_ptr<prometheus::Registry> registry = std::make_shared<prometheus::Registry>();
auto& cpp_counter_family = prometheus::BuildCounter()
    .Name("replica_cpp_requests_total")
    .Help("Total C++ replica requests handled")
    .Register(*registry);

auto& cpp_latency_family = prometheus::BuildHistogram()
    .Name("replica_cpp_request_latency_seconds")
    .Help("C++ Replica request latency in seconds")
    .Register(*registry);

auto& cpp_first_token_family = prometheus::BuildHistogram()
    .Name("replica_cpp_first_token_latency_seconds")
    .Help("C++ Replica first token latency in seconds")
    .Register(*registry);

std::map<std::string, prometheus::Counter*> request_counters;
std::map<std::string, prometheus::Histogram*> latency_histograms;
std::map<std::string, prometheus::Histogram*> ttft_histograms;


// Shared args
std::string replica_id, parent_port, port, deployment_name, deployment_id, num_cpus, num_gpus, metrics_port;

class ThreadSafeQueue {
    std::queue<std::string> q;
    std::mutex m;
    std::condition_variable cv;
    bool closed = false;

public:
    void put(std::string val) {
        std::lock_guard<std::mutex> lock(m);
        q.push(std::move(val));
        cv.notify_one();
    }

    std::optional<std::string> get() {
        std::unique_lock<std::mutex> lock(m);
        cv.wait(lock, [&] { return closed || !q.empty(); });
        if (q.empty()) return std::nullopt;
        auto val = std::move(q.front());
        q.pop();
        return val;
    }

    void close() {
        std::lock_guard<std::mutex> lock(m);
        closed = true;
        cv.notify_all();
    }
};

class ReplicaServer final : public protos::WorkerService::Service {
    py::object loop, replica_mgr;

public:
    ReplicaServer(py::object loop_, py::object mgr_) : loop(loop_), replica_mgr(mgr_) {}

    grpc::Status Ping(grpc::ServerContext*, const google::protobuf::Empty*, protos::Ack* reply) override {
        std::cout << "[C++] Ping received" << std::endl;
        reply->set_acknowledged(true);
    
        return grpc::Status::OK;
    }

    grpc::Status SendRequest(grpc::ServerContext*, const protos::ReplicaRequest* req,
                             grpc::ServerWriter<protos::ReplicaReply>* writer) override {
        const std::string& prompt = req->prompt();
        auto start = std::chrono::high_resolution_clock::now();
        auto last_token_time = start;
        bool first_token_seen = false;
        double ttft = 0.0;
        std::string formatted = "<|user|>\n" + prompt + "<|end|>\n<|assistant|>\n";
        auto queue = std::make_shared<ThreadSafeQueue>();

        try {
            py::gil_scoped_acquire gil;

            static bool defined = false;
            if (!defined) {
                py::exec(R"(
class QueueCallback:
    def __init__(self, cpp_put):
        self.cpp_put_func = cpp_put
    def put(self, item):
        self.cpp_put_func(item)
)");
                defined = true;
            }

            auto cpp_put = py::cpp_function([queue](py::object item) {
                if (item.is_none()) queue->close();
                else queue->put(item.cast<std::string>());
            });

            auto callback_class = py::globals()["QueueCallback"];
            auto callback = callback_class(cpp_put);
            auto coro = replica_mgr.attr("generate_stream")(formatted, callback);

            loop.attr("call_soon_threadsafe")(loop.attr("create_task"), coro);
        } catch (const py::error_already_set& e) {
            std::cerr << "[C++] Python error in SendRequest: " << e.what() << std::endl;
            return grpc::Status::CANCELLED;
        }

        while (true) {
            auto item = queue->get();
            if (!item.has_value()) break;
            protos::ReplicaReply reply;
            cout << "[C++] Received item: " << *item << endl;
            reply.set_text(*item);
            reply.set_is_error(item->find("[PYTHON ERROR]") != std::string::npos);
            
            if (!first_token_seen) {
                ttft = std::chrono::duration<double>(
                    std::chrono::high_resolution_clock::now() - start).count();
                ttft_histograms[deployment_name]->Observe(ttft);
                first_token_seen = true;
            }
    
            if (!writer->Write(reply)) break;
            last_token_time = std::chrono::high_resolution_clock::now();
        }

        if (!first_token_seen) {
            last_token_time = std::chrono::high_resolution_clock::now();
        }

        auto total_latency = std::chrono::duration<double>(
            last_token_time - start).count();
        latency_histograms[deployment_name]->Observe(total_latency);
        request_counters[deployment_name]->Increment();
    
        return grpc::Status::OK;
    }
};

void RegisterReplicaWithScheduler(const std::string& parent_port,
                                  const std::string& replica_port,
                                  const std::string& replica_id,
                                  const std::string& deployment_id,
                                  const std::string& deployment_name) {
    auto channel = grpc::CreateChannel("0.0.0.0:" + parent_port, grpc::InsecureChannelCredentials());
    auto stub = protos::ReplicaService::NewStub(channel);

    protos::replicaStatus request;
    request.set_state("RUNNING");
    request.set_replica_id(static_cast<uint32_t>(std::stoul(replica_id)));
    request.set_pid(static_cast<uint32_t>(getpid()));
    request.set_port(replica_port);
    request.set_deployment_id(static_cast<uint32_t>(std::stoul(deployment_id)));
    request.set_deployment_name(deployment_name);

    grpc::ClientContext context;
    protos::Reply response;
    grpc::Status status = stub->RegisterReplica(&context, request, &response);

    if (!status.ok() || !response.ack()) {
        std::cerr << "[Replica-" << replica_id << "] Registration failed: " << status.error_message() << std::endl;
        exit(1);
    }

    std::cout << "[Replica-" << replica_id << "] Registered successfully." << std::endl;
}

void run_python_event_loop(py::object loop) {
    py::gil_scoped_acquire gil;
    try {
        loop.attr("run_forever")();
    } catch (const py::error_already_set& e) {
        std::cerr << "[C++] Python loop error: " << e.what() << std::endl;
    }
}

std::string get_arg(char** argv, int& i) {
    char* eq = strchr(argv[i], '=');
    return eq ? std::string(eq + 1) : std::string(argv[++i]);
}

bool parse_args(int argc, char** argv) {
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--replica_id") replica_id = get_arg(argv, i);
        else if (arg == "--parent_port") parent_port = get_arg(argv, i);
        else if (arg == "--port") port = get_arg(argv, i);
        else if (arg == "--deployment_name") deployment_name = get_arg(argv, i);
        else if (arg == "--deployment_id") deployment_id = get_arg(argv, i);
        else if (arg == "--num_cpus") num_cpus = get_arg(argv, i);
        else if (arg == "--num_gpus") num_gpus = get_arg(argv, i);
        else if (arg == "--metrics_port") metrics_port = get_arg(argv, i);
    }
    return !replica_id.empty() && !port.empty() && !metrics_port.empty();
}

int main(int argc, char** argv) {
    if (!parse_args(argc, argv)) {
        std::cerr << "Usage: " << argv[0] << " --replica_id <id> --port <port> --metrics_port <port> [...]";
        return 1;
    }

    py::scoped_interpreter guard{};

    // Initialize metrics
    request_counters[deployment_name] = &cpp_counter_family.Add({{"deployment_name", deployment_name}});
    latency_histograms[deployment_name] = &cpp_latency_family.Add({{"deployment_name", deployment_name}},
    prometheus::Histogram::BucketBoundaries{0.1, 0.5, 1, 5, 10, 30, 60, 120,180});
    ttft_histograms[deployment_name] = &cpp_first_token_family.Add({{"deployment_name", deployment_name}},
    prometheus::Histogram::BucketBoundaries{0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.0});


    py::gil_scoped_release release;

    py::object loop, mgr;
    {
        py::gil_scoped_acquire gil;
        py::module_::import("sys").attr("path").attr("insert")(0, "/app");
        auto asyncio = py::module_::import("asyncio");
        loop = asyncio.attr("new_event_loop")();
        asyncio.attr("set_event_loop")(loop);

        auto mod = py::module_::import("src.components.add_replica");
        auto cls = mod.attr("ReplicaManager");
        mgr = cls(deployment_name, std::stoi(deployment_id), std::stoi(metrics_port), loop);
       
    }
    
    std::thread py_thread(run_python_event_loop, loop);
    /*
    {
        py::gil_scoped_acquire gil;
        mgr.attr("start_polling_metrics")();
        std::cout << "[C++] Started polling metrics" << std::endl;
    }
    */
    ReplicaServer service(loop, mgr);

    grpc::ServerBuilder builder;
    builder.AddListeningPort("0.0.0.0:" + port, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    auto server = builder.BuildAndStart();
    std::cout << "[C++] gRPC Server listening on port " << port << std::endl;

    RegisterReplicaWithScheduler(parent_port, port, replica_id, deployment_id, deployment_name);
    
    // Start Prometheus exposer
    int cpp_metrics_port = std::stoi(metrics_port) + 1;
    prometheus::Exposer exposer("0.0.0.0:" + std::to_string(cpp_metrics_port));
    exposer.RegisterCollectable(registry);
    std::cout << "[C++] Exposing Prometheus metrics at :" << cpp_metrics_port << std::endl;

    server->Wait();


    {
        py::gil_scoped_acquire gil;
        loop.attr("stop")();
    }
    py_thread.join();

    return 0;
}