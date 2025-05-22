# Model Serving System

## Overview

This project implements a distributed model serving system designed to manage and serve machine learning models efficiently. It consists of a head node for coordination, scheduler nodes that manage replica processes, and the replica processes themselves which are responsible for running models. The system uses gRPC for communication between components and focuses on robustness, including health checks, fault tolerance, and dynamic replica management. ***This system is currently in the active development stage.***

## Core Features Implemented

*   **Distributed Architecture Foundation:** Basic structure for a head node, scheduler nodes, and replica instances.
*   **Dynamic Replica Creation:** Schedulers can create new model serving replicas (`add_replica.py` processes) on demand via gRPC calls.
*   **Task Forwarding Mechanism:** Client requests can be sent to schedulers, which then route them to appropriate `Replica` abstractions that manage communication with the actual replica processes.
*   **Inter-Component Communication:** gRPC is used for all primary communication pathways (Client <-> Scheduler, Scheduler <-> Head Node, Scheduler <-> Replica Process).
*   **Basic Health Monitoring:**
    *   Replicas send periodic health updates to their parent scheduler.
    *   Schedulers send periodic health updates (including aggregated replica states) to the head node.
    *   Schedulers can ping their managed replicas.
*   **Initial Fault Tolerance Concepts:**
    *   Replicas can terminate themselves if the scheduler NACKs their health update.
    *   Schedulers detect ping failures to replicas and can mark them as dead, subsequently cleaning them from the active registry.
    *   Retry mechanisms are implemented for some gRPC calls.
*   **Concurrency:** Utilizes `asyncio` for non-blocking operations.
*   **Protected Shared Resources:** Employs `asyncio.Lock` for thread-safe operations on critical shared data like the `replica_registry`.
*   **Separated Logging:** Output from individual replica processes is redirected to dedicated log files (`replica_<id>.log`).
*   **Client Simulation:** `dummy_server.py` includes a `client_side_calls` function to simulate parallel client requests for testing.

## Architecture & Components

The system is primarily composed of the following parts:

1.  **Head Node (`dummy_server.py` - Simplified Test Implementation, actual implementation is ongoing)**
    *   Acts as a basic central point for scheduler registration and receiving health updates.
    *   *Includes client-side logic (`client_side_calls`) for testing interactions with the scheduler.*

2.  **Scheduler Node (`scheduler.py`)**
    *   Manages a pool of replica processes.
    *   Registers with the Head Node.
    *   Sends its health and aggregated replica status to the Head Node.
    *   Manages `CreateReplica` and `SendRequest` RPCs from clients/head node.
    *   Manages `RegisterReplica` and `sendHealthupdate` RPCs from replica processes.
    *   Contains `Replica` class instances (from `replica.py`) to manage individual replica interactions.

3.  **Replica Process (`add_replica.py`)**
    *   An individual model server instance, started as a subprocess by `scheduler.py`.
    *   Registers with its parent scheduler and sends periodic health updates.
    *   Responds to pings and executes `PushTask` RPCs (model inference placeholder).

4.  **Replica Abstraction (`replica.py`)**
    *   `Replica` class: Used by `scheduler.py` to represent and manage communication with an `add_replica.py` process, including task queuing and result futures.

5.  **Protobuf Definitions(Doesnt capture the entire functionality yet)**
    *   `headnode-service.proto`: Defines gRPC for Scheduler <-> Head Node and Client <-> Scheduler interactions.
    *   `worker-service.proto`: Defines gRPC for Scheduler <-> Replica Process interactions.

6.  **Supporting Modules**
    *   `configurations.py`: For storing timing values for communication.
    *   `headstore_client.py`: Client utility for head node communication.
    *   `future_manager.py`: Manages `asyncio.Future` objects.

## Communication Protocol

*   All inter-process communication is via **gRPC**.
*   Message structures are defined using **Protocol Buffers**.

## Logging(Under development)

*   Scheduler (`scheduler.py`) and Head Node (`dummy_server.py`) log to their terminals.
*   Replica Processes (`add_replica.py`) log to `replica_<REPLICA_ID>.log` files.

## Upcoming Features / Future Work

*   **Actual Model Loading & Inference:** Integrate a real model loading mechanism (e.g., Hugging Face Transformers, VLLM) into `add_replica.py`'s `load_and_run_model` function.
*   **Load Balancing:** Implement strategies in the scheduler for distributing `SendRequest` calls among available healthy replicas (e.g., round-robin, least busy).
*   **More Sophisticated Head Node:** Develop the head node beyond a simple test server, including features like:
    *   Persistent storage of cluster state.
    *   A user-facing API or dashboard for cluster management.
    *   Global policies for replica scaling.
    *    Enhance the scheduler to consider resource availability (CPUs, GPUs, memory) when deciding where and if to create new replicas.
    *   Load balancing : Implement startegies in the scheduler for calls among available replicas
*   *   Replica Auto-Scaling: Allow schedulers or the head node to automatically scale the number of replicas up or down based on load or other metrics.
*   **Robust Error Handling & Reporting:** Standardize error propagation and reporting across all gRPC calls and components.
*   **Configuration Management:** Centralize and improve management of configurable parameters (ports, intervals, resource types) possibly via `configurations.py` or external config files.
*   **Dependency Management:** Create a `requirements.txt` file to list and manage Python package dependencies.
*   **Graceful Shutdown:** Implement more thorough graceful shutdown procedures for all components, ensuring tasks are completed or safely terminated.
*   **Security:** Consider security aspects like secure gRPC channels (TLS) if the system were to be deployed in a non-trusted environment.
*   **Comprehensive Testing:** Develop unit and integration tests for various components and scenarios.
*   **Metrics Collection & Monitoring:** Integrate a system for collecting metrics (e.g., request latency, queue lengths, resource utilization) and potentially visualizing them.



*(Note: The files are not ready for deployment yet. Running these would cause errors)* 
