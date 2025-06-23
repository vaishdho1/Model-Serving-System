import time
import grpc
import asyncio
import requests
import logging
import random

from urllib import request, error
async def try_send_with_retries(coro_func, *args, num_attempts=3, delay_seconds=3, backoff_factor=2, max_delay=10, jitter=True, **kwargs):
    """Helper function to retry an async operation that might raise grpc.RpcError."""
    last_exception = None
    current_delay = delay_seconds

    for attempt in range(1, num_attempts + 1):
        try:
            # For logging, getattr helps get the name of the function being called
            func_name = getattr(coro_func, '__name__', 'rpc_call')
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} calling '{func_name}'...")
            
            return await coro_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} failed: {e}")

            if attempt < num_attempts:
                # Calculate the backoff delay for the next attempt
                backoff_delay = current_delay
                if jitter:
                    # Add jitter: a random value between 0 and the current delay
                    backoff_delay += random.uniform(0, current_delay)
                
                print(f"[RetryHelper] Retrying in {backoff_delay:.2f} seconds...")
                await asyncio.sleep(backoff_delay)
                
                # Increase the delay for the next potential failure, capped at max_delay
                current_delay = min(current_delay * backoff_factor, max_delay)
            
    print(f"[RetryHelper] All {num_attempts} attempts failed. Returning last exception.")
    return last_exception

    
def try_send_with_retries_sync(coro_func, *args, num_attempts=3, delay_seconds=2, timeout=None, **kwargs):
    """Helper function to retry an async operation that might raise grpc.RpcError."""
    last_exception = None
    for attempt in range(1, num_attempts + 1):
        try:
            return coro_func(*args, timeout=timeout, **kwargs)
        except grpc.RpcError as e:
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} failed for {getattr(coro_func, '__name__', 'rpc_call')}: {e.code()} - {e.details()}")
            last_exception = e
            if attempt < num_attempts:
                print(f"[RetryHelper] Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
        # Consider if other exceptions should be caught and retried, or allowed to propagate immediately.
    
    return None
def send_with_delay(coro_func, *args, num_attempts=3, delay_seconds=2, **kwargs):
    """Helper function to retry an async operation that might raise grpc.RpcError."""
    last_exception = None
    for attempt in range(1, num_attempts + 1):
        try:
            #print(f"[RetryHelper] Attempt {attempt}/{num_attempts} calling {coro_func.__name__}") # Optional: for more verbose logging
            return coro_func(*args, **kwargs)
        except grpc.RpcError as e:
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} failed for {getattr(coro_func, '__name__', 'rpc_call')}: {e.code()} - {e.details()}")
            last_exception = e
            if attempt < num_attempts:
                print(f"[RetryHelper] Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
        # Consider if other exceptions should be caught and retried, or allowed to propagate immediately.
    
    return None



def get_gcp_internal_ip() -> str:
    """
    Queries the GCP metadata server to get the VM's internal IP address.
    """
    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip"
    metadata_header = {"Metadata-Flavor": "Google"}
    
    try:
        logging.info("Querying metadata server for internal IP address...")
        response = requests.get(metadata_url, headers=metadata_header, timeout=2)
        response.raise_for_status()  # Raise an exception for bad status codes
        internal_ip = response.text
        logging.info(f"Successfully discovered internal IP: {internal_ip}")
        return internal_ip
    except requests.exceptions.RequestException as e:
        logging.error(f"Could not connect to GCP metadata server: {e}. Are you running on a GCP VM? Defaulting to 'localhost'.")
        # Provide a fallback for local testing
        return "localhost"

def get_aws_internal_ip() -> str:
    """
    Queries the AWS EC2 metadata server using only Python's standard library.
    """
    token_url = "http://169.254.169.254/latest/api/token"
    ip_url = "http://169.254.169.254/latest/meta-data/local-ipv4"

    try:
        # 1. Get a session token (IMDSv2)
        token_headers = {'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
        # For a PUT request, we must create a Request object
        req = request.Request(token_url, headers=token_headers, method='PUT')
        with request.urlopen(req, timeout=2) as response:
            token = response.read().decode('utf-8')

        # 2. Use the token to get the IP address
        ip_headers = {'X-aws-ec2-metadata-token': token}
        req = request.Request(ip_url, headers=ip_headers)
        with request.urlopen(req, timeout=2) as response:
            private_ip = response.read().decode('utf-8')
            return private_ip

    except error.URLError as e:
        print(f"Could not connect to AWS metadata server with urllib: {e}. Defaulting to 'localhost'.")
        return "localhost"
