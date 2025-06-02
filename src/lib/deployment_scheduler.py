import asyncio
from src.lib.configurations import *

class DeploymentScheduler:
    def __init__(self, head_controller):
        self.scheduler_queue = asyncio.Queue()
        self.head_controller = head_controller
        asyncio.create_task(self.run_scheduler_loop())
    
    #This is the function which is called by the deployment manager to schedule the replicas
    def schedule_replicas(self, num_replicas, deployment_id, to_add):
        #Does this need to be async?
        self.scheduler_queue.put_nowait((num_replicas, deployment_id, to_add))
    
    async def run_scheduler_loop(self):
        while True:
            num_replicas, deployment_id, to_add = await self.scheduler_queue.get()
            #These are fire and forget
            if to_add:
                await self._start_replicas(num_replicas, deployment_id)
            else:
                await self._stop_replicas(num_replicas, deployment_id)
            await asyncio.sleep(scheduling_interval)
    
