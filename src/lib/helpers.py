import time
import grpc
import asyncio
async def try_send_with_retries(coro_func, *args, num_attempts=3, delay_seconds=2, **kwargs):
    """Helper function to retry an async operation that might raise grpc.RpcError."""
    last_exception = None
    for attempt in range(1, num_attempts + 1):
        try:
            #print(f"[RetryHelper] Attempt {attempt}/{num_attempts} calling {coro_func.__name__}") # Optional: for more verbose logging
            return await coro_func(*args, **kwargs)
        except Exception as e:  # Catch ALL exceptions, not just grpc.RpcError
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} failed for {getattr(coro_func, '__name__', 'rpc_call')}: {type(e).__name__}: {e}")
            last_exception = e
            if attempt < num_attempts:
                print(f"[RetryHelper] Retrying in {delay_seconds} seconds...")
        await asyncio.sleep(delay_seconds)
        # Consider if other exceptions should be caught and retried, or allowed to propagate immediately.
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