#include "http_proxy.h"

#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>
#include <boost/asio/signal_set.hpp>
#include <boost/asio/write.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/program_options.hpp>
#include <prometheus/text_serializer.h>

#include <print>
#include <iostream>
#include <sstream>
#include <thread>

#include "src/generated/headnode-service.grpc.pb.h"
#include "src/generated/headnode-service.pb.h"
#include "src/generated/proxy-service.grpc.pb.h"
#include "src/generated/proxy-service.pb.h"

#include <grpcpp/create_channel.h>
#include <grpcpp/security/credentials.h>
#include <grpcpp/server.h>
#include <grpcpp/server_builder.h>
#include <agrpc/asio_grpc.hpp>


namespace po = boost::program_options;
namespace beast = boost::beast;
namespace http = beast::http;

HttpProxy::HttpProxy(asio::io_context& ioc,
                     agrpc::GrpcContext& grpc_context,
                     unsigned short http_port, unsigned short parent_port)
    : ioc_(ioc),
      grpc_context_(grpc_context),
      acceptor_(ioc, {tcp::v4(), http_port}),
      parent_port_(parent_port),
      metrics_registry_(std::make_shared<prometheus::Registry>()),
      request_count_family_(prometheus::BuildCounter()
                                .Name("proxy_requests_total")
                                .Help("Total requests handled by proxy")
                                .Register(*metrics_registry_)),
      active_requests_family_(prometheus::BuildGauge()
                                  .Name("proxy_active_requests")
                                  .Help("Number of active requests")
                                  .Register(*metrics_registry_)),
      request_latency_family_(
          prometheus::BuildHistogram()
              .Name("proxy_request_latency_seconds")
              .Help("End-to-end request latency from proxy perspective")
              .Register(*metrics_registry_)),
      first_token_latency_family_(
          prometheus::BuildHistogram()
              .Name("proxy_first_token_latency_seconds")
              .Help("Time to first token from proxy perspective")
              .Register(*metrics_registry_)),
      inter_token_latency_histogram_(
          prometheus::BuildHistogram()
              .Name("inter_token_latency_seconds")
              .Help("Time between consecutive tokens from the LLM")
              .Register(*metrics_registry_))
{
    std::println(stderr,"HTTP Proxy listening on port {}", http_port);
}   

// ... http_listener and serve_metrics are unchanged ...
asio::awaitable<void> HttpProxy::http_listener() {
    for (;;) {
        try {
            auto socket = co_await acceptor_.async_accept(asio::use_awaitable);
            asio::co_spawn(ioc_, http_session(std::move(socket)),
                           asio::detached);
        } catch (const std::exception& e) {
            std::println(stderr, "Accept error: {}", e.what());
        }
    }
}

asio::awaitable<void> HttpProxy::serve_metrics(tcp::socket& socket) {
    try {
        prometheus::TextSerializer serializer;
        auto metrics = metrics_registry_->Collect();
        std::stringstream ss;
        serializer.Serialize(ss, metrics);

        http::response<http::string_body> res{http::status::ok, 11};
        res.set(http::field::server, "http-proxy");
        res.set(http::field::content_type, "text/plain; version=0.0.4");
        res.body() = ss.str();
        res.prepare_payload();
        co_await http::async_write(socket, res, asio::use_awaitable);
    } catch (const std::exception& e) {
        std::println(stderr, "Metrics serving error: {}", e.what());
    }
}


asio::awaitable<void> HttpProxy::http_session(tcp::socket socket) {
    beast::flat_buffer buffer;
    http::request<http::string_body> req;
    const auto start_time = std::chrono::steady_clock::now();
    std::string deployment_name = "unknown";

    // This is a RAII-style way to ensure the gauge is always decremented
    // when the session goes out of scope.
    auto& active_requests_gauge = active_requests_family_.Add({});
    active_requests_gauge.Increment();
    struct final_action {
        prometheus::Gauge& gauge;
        ~final_action() { gauge.Decrement(); }
    };
    final_action decrementer{active_requests_gauge};

    try {
        co_await http::async_read(socket, buffer, req, asio::use_awaitable);

        if (req.target() == "/metrics") {
            co_await serve_metrics(socket);
            co_return;
        }

        std::shared_ptr<DeploymentHandle> handle;
        {
            std::shared_lock<std::shared_mutex> lock(routing_mutex_);
            deployment_name = std::string(req.target());
            std::println(stderr, "Deployment name: {}", deployment_name);
            auto it = routing_table_.find(deployment_name);
            if (it != routing_table_.end()) {
                handle = it->second;
            }
        }

        if (!handle) {
            http::response<http::string_body> res{http::status::not_found, req.version()};
            res.set(http::field::server, "http-proxy");
            res.body() = "Deployment not found";
            res.prepare_payload();
            co_await http::async_write(socket, res, asio::use_awaitable);
            throw std::runtime_error("Deployment not found");
        }

        http::response<http::empty_body> res{http::status::ok, req.version()};
        res.set(http::field::server, "http-proxy");
        res.set(http::field::content_type, "text/plain");
        res.chunked(true);
        
        http::response_serializer<http::empty_body> sr{res};
        co_await http::async_write_header(socket, sr, asio::use_awaitable);

        // Stream tokens as they arrive from the gRPC service using callback
        bool first_token = true;
        auto last_token_time = std::chrono::steady_clock::now();
        bool last_token_received = false; 
        auto on_token_received = [&](std::expected<std::string, grpc::Status> expected_token) -> asio::awaitable<void> {
            if (first_token) {
                const auto ttft = std::chrono::duration<double>(
                    std::chrono::steady_clock::now() - start_time).count();
                // Corrected: Pass bucket boundaries when adding a histogram to the family.
                auto& latency_hist = first_token_latency_family_.Add(
                    {{"deployment_name", deployment_name}},
                    prometheus::Histogram::BucketBoundaries{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 180});
                latency_hist.Observe(ttft);
                first_token = false;
            }

            if (expected_token.has_value()) {
                std::stringstream chunk_stream;
                chunk_stream << std::hex << expected_token.value().length() << "\r\n"
                << expected_token.value() << "\r\n";
                std::string chunk = chunk_stream.str();
                co_await asio::async_write(socket, asio::buffer(chunk), asio::use_awaitable);
                //Are these latency calcualtions robust to stream errors?
                if(last_token_received)
                {
                    auto& inter_token_latency_hist = inter_token_latency_histogram_.Add({{"deployment_name", deployment_name}},
                    prometheus::Histogram::BucketBoundaries{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10});
                    inter_token_latency_hist.Observe(std::chrono::duration<double>(std::chrono::steady_clock::now() - last_token_time).count());
                }
                last_token_time = std::chrono::steady_clock::now();
                last_token_received = true;
            } else {
                std::println(stderr, "gRPC stream error: {}",
                             expected_token.error().error_message());
                throw std::runtime_error("gRPC stream error");
            }
        };

        co_await handle->send_request(req.body(), on_token_received);

        if (first_token) {
            // If no tokens were received (empty response), mark the end time now.
            last_token_time = std::chrono::steady_clock::now();
        }

        const auto latency = std::chrono::duration<double>(
            last_token_time - start_time).count();
        // Corrected: Pass bucket boundaries when adding a histogram to the family.
        auto& request_latency_hist = request_latency_family_.Add(
            {{"deployment_name", deployment_name}, {"status", "success"}},
            prometheus::Histogram::BucketBoundaries{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 180});
        request_latency_hist.Observe(latency);

        request_count_family_.Add({{"deployment_name", deployment_name}, {"status", "success"}})
            .Increment();

    } catch (const std::exception& e) {
        std::println(stderr, "Session error for deployment '{}': {}", deployment_name, e.what());
        const auto latency = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - start_time).count();
        auto& request_latency_hist = request_latency_family_.Add(
            {{"deployment_name", deployment_name}, {"status", "error"}},
            prometheus::Histogram::BucketBoundaries{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 180});
        request_latency_hist.Observe(latency);
        request_count_family_.Add({{"deployment_name", deployment_name}, {"status", "error"}})
            .Increment();
    }
    try{
        // Manually write the final "zero-chunk" to correctly terminate the HTTP response.
        co_await asio::async_write(socket, asio::buffer("0\r\n\r\n"), asio::use_awaitable);
    }
    //Ignore if the client already disconnected
    catch(...){}
    beast::get_lowest_layer(socket).close();
}

asio::awaitable<void> HttpProxy::subscribe_to_head_node() {
    
    while (true) {
        auto channel = grpc::CreateChannel("0.0.0.0:" + std::to_string(parent_port_),
                                       grpc::InsecureChannelCredentials());
        auto stub = protos::ProxyManagementService::NewStub(channel);
        protos::SubscriptionRequest request;
        request.set_proxy_id("cpp-proxy-01");
        
        agrpc::ClientRPC<&protos::ProxyManagementService::Stub::PrepareAsyncSubscribeToRoutingUpdates> rpc(grpc_context_);
        
        bool connected = false;
        try {
            if (co_await rpc.start(*stub, request, asio::use_awaitable)) {
                connected = true;
                std::println(stderr, "Successfully subscribed to head node.");
                protos::RoutingUpdate update;
                while (co_await rpc.read(update, asio::use_awaitable)) {
                    apply_routing_update(update);
                }
            }
        } catch (const std::exception& e) {
            std::println(stderr, "Exception during subscription RPC: {}", e.what());
        }

        if (!connected) {
            std::println(stderr, "Failed to start subscription RPC to head node.");
        } else {
             std::println(stderr, "Subscription stream ended. Reconnecting...");
        }

        std::println(stderr, "Retrying in 5 seconds...");
        asio::steady_timer timer(co_await asio::this_coro::executor);
        timer.expires_after(std::chrono::seconds(5));
        co_await timer.async_wait(asio::use_awaitable);
    }
}



void HttpProxy::apply_routing_update(
    const protos::RoutingUpdate& update) {
    std::unique_lock<std::shared_mutex> lock(routing_mutex_);
    
    // --- [DEBUG] Detailed logging for RoutingUpdate ---
    std::println(stderr, "--- New Routing Update Received ---");
    std::println(stderr, "  Timestamp (ns): {}", update.timestamp_ns());
    std::println(stderr, "  Total deployments in update: {}", update.current_deployments_size());

    // Create a temporary new routing table
    std::unordered_map<std::string, std::shared_ptr<DeploymentHandle>> new_routing_table;

    for (const auto& [dep_id, dep_info] : update.current_deployments()) {
        std::println(stderr, "  -> Deployment ID: {}, Name: '{}'", dep_id, dep_info.deployment_name());
        std::println(stderr, "     Replicas: {}", dep_info.replicas_size());

        for (const auto& replica : dep_info.replicas()) {
            std::println(stderr, "       - Replica ID: {}, Address: {}, State: {}", 
                         replica.replica_id(), replica.address(), replica.state());
        }
        
        // If the deployment is new
         new_routing_table[dep_info.deployment_name()] =
            std::make_shared<DeploymentHandle>(grpc_context_, dep_info);
    }
    
    // Atomically swap the old routing table with the new one
    routing_table_.swap(new_routing_table);
    
    std::println(stderr, "--- Routing Update Applied ---");
}


//Class to start a grpc server for health checks from the head node
class HealthService : public protos::HealthService::Service {
    public:
      // The service class now only needs to implement its RPCs.
      grpc::Status Ping(grpc::ServerContext* context,
                        const google::protobuf::Empty* request,
                        protos::Ack* response) override {
          std::println(stderr, "Received health check request");
          response->set_acknowledged(true);
          return grpc::Status::OK;
      }
  };

int main(int argc, char* argv[]) {
    std::cout << std::unitbuf;
    try {
        // --- 1. Argument Parsing (unchanged) ---
        po::options_description desc("Allowed options");
        desc.add_options()("help", "produce help message")(
            "http_port", po::value<unsigned short>()->default_value(8000),
            "HTTP listen port")(
            "parent_port", po::value<unsigned short>()->default_value(50051),
            "Head node gRPC port")(
            "grpc_port", po::value<unsigned short>()->default_value(50052),
            "gRPC listen port for health checks");

        po::variables_map vm;
        po::store(po::parse_command_line(argc, argv, desc), vm);
        po::notify(vm);

        if (vm.count("help")) {
            std::cout << desc << std::endl;
            return 1;
        }

        const auto http_port = vm["http_port"].as<unsigned short>();
        const auto parent_port = vm["parent_port"].as<unsigned short>();
        const auto grpc_port = vm["grpc_port"].as<unsigned short>();
        const auto thread_count = std::thread::hardware_concurrency();
        
        std::println(stderr, "C++ Proxy starting...");
        std::println(stderr, "  HTTP Port: {}", http_port);
        std::println(stderr, "  gRPC Health Port: {}", grpc_port);
        std::println(stderr, "  Worker Threads: {}", thread_count);

        // --- 2. Setup Contexts and Services ---
        asio::io_context ioc{static_cast<int>(thread_count)};
        // Create the ServerBuilder first.
        grpc::ServerBuilder builder;
        // **NEW: Pass the builder to the GrpcContext constructor.**
        // This handles the linking automatically and is the preferred approach.
        agrpc::GrpcContext grpc_context{builder.AddCompletionQueue()};
        HttpProxy proxy(ioc, grpc_context, http_port, parent_port);
        HealthService health_service;

        // --- 3. Build the gRPC Server ---
        // The builder is now already linked to the context.
        builder.AddListeningPort("0.0.0.0:" + std::to_string(grpc_port),
                                 grpc::InsecureServerCredentials());
        builder.RegisterService(&health_service);
        std::unique_ptr<grpc::Server> server = builder.BuildAndStart();
        std::println(stderr, "gRPC HealthService is listening on port {}", grpc_port);

        // --- 4. Spawn Asynchronous Tasks (unchanged) ---
        asio::co_spawn(ioc, proxy.http_listener(), asio::detached);
        asio::co_spawn(grpc_context, proxy.subscribe_to_head_node(),
                       asio::detached);

        // --- 5. Start a Dedicated Thread for All gRPC Operations ---
        std::thread grpc_thread{[&] {
            grpc_context.run();
        }};

        // --- 6. Graceful Shutdown Handler ---
        asio::signal_set signals(ioc, SIGINT, SIGTERM);
        signals.async_wait([&](auto, auto) {
            std::println(stderr, "\nShutdown signal received...");
            server->Shutdown();
            grpc_context.stop();
            ioc.stop();
        });

        // --- 7. Create Thread Pool for HTTP I/O (unchanged) ---
        std::vector<std::thread> threads;
        threads.reserve(thread_count);
        for (unsigned int i = 0; i < thread_count; ++i) {
            threads.emplace_back([&ioc] { ioc.run(); });
        }

        // --- 8. Wait for All Threads to Complete (unchanged) ---
        grpc_thread.join();
        for (auto& t : threads) {
            if (t.joinable()) {
                t.join();
            }
        }

    } catch (const std::exception& e) {
        std::println(stderr, "Main exception: {}", e.what());
        return 1;
    }

    std::println(stderr, "Proxy shut down cleanly.");
    return 0;
}