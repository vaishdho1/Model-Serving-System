# Model Serving System

## Overview

This project implements a **basic functional** distributed model serving system designed to manage and serve LLMs efficiently. The system consists of a head controller for coordination, scheduler nodes that manage replica processes, HTTP proxy for client access, and replica processes that run actual models. The system uses gRPC for internal communication and HTTP for client access, with robust fault tolerance, automatic restart capabilities, and support for multiple deployment scenarios.

## Current Status: **BASIC FULL FLOW UP** 
The system is not fully ready but the basic functionalities are up.

## Core Features Implemented

### **Architecture & Communication**
- **Distributed Architecture**: Head controller, schedulers, HTTP proxy, and replica processes
- **Multi-Protocol Support**: gRPC for internal communication, HTTP/REST for client access
- **Streaming Responses**: Real-time token-by-token model output streaming
- **Dynamic Replica Management**: Automatic creation and scaling of model replicas

### **Model Support**
- **Multiple Models**:Basic testing with GPT-2, TinyLlama, Phi-2, Mistral-7B, CodeLlama, Llama-2
- **Configurable Parameters**: Temperature, max_length, top_p per model
- **Model Configuration Management**: Centralized config via `model_configs.json`

### **Network & Deployment**
- **Machine Deployment**: Multiple machines running each service
- **Same Network Deployment**: Components across local network (10.0.0.x)
- **Client Access**: HTTP API on port 8000 with streaming support

### **Fault Tolerance & Health Management**
- **Health Monitoring**: Comprehensive health checks across all components
- **Automatic Restart**: HTTP proxy auto-restart on failure
- **Dead Replica Detection**: Automatic cleanup of failed replicas
- **Retry Mechanisms**: Robust retry logic with exponential backoff
- **Exception Handling**: Comprehensive error handling and recovery

### **Bring up**
- **Setup**: Installation of dependencies with `pip install -r requirements.txt`


## Architecture & Components

### 1. **Head Controller** (`src/components/headNode/head_controller.py`)
- Central coordination and management
- Deployment lifecycle management
- Routing table distribution to proxies
- Worker node registration and health monitoring

### 2. **HTTP Proxy** (`src/components/headNode/http_proxy.py`)
- Client-facing HTTP/REST API
- Request routing to appropriate replicas
- Streaming response handling
- **Auto-restart**: Automatic recovery on failure

### 3. **Scheduler** (`src/components/scheduler.py`)
- Replica process management
- Resource allocation and monitoring
- Health status aggregation and reporting

### 4. **Replica Process** (`src/components/add_replica.py`)
- Actual model loading and inference
- Streaming token generation
- **Real Models**: Hugging Face Transformers integration
- Model-specific configuration support

### 5. **Supporting Libraries**
- **Model Config** (`src/lib/model_config.py`): Centralized model management
- **Deployment Manager**: Replica lifecycle and routing
- **Health Manager**: System-wide health monitoring

### Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

### Single Machine Deployment
```bash
# Terminal 1: Start Head Controller
python3 -m src.components.headNode.head_controller --http_port=8000 --node_port=50051 --grpc_port=50052

# Terminal 2: Start Scheduler
python3 -m src.components.scheduler --node_id=1 --head_address=localhost --port=50051 --num_cpus=2 --num_gpus=0

```
## Client Usage

### Simple Request
```bash
curl -X POST http://localhost:8000/v1/chat/tinyllama \
  -H "Content-Type: text/plain" \
  -d "Hello! How are you?" \
  --no-buffer
```
## Available Models & Endpoints

- GPT-2 | `/v1/chat/gpt2`
- TinyLlama | `/v1/chat/tinyllama` 
- Phi-2 | `/v1/chat/phi2` 
- CodeLlama | `/v1/code/codellama` 
 |

### Logging Files
- `proxy.log`: HTTP proxy activity
- `replica_N.log`: Individual replica logs
- Terminal output: Real-time system status


### Planned Features

- **Auto-scaling**: Dynamic replica scaling based on load
- **Cloud-Integration** - Deploy the application on cloud with dynamic scheduling.
- **Streaming-Rate** - Adding batched implementation for faster streaming
- **Persistent-Storage** -Adding persistent storage for head-controller to deal with fault tolerance
- **Smarter LoadBalancing** - Adding better load balancing techniques
- **Container Deployment**: Docker and Kubernetes support
- **Model-Enhancement** - Add support for bigger models and use GPU integration




*(Note: The files are not ready for deployment yet. Running these would only bring basic flow)* 
