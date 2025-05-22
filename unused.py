async def _dispatch_next(self, replica_id: str):

        if not replica_registry[replica_id]:
            # No tasks in the queue, set status to idle
            replica_registry[replica_id].status = "idle"
            return
        
        replica_registry[replica_id].status = "busy"
        input_data = replica_registry[replica_id].replica_queue.popleft()
        async def message_callback():
            output = await replica_registry[replica_id].stub.PushTask(input_data)
            # I want to send the reply back to the head node
            await self.gcs_client._stub.sendReplicaReply(output)
            await self._dispatch_next(replica_id)
        asyncio.create_task(message_callback())