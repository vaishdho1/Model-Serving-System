import asyncio
import time

async def slow_task():
    await asyncio.sleep(5)
    print(f"Slow done at {time.time()}")

async def fast_loop():
    while True:
        print(f"Heartbeat at {time.time()}")
        await asyncio.sleep(4)

async def main():
    asyncio.create_task(fast_loop())
    for _ in range(3):
        await slow_task()

asyncio.run(main())
