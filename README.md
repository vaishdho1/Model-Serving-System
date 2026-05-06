# Distributed LLM Serving Infrastructure

A distributed model serving system for low-latency, streaming LLM inference. The system separates the data plane from the control plane: a C++ HTTP proxy handles client facing streaming traffic, while a Python head controller manages deployment state, routing metadata, replica lifecycle, health, and worker coordination.

The project was built to explore the infrastructure problems behind production model serving systems: request routing, replica placement, health-aware load balancing, streaming backpressure, observability, fault recovery, and serving performance under high concurrency.

## Highlights

- Served 1,000+ concurrent clients with 100+ sustained RPS in load tests on 4 A10 GPUs
- Improved p95 end-to-end latency by ~2.5x after replacing the Python proxy path with a C++ proxy and C++ replica networking layer
- ~100ms TTFT under 950 concurrent requests with zero queuing overhead between proxy and replicas
- Supports token-level streaming over HTTP/gRPC
- Uses vLLM-backed replicas for asynchronous generation
- Implements health-aware, least-loaded request routing
- Separates control-plane coordination from the request-serving data path
- Exposes Prometheus metrics for proxy, replica, and serving-path observability

The system was built in two iterations. The first version was a fully async Python system that validated the core architecture but hit GIL and event-loop bottlenecks under high concurrency. The second version replaced the serving path with C++ for the proxy and replica networking layer, eliminating those bottlenecks and cutting p95 latency by ~2.5x.

For detailed write-ups on each version:
- [V1: Building the serving system](https://vaishdho1.github.io/my-portfolio/llm-serving-system.html) — architecture, design decisions, initial load testing
- [V2: The C++ redesign](https://vaishdho1.github.io/my-portfolio/llm-serving-system2.html) — what broke under load, the hybrid C++/Python approach, performance analysis

For the architecture design document, see [`docs/design_document.pdf`](docs/design_document.pdf). For raw benchmark data, see [`docs/results.pdf`](docs/results.pdf).

## Motivation

Production LLM serving looks simple from the outside — accept a prompt, return tokens — but the infrastructure underneath has to solve hard distributed systems problems: how do you route requests when replicas go unhealthy mid-stream? How do you keep tail latency stable when concurrency spikes? How do you separate the fast path (token streaming) from slow coordination (deployment state, health checks) without stale routing?

Most existing frameworks abstract these away behind a single API call. This project builds them explicitly — request routing, replica lifecycle, streaming backpressure, health propagation, observability — to understand what breaks at scale and why.

## Architecture

The system is organized into separate control plane and data plane components.
![Architecture](docs/architecture.png)
### Data plane

The data plane serves user requests and streams generated tokens.

**C++ HTTP Proxy**
- Accepts client requests over HTTP
- Selects a healthy replica using routing metadata from the controller
- Forwards requests to replicas over gRPC
- Streams generated tokens back to clients using HTTP chunked responses

**Replica Server**
- C++ gRPC server handles request and streaming communication
- Python model process runs vLLM generation
- The split avoids placing all networking and model execution in a single Python event loop

### Control plane

The control plane manages deployment and cluster state.

**Head Controller**
- Tracks deployments, replicas, health, and routing state
- Distributes routing updates to proxies
- Coordinates with worker schedulers for replica lifecycle

**Worker Scheduler**
- Runs on each worker node
- Registers available worker capacity with the head controller
- Starts model replicas
- Reports health and replica status

## Core infrastructure problems

### Control plane / data plane separation

The serving path is kept separate from deployment and health-management logic. The proxy can route and stream requests without synchronously involving the controller on every request.

### Health-aware request routing

The proxy routes only to replicas that are known to be healthy and available. Routing metadata is maintained by the head controller and pushed to the serving path.

### Load-aware replica selection

Requests are distributed using least loaded routing to reduce hot spots and improve latency under concurrent traffic.

### Token-level streaming

Responses are streamed token-by-token from the replica back to the client. This reduces perceived latency and allows the system to optimize for time-to-first-token independently of total generation time.

### Observability

The system exposes Prometheus metrics for request throughput, latency, active requests, replica health, and serving-path behavior.

## Performance results

The system was evaluated under high concurrency streaming workloads with up to 1,000 concurrent clients.

| Metric | Earlier Python proxy path | C++ proxy + C++ replica networking path | Result |
|---|---:|---:|---|
| P95 end-to-end latency | ~100s | ~40–42s | ~2.5x improvement |
| P50 end-to-end latency | ~100s under load | ~30–40s | ~2.5–3x improvement |
| Concurrent clients | ~1,000 | ~1,000 | maintained concurrency |
| Failure rate | 0 observed failures | 0 observed failures | stable under test |
| Ramp behavior | latency spikes during load changes | smoother recovery during ramps | improved tail behavior |

The optimization focused on reducing serving-path overhead and improving latency stability under streaming workloads, rather than maximizing raw peak RPS.

## Design tradeoffs

### Direct proxy to replica data path

**V1:** The proxy forwarded requests through the scheduler, which placed them into replica queues. This added a hop and made the scheduler a bottleneck under high concurrency.
**V2:** The proxy sends requests directly to replicas using routing metadata pushed by the controller. Lower latency, but the proxy must maintain a local routing table and the controller must keep it fresh.

### C++ serving path with Python model execution

**V1:** The proxy and replica were both pure Python. Under high concurrency, GIL contention and event-loop blocking from tokenization caused queuing delays that inflated tail latency well beyond what the GPU itself needed.
**V2:** The proxy was rewritten in C++ using Boost.Asio and C++23 coroutines, and the replica was split into a C++ gRPC server for networking with a dedicated Python thread for vLLM generation. This cut p95 latency by ~2.5x, at the cost of a dual-language build and a gRPC boundary between the networking and model layers.

### Scheduler as control-plane only

**V1:** The scheduler participated in both orchestration and live inference traffic, coupling request serving with replica management.
**V2:** The scheduler only manages replica lifecycle and health reporting. The data path scales independently, but the controller must reconcile distributed state from multiple workers.

## Current limitations and future work

- SLO-aware autoscaling and token-aware scheduling
- Backpressure and admission control during overload
- Multi-GPU and multi-node model parallel serving
- Pluggable cluster scheduler for heterogeneous resource placement (GPU, TPU) and mixed workload scheduling (inference, training, fine-tuning)
- Persistent deployment state for controller fault recovery

## Getting started

Quick example on AWS:

```bash
# Build and deploy
chmod +x scripts/aws_scripts/build-aws deploy/aws/deploy_prometheus
scripts/aws_scripts/build-aws
deploy/aws/deploy_prometheus

# Verify serving
curl -N -X POST http://<host>:8000/v1/chat/tinyllama \
  -H "Content-Type: text/plain" \
  --data "What is machine learning?"
```