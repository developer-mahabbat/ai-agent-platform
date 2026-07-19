import json
import logging
import time
from datetime import datetime
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class TelemetrySDK(SDKModule):
    name = "telemetry"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._events: list[dict[str, Any]] = []
        self._metrics: dict[str, Any] = {
            "total_chats": 0,
            "total_messages": 0,
            "total_tool_calls": 0,
            "total_errors": 0,
            "total_tokens": 0,
            "started_at": datetime.utcnow().isoformat(),
        }
        self._timers: dict[str, float] = {}
        self._max_events: int = 10000

    async def initialize(self) -> None:
        logger.info("TelemetrySDK initialized")

    async def shutdown(self) -> None:
        self._events.clear()
        logger.info("TelemetrySDK shut down")

    async def track_event(self, category: str, action: str, label: str = "", value: float = 0.0, metadata: dict[str, Any] | None = None) -> SDKResult:
        event = {
            "category": category,
            "action": action,
            "label": label,
            "value": value,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events.pop(0)

        if category == "chat":
            self._metrics["total_chats"] += 1
        elif category == "message":
            self._metrics["total_messages"] += 1
        elif category == "tool":
            self._metrics["total_tool_calls"] += 1
        elif category == "error":
            self._metrics["total_errors"] += 1
        elif category == "token":
            self._metrics["total_tokens"] += int(value)

        return SDKResult.ok()

    def start_timer(self, name: str) -> None:
        self._timers[name] = time.time()

    def stop_timer(self, name: str) -> float:
        start = self._timers.pop(name, None)
        if start is None:
            return 0.0
        return (time.time() - start) * 1000

    async def get_metrics(self) -> dict[str, Any]:
        return dict(self._metrics)

    async def get_events(self, category: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        if category:
            return [e for e in self._events if e["category"] == category][-limit:]
        return self._events[-limit:]

    async def reset(self) -> None:
        self._events.clear()
        self._metrics = {
            "total_chats": 0,
            "total_messages": 0,
            "total_tool_calls": 0,
            "total_errors": 0,
            "total_tokens": 0,
            "started_at": datetime.utcnow().isoformat(),
        }
