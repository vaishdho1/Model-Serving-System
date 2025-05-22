import asyncio
from collections import deque
from typing import Callable, Dict

class ActorStub:
    def __init__(self, actor_id: str):
        self.actor_id = actor_id

    async def execute_task(self, input_data: str) -> str:
        print(f"[Actor {self.actor_id}] Executing task with input: {input_data}")
        await asyncio.sleep(2)  # simulate I/O or model execution
        return f"Output for: {input_data}"

class HeadNodeStub:
    async def send_result(self, actor_id: str, output: str):
        print(f"[HeadNode] Got result from Actor {actor_id}: {output}")

class ActorManager:
    def __init__(self, headnode_stub: HeadNodeStub):
        self.actors: Dict[str, Dict] = {}
        self.headnode = headnode_stub

    def register_actor(self, actor_id: str):
        self.actors[actor_id] = {
            "stub": ActorStub(actor_id),
            "queue": deque(),
            "busy": False
        }
        print(f"[Raylet] Registered Actor {actor_id}")

    async def submit_task(self, actor_id: str, input_data: str):
        actor_state = self.actors[actor_id]
        actor_state["queue"].append(input_data)

        if not actor_state["busy"]:
            await self._dispatch_next(actor_id)

    async def _dispatch_next(self, actor_id: str):
        actor_state = self.actors[actor_id]
        queue = actor_state["queue"]

        if not queue:
            actor_state["busy"] = False
            return

        input_data = queue.popleft()
        actor_state["busy"] = True

        async def callback():
            output = await actor_state["stub"].execute_task(input_data)
            await self.headnode.send_result(actor_id, output)

            # Now dispatch next task if queue is not empty
            await self._dispatch_next(actor_id)

        asyncio.create_task(callback())

# --- Test ---
async def main():
    headnode = HeadNodeStub()
    raylet = ActorManager(headnode)

    raylet.register_actor("actor-1")

    # Submit multiple tasks asynchronously
    await raylet.submit_task("actor-1", "task-A")
    await raylet.submit_task("actor-1", "task-B")
    await raylet.submit_task("actor-1", "task-C")

    await asyncio.sleep(10)  # wait for all tasks to finish

asyncio.run(main())
