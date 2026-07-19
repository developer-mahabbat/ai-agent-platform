import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class StreamSDK(SDKModule):
    name = "stream"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._subscribers: dict[str, list[Callable]] = {}
        self._streams: dict[str, asyncio.Queue] = {}

    async def initialize(self) -> None:
        logger.info("StreamSDK initialized")

    async def shutdown(self) -> None:
        self._subscribers.clear()
        self._streams.clear()
        logger.info("StreamSDK shut down")

    async def create_stream(self, stream_id: str) -> SDKResult:
        if stream_id in self._streams:
            return SDKResult.fail(f"Stream {stream_id} already exists")
        self._streams[stream_id] = asyncio.Queue()
        return SDKResult.ok()

    async def push(self, stream_id: str, event: str, data: Any) -> SDKResult:
        if stream_id not in self._streams:
            return SDKResult.fail(f"Stream {stream_id} not found")
        message = {"event": event, "data": data, "timestamp": datetime.utcnow().isoformat()}
        await self._streams[stream_id].put(message)

        for cb in self._subscribers.get(stream_id, []):
            try:
                await cb(message) if asyncio.iscoroutinefunction(cb) else cb(message)
            except Exception as e:
                logger.error(f"Subscriber error on {stream_id}: {e}")

        return SDKResult.ok()

    async def subscribe(self, stream_id: str, callback: Callable) -> SDKResult:
        self._subscribers.setdefault(stream_id, []).append(callback)
        return SDKResult.ok()

    async def unsubscribe(self, stream_id: str, callback: Callable) -> SDKResult:
        if stream_id in self._subscribers:
            self._subscribers[stream_id] = [cb for cb in self._subscribers[stream_id] if cb != callback]
        return SDKResult.ok()

    async def stream(self, stream_id: str) -> AsyncIterator[dict[str, Any]]:
        if stream_id not in self._streams:
            self._streams[stream_id] = asyncio.Queue()
        queue = self._streams[stream_id]
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30)
                yield message
            except asyncio.TimeoutError:
                yield {"event": "keepalive", "data": None}
                continue

    async def broadcast(self, event: str, data: Any) -> None:
        for stream_id in self._streams:
            await self.push(stream_id, event, data)

    async def sse_format(self, stream_id: str) -> AsyncIterator[str]:
        async for message in self.stream(stream_id):
            yield f"event: {message['event']}\ndata: {json.dumps(message['data'])}\n\n"
