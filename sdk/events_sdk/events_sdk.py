import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class EventSDK(SDKModule):
    name = "events"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._handlers: dict[str, list[Callable]] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history: int = 1000

    async def initialize(self) -> None:
        logger.info("EventSDK initialized")

    async def shutdown(self) -> None:
        self._handlers.clear()
        self._history.clear()
        logger.info("EventSDK shut down")

    def on(self, event: str, handler: Callable) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable) -> None:
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    async def emit(self, event: str, data: Any = None) -> None:
        entry = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for handler in self._handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(entry)
                else:
                    handler(entry)
            except Exception as e:
                logger.error(f"Handler error for event '{event}': {e}")

        for wildcard_handler in self._handlers.get("*", []):
            try:
                if asyncio.iscoroutinefunction(wildcard_handler):
                    await wildcard_handler(entry)
                else:
                    wildcard_handler(entry)
            except Exception as e:
                logger.error(f"Wildcard handler error: {e}")

    async def history(self, event: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
        if event:
            return [e for e in self._history if e["event"] == event][-limit:]
        return self._history[-limit:]

    async def clear_history(self) -> None:
        self._history.clear()
