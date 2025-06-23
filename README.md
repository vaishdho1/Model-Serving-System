# Model Serving System

## Overview

This project implements a **basic functional** distributed model serving system designed to manage and serve LLMs efficiently. The system consists of a head controller for coordination, scheduler nodes that manage replica processes, HTTP proxy for client access, and replica processes that run actual models. The system uses gRPC for internal communication and HTTP for client access, with robust fault tolerance, automatic restart capabilities, and support for multiple deployment scenarios.

## Current Status: ***BASIC FULL FLOW UP***
The system is not fully ready but the basic functionalities are up.

## Project Structure

```
.
├── docker/
│   ├── Dockerfile.controller    # Docker configuration for head controller
│   └── Dockerfile.scheduler     # Docker configuration for scheduler with CUDA support
├── requirements/
│   ├── requirements-controller.txt  # Dependencies for controller node
│   └── requirements-scheduler.txt   # Dependencies for scheduler (includes vLLM, PyTorch)
├── scripts/
│   └── aws_scripts/
│       ├── build-aws-controller.sh  # AWS ECR build script for controller
│       └── build-aws-scheduler.sh   # AWS ECR build script for scheduler
├── src/
│   └── components/              # Core system components
└── protos/                      # Protocol buffer definitions
```

## Core Features Implemented

### **Architecture & Communication**
- **Distributed Architecture**: Head controller, schedulers, HTTP proxy, and replica processes
- **Multi-Protocol Support**: gRPC for internal communication, HTTP/REST for client access
- **Streaming Responses**: Real time token by token model output streaming
- **Dynamic Replica Management**: Automatic creation of model replicas
- **Docker Support**: Containerized deployment for both controller and scheduler
- **Cloud Deployment**: AWS ECR integration for container deployment

### **Model Support**
- **Multiple Models**: Basic testing with GPT-2, TinyLlama, Phi-2


### **Fault Tolerance & Health Management**
- **Health Monitoring**: Comprehensive health checks across all components
- **Automatic Restart**: HTTP proxy auto-restart on failure
- **Dead Replica Detection**: Automatic cleanup of failed replicas
- **Retry Mechanisms**: Robust retry logic with exponential backoff
- **Exception Handling**: Comprehensive error handling and recovery

## Deployment Options

### 1. Docker Deployment

#### Build Docker Images
```bash
# Build Controller Image
cd scripts/aws_scripts
./build-aws-controller.sh

# Build Scheduler Image
./build-aws-scheduler.sh
```

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

### 2. Local Deployment
```bash
# Terminal 1: Start Head Controller
python3 -m src.components.headNode.head_controller --http_port=8000 --node_port=50051 --grpc_port=50052

# Terminal 2: Start Scheduler
python3 -m src.components.scheduler --node_id=1 --head_address=localhost --port=50051 --num_cpus=2 --num_gpus=0
```

### 3. AWS Deployment
The system supports deployment to AWS using Amazon Elastic Container Registry (ECR):
1. Images are built locally with CUDA support for GPU instances
2. Automatically pushed to the ECR repository
3. Can be deployed to ECS/EKS for orchestration

## Client Usage

### Simple Request
```bash
curl -X POST http://localhost:8000/v1/chat/tinyllama \
  -H "Content-Type: text/plain" \
  -d "Explain about Machine Learning?" \
  --no-buffer
```

## Available Models & Endpoints

- GPT-2 | `/v1/chat/gpt2`
- TinyLlama | `/v1/chat/tinyllama` 
- Phi-2 | `/v1/chat/phi2` 

### Planned Features

- **Autoscaling**: Dynamic replica scaling based on request queues on the vllm side taking SLO requriements into consideration.
- **Persistent Storage**:  Exploring storage options for head controller to deal with fault tolerance.
- **Distributed proxy**: Add distributed proxy features for better handling of requests



*(Note: Docker images may require environment specific configuration)*
