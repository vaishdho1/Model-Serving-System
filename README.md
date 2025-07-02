# Model Serving System

## Overview

This project implements a **distributed model serving system** designed to efficiently manage and serve Large Language Models (LLMs). The architecture features a **head controller** for coordination, **scheduler nodes** managing replica processes, an **HTTP proxy** for client access, and **replica processes** running the actual models. Built with **gRPC** for internal communication and **HTTP** for client interfaces, the system delivers robust fault tolerance, automatic restart capabilities, and flexible deployment options while successfully handling **1000+ concurrent users** with **100+ RPS sustained throughput**.


### Core Components

- **HTTP Proxy** (`src/components/headNode/http_proxy.py`): FastAPI-based client interface providing RESTful endpoints 
- **Head Controller** (`src/components/headNode/head_controller.py`): Central orchestrator for the system
- **Scheduler Nodes** (`src/components/scheduler.py`): Worker nodes managing model replicas
- **Model Replicas** (`src/components/add_replica_vllm.py`): vLLM powered inference engines
- **Cloud VM Manager** (`src/lib/cloud_vm/aws_vm_manager.py`): AWS EC2 autoscaling integration

---

## Key Features Implemented

### **High-Performance Inference**
- **vLLM AsyncEngine**: Continuous batching with PagedAttention for optimal GPU utilization
- **Token-by-Token Streaming**: Real time response streaming
- **Concurrent Processing**: Handles 1000+ concurrent requests with minimal latency increase
- **Efficient Memory Management**: 2-3x better GPU memory utilization vs vanilla Transformers

### **Distributed Architecture**
- **Async Architecture**: Entire system uses async architecture.
- **gRPC Communication**: Type safe, high performance internal communication with bi-directional streaming
- **Pub-Sub**: Real-time routing updates without external dependencies
- **Load Balancing**: Least loaded replica selection with request count tracking
- **Fault Tolerance**: Multi layer health monitoring with automatic recovery

### **Production Monitoring**
- **Prometheus Integration**: Comprehensive metrics at certain layers (proxy, replicas)
- **Grafana Dashboards**: Real time visualization of performance and health metrics

### **Cloud-Native Deployment**
- **Docker Containers**: Multi stage builds optimized for CUDA workloads
- **AWS Integration**: EC2 auto scaling with dynamic resource discovery
- **Infrastructure as Code**: Automated deployment scripts and security group management
- **Container Registry**: ECR integration for image management

### **Model Support**
- **Multiple Models**: GPT-2, TinyLlama, Phi-2
- **Dynamic Configuration**: JSON-based model configuration
- **Flexible Endpoints**: RESTful API design with model specific routing



## Deployment Options

### AWS Deployment

#### Docker Image Details

**Controller Image**
- Base: python:3.10-slim
- Key Components:
  - FastAPI for HTTP endpoints
  - gRPC for internal communication
  - Cloud provider SDKs (AWS, GCP)

**Scheduler Image**
- Base: nvidia/cuda:12.1.1-cudnn8-devel
- Features:
  - CUDA 12.1.1 support
  - PyTorch with CUDA
  - vLLM for efficient inference

#### Build Docker Images
```bash
# Build Controller Image
cd scripts/aws_scripts
./build-aws-controller.sh

# Build Scheduler Image
./build-aws-scheduler.sh
```


#### Start controller VM
```bash
# Build Controller Image
./deploy-controller-aws.sh
```

#### (Optionally) Start Prometheus VM
```bash
./deploy_prometheus_vm_aws.sh
```



---

## Available Models & Endpoints

| Model | Endpoint | Model ID | 
|-------|----------|----------|
| **TinyLlama** | `/v1/chat/tinyllama` | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` |
| **GPT-2** | `/v1/chat/gpt2` | `gpt2` |
| **Phi-2** | `/v1/chat/phi2` | `microsoft/phi-2` |


### API Usage Examples

```bash
# Streaming chat completion
curl -X POST http://your-endpoint:8000/v1/chat/tinyllama \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Explain machine learning"}],
    "max_tokens": 500,
    "stream": true
  }' --no-buffer

# Simple text completion
curl -X POST http://your-endpoint:8000/v1/chat/gpt2 \
  -H "Content-Type: text/plain" \
  -d "The future of AI is" \
  --no-buffer
```

---

## Performance Metrics

### **Load Testing Results** (Locust Testing Framework)

#### **Test Configuration**
- **Setup**: Four replicas of A10G with 16GB memory for TinyLlama endpoint
- **Target**: 1000+ concurrent users with sustained load

#### **Performance Results**
```
THROUGHPUT METRICS:
   • Peak RPS: 100 requests/second sustained
   • Variable Load Handling: 20-100 RPS across test phases
   • Load Pattern: Multi phase testing with ramp-up/ramp-down cycles
   • Concurrent Users: Up to 1000 simultaneous connections

RESPONSE TIME ANALYSIS:
   • 50th Percentile (P50): ~10s under normal load
   • 95th Percentile (P95): ~100s during peak stress
   • Response Time Spikes: Correlated with load increases
   • Performance Recovery: Quick stabilization after load drops
   

RELIABILITY TESTING:
   • Zero failures throughout entire test duration
   • System stability maintained across all load phases
   • Graceful performance degradation under extreme load
   • Automatic recovery when load decreases
```

## **Planned features**

-[] **Autoscaling**: Dynamic replica scaling taking SLOs into consideration.
-[] **Persistent Storage**: Exploring storage options for head controller to deal with fault tolerance.
-[] **Distributed proxy**: Add distributed proxy features for better handling of requests
-[] **Quantized inference** : Add 4-bit, 8-bit inference support



