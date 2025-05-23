# future_manager.py

import asyncio
from typing import Dict, Any


class FutureManager:
    def __init__(self):
        self._futures: Dict[Any, asyncio.Future] = {}

    def create_future(self, key: Any) -> asyncio.Future:
        """Create a future associated with the given key."""
        if key in self._futures:
            raise RuntimeError(f"Future already exists for key: {key}")
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._futures[key] = fut
        return fut

    def get_future(self, key: Any) -> asyncio.Future:
        return self._futures.get(key)

    def set_result(self, key: Any, value: Any):
        fut = self._futures.pop(key, None)
        if fut and not fut.done():
            fut.set_result(value)

    def set_exception(self, key: Any, exc: Exception):
        fut = self._futures.pop(key, None)
        if fut and not fut.done():
            fut.set_exception(exc)

    def cancel_future(self, key: Any):
        fut = self._futures.pop(key, None)
        if fut and not fut.done():
            fut.cancel()

    def has_future(self, key: Any) -> bool:
        return key in self._futures

    def pop(self, key: Any) -> asyncio.Future:
        return self._futures.pop(key, None)
