#pragma once

#include "src/lib/deployment_handle.h"

#include <agrpc/asio_grpc.hpp>
#include <boost/asio/awaitable.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/beast/http/message.hpp>
#include <boost/beast/http/string_body.hpp>

#include <prometheus/counter.h>
#include <prometheus/gauge.h>
#include <prometheus/histogram.h>
#include <prometheus/registry.h>

#include <memory>
#include <shared_mutex>
#include <string>
#include <unordered_map>

namespace asio = boost::asio;
namespace beast = boost::beast;
namespace http = beast::http;
using tcp = asio::ip::tcp;

// The main HTTP server class that listens for requests and routes them.
class HttpProxy {
public:
    // Constructor takes references to the two main execution contexts.(their communication is explained)
    HttpProxy(asio::io_context& ioc, agrpc::GrpcContext& grpc_context,
              unsigned short http_port, unsigned short parent_port);

    // The main coroutine that listens for incoming HTTP connections.
    asio::awaitable<void> http_listener();

    // The coroutine that subscribes to the head node for routing updates.
    asio::awaitable<void> subscribe_to_head_node();

private:
    // Coroutine that handles a single HTTP session.
    asio::awaitable<void> http_session(tcp::socket socket);

    // Coroutine that serves the /metrics endpoint.
    asio::awaitable<void> serve_metrics(tcp::socket& socket);

    // Applies routing updates received from the head node.
    void apply_routing_update(
        const protos::RoutingUpdate& update);

    // A reference to the main Asio execution context for network I/O.
    asio::io_context& ioc_;

    // A reference to the gRPC execution context for gRPC operations.
    agrpc::GrpcContext& grpc_context_;

    // The TCP acceptor that listens for new HTTP connections.
    tcp::acceptor acceptor_;
    unsigned short parent_port_;

    // The routing table mapping deployment names to their handles.
    std::unordered_map<std::string, std::shared_ptr<DeploymentHandle>>
        routing_table_;

    // A read-write mutex to protect the routing table from concurrent access.
    std::shared_mutex routing_mutex_;

    // --- Prometheus Metrics ---
    std::shared_ptr<prometheus::Registry> metrics_registry_;
    prometheus::Family<prometheus::Counter>& request_count_family_;
    prometheus::Family<prometheus::Gauge>& active_requests_family_;
    prometheus::Family<prometheus::Histogram>& request_latency_family_;
    prometheus::Family<prometheus::Histogram>& first_token_latency_family_;
    prometheus::Family<prometheus::Histogram>& inter_token_latency_histogram_;
};

