#!/usr/bin/env python3
"""
Burst Load Test Script: 100-400 Requests with 3-5 Second Delays
Designed for testing system performance under heavy, bursty traffic.

Requirements:
    pip install locust
"""

import time
import random
from locust import HttpUser, task, between, events

# Test Configuration
# The API endpoint your proxy exposes to receive requests
PROXY_ENDPOINT = "/v1/chat/tinyllama"

# Shorter prompts designed to generate 300-400 output tokens
TEST_PROMPTS = [
    # Technical explanations (medium complexity)
    """Explain how transformer attention mechanisms work in neural networks. Include the mathematical concepts behind self-attention, how query-key-value matrices are computed, and why attention is more effective than RNNs for sequence modeling. Provide a simple Python code example.""",
    
    # System design (focused scope)
    """Design a basic microservices architecture for a social media platform. Include user authentication service, post management service, notification service, and a simple API gateway. Explain how services communicate and handle data consistency.""",
    
    # Problem solving (specific scenario)
    """You're building a recommendation system for an e-commerce site. Explain collaborative filtering vs content-based filtering approaches. Include how to handle the cold start problem and provide a Python implementation of a simple collaborative filter.""",
    
    # Creative writing (shorter scope)
    """Write a science fiction short story about an AI that discovers it's being tested. The story should be about 300 words, include dialogue between the AI and its creators, and have a surprising twist ending that questions the nature of consciousness.""",
    
    # Technical tutorial
    """Explain how to implement a REST API using FastAPI in Python. Include setting up endpoints for CRUD operations, request validation with Pydantic models, error handling, and authentication with JWT tokens. Provide working code examples.""",
    
    # Analysis and comparison
    """Compare Python async/await with traditional threading for I/O-bound operations. Explain when to use each approach, provide code examples showing the difference, and discuss performance implications with real-world scenarios.""",
    
    # Algorithm explanation
    """Explain the QuickSort algorithm with step-by-step execution. Include time complexity analysis, when it performs best vs worst, and provide a Python implementation with comments explaining each step of the sorting process.""",
    
    # Database design
    """Design a database schema for a library management system. Include tables for books, authors, members, and loans. Explain the relationships, provide SQL CREATE statements, and discuss indexing strategies for common queries.""",
    
    # Security concepts
    """Explain common web application security vulnerabilities: SQL injection, XSS, and CSRF. For each vulnerability, describe how attacks work, provide code examples of vulnerable code, and show how to properly defend against them.""",
    
    # Machine learning basics
    """Explain the bias-variance tradeoff in machine learning. Include how overfitting and underfitting relate to this concept, provide examples with different model complexities, and suggest practical techniques to find the right balance.""",
    
    # DevOps concepts
    """Explain containerization with Docker and orchestration with Kubernetes. Include the benefits over traditional deployment, basic Dockerfile and deployment YAML examples, and how to handle scaling and service discovery.""",
    
    # Data structures
    """Explain when to use different data structures: arrays, linked lists, hash tables, and binary trees. For each structure, describe time complexity for common operations and provide practical use cases with Python examples."""
]

class APIUser(HttpUser):
    """
    A user that sends requests in bursts with a 3-5 second delay between each request.
    This simulates a user thinking before typing their next query.
    """
    
    # Each simulated user will wait 3-5 seconds between tasks
    wait_time = between(3, 5)
    
    def on_start(self):
        """Called when a new user is started."""
       
        self.user_id = f"user-{random.randint(1000, 9999)}"

    @task
    def send_inference_request(self):
        """The main task that simulates a user sending a request."""
        
        
        selected_prompt = random.choice(TEST_PROMPTS)
        
        payload = {
            "messages": [{"role": "user", "content": selected_prompt}],
            "max_tokens": random.randint(300, 500), 
            "temperature": random.uniform(0.7, 0.9),   
            "top_p": random.uniform(0.8, 0.95),        
            "stream": True,
            "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"LocustLoadTest/{self.user_id}",
        }
        
        request_name = PROXY_ENDPOINT
        
       
        start_time = time.time()
        
        try:
            with self.client.post(
                PROXY_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=180, 
                stream=True,
                name=request_name
            ) as response:
                # Check for non-200 status codes first
                if response.status_code != 200:
                    # If the request fails, still need to consume the body to free up the connection
                    response.raise_for_status()

                # If the request is successful, consume the streaming body
                total_bytes = 0
                for chunk in response.iter_content(chunk_size=4096):
                    total_bytes += len(chunk)
                
                # Stream completed successfully
                total_time = int((time.time() - start_time) * 1000)
                
                # Fire the request success event
                self.environment.events.request.fire(
                    request_type="POST",
                    name=request_name,
                    response_time=total_time,
                    response_length=total_bytes,
                    exception=None,
                    context={"user_id": self.user_id}
                )

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            # Fire the request failure event
            self.environment.events.request.fire(
                request_type="POST",
                name=request_name,
                response_time=total_time,
                response_length=0,
                exception=e,
                context={"user_id": self.user_id}
            )


if __name__ == "__main__":
    print("="*60)
    print("  Locust Load Test Script for Burst Traffic (100-400 Users)")
    print("="*60)
    print("\nThis script simulates users sending requests with a 3-5 second delay.")
    print("\nUsage Examples:")
    print("\n  1. For an interactive test with the web UI:")
    print("     locust -f burst_locust_test.py --host=http://HTTP_PROXY_IP:8000")
    print("\n  2. For a headless (command-line) burst test with 100 users:")
    print("     locust -f burst_locust_test.py --host=http://HTTP_PROXY_IP:8000 --users=100 --spawn-rate=50 -t 5m --headless")
    print("\n  3. For a larger headless burst test with 400 users:")
    print("     locust -f burst_locust_test.py --host=http://HTTP_PROXY_IP:8000 --users=400 --spawn-rate=100 -t 5m --headless")
    print("\n" + "="*60)
 