import asyncio
import time
from datetime import datetime
import aiohttp
import json
from collections import defaultdict
import statistics
import os

# Test prompts - AI/ML focused for meaningful responses
PROMPTS = [
    "Explain machine learning algorithms in detail...",
    "Describe the architecture of neural networks...",
    "What are the applications of artificial intelligence?...",
    "How does deep learning differ from traditional ML?...",
    "Explain natural language processing techniques...",
    "What is computer vision and how does it work?...",
    "Describe reinforcement learning principles...",
    "How do recommendation systems function?...",
    "Explain the concept of transfer learning...",
    "What are generative adversarial networks?...",
    "Describe the evolution of AI technologies...",
    "How does feature engineering work in ML?...",
    "Explain gradient descent optimization...",
    "What are the challenges in AI deployment?...",
    "Describe ensemble learning methods...",
    "How does unsupervised learning work?...",
    "Explain the bias-variance tradeoff...",
    "What are attention mechanisms in AI?...",
    "Describe model evaluation techniques...",
    "How does federated learning work?..."
]

async def make_request(session, prompt, request_id):
    url = "http://18.215.152.157:8000/v1/chat/tinyllama"
    headers = {"Content-Type": "application/json"}
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "stream": True
    }

    start_time = time.time()
    first_token_time = None
    success = False
    error_msg = None
    full_response = ""

    try:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                success = True
                # --- CORRECTED CHUNK HANDLING ---
                # Use iter_any() to read raw bytes as they arrive
                async for chunk in response.content.iter_any():
                    if chunk:
                        if first_token_time is None:
                            first_token_time = time.time()
                        try:
                            # Decode the chunk of bytes into a string
                            full_response += chunk.decode('utf-8')
                        except UnicodeDecodeError:
                            # Handle cases where a multi-byte character might be split across chunks
                            # For this example, we'll ignore decode errors on partial chunks
                            pass
            else:
                error_msg = f"HTTP {response.status}"
                success = False

    except Exception as e:
        error_msg = str(e)
        success = False

    end_time = time.time()

    return {
        "request_id": request_id,
        "prompt": prompt,
        "response": full_response,
        "success": success,
        "error": error_msg,
        "start_time": start_time,
        "first_token_time": first_token_time,
        "end_time": end_time,
        "total_time": end_time - start_time,
        "first_token_latency": first_token_time - start_time if first_token_time else None
    }


async def run_test(num_requests=200):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_results_{timestamp}.json"
    
    print(f"\n🚀 Launching {num_requests} concurrent requests...")
    
    requests_to_make = [(i + 1, PROMPTS[i % len(PROMPTS)]) for i in range(num_requests)]
    
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, prompt, req_id) for req_id, prompt in requests_to_make]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    print("🏁 All requests completed.")
    
    # Process results
    successful = [r for r in results if isinstance(r, dict) and r["success"]]
    failed = [r for r in results if isinstance(r, dict) and not r["success"]]
    errors = [r for r in results if not isinstance(r, dict)]

    if successful:
        first_token_times = [r["first_token_latency"] for r in successful if r["first_token_latency"]]
        total_times = [r["total_time"] for r in successful]
        
        print("\n--- PERFORMANCE SUMMARY ---")
        print(f"✅ Successful Requests: {len(successful)}")
        print(f"❌ Failed Requests: {len(failed)}")
        print(f"⚠️  Errors: {len(errors)}")

        if first_token_times:
            print("\nTime to First Token (TTFT):")
            print(f"  • Average: {statistics.mean(first_token_times):.3f}s")
            print(f"  • Median:  {statistics.median(first_token_times):.3f}s")
            print(f"  • Min:     {min(first_token_times):.3f}s")
            print(f"  • Max:     {max(first_token_times):.3f}s")

        if total_times:
            print("\nTotal Request Time:")
            print(f"  • Average: {statistics.mean(total_times):.3f}s")
            print(f"  • Median:  {statistics.median(total_times):.3f}s")
            print(f"  • Min:     {min(total_times):.3f}s")
            print(f"  • Max:     {max(total_times):.3f}s")
            
            test_duration = max(r['end_time'] for r in results if isinstance(r, dict)) - min(r['start_time'] for r in results if isinstance(r, dict))
            print(f"\nOverall Throughput: {len(successful) / test_duration:.2f} requests/second")
            
    if failed or errors:
        print("\n--- ERROR DETAILS ---")
        for r in failed[:5]: # Show first 5 failed
            print(f"  • Failed Request #{r['request_id']}: {r['error']}")
        for e in errors[:5]: # Show first 5 errors
            print(f"  • Unexpected Client Error: {str(e)}")


async def main():
    await run_test(100)

if __name__ == "__main__":
    asyncio.run(main())