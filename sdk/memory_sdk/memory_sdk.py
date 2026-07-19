import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from ..base import SDKModule, SDKResult
from .models import Memory, MemoryEntry, MemoryType

logger = logging.getLogger(__name__)


class MemorySDK(SDKModule):
    name = "memory"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._sessions: dict[str, Memory] = {}

    async def initialize(self) -> None:
        logger.info("MemorySDK initializing")

    async def shutdown(self) -> None:
        self._sessions.clear()
        logger.info("MemorySDK shut down")

    async def store(
        self, session_id: str, content: str, mtype: MemoryType = MemoryType.CONVERSATION, **metadata: Any
    ) -> SDKResult[MemoryEntry]:
        if session_id not in self._sessions:
            self._sessions[session_id] = Memory(session_id=session_id)
        entry = MemoryEntry(
            id=f"mem_{uuid.uuid4().hex[:12]}",
            type=mtype,
            content=content,
            metadata=metadata,
        )
        self._sessions[session_id].entries.append(entry)
        logger.debug(f"Stored memory {entry.id} for session {session_id}")
        return SDKResult.ok(entry)

    async def retrieve(
        self, session_id: str, limit: int = 50, mtype: Optional[MemoryType] = None
    ) -> list[MemoryEntry]:
        memory = self._sessions.get(session_id)
        if not memory:
            return []
        entries = memory.entries
        if mtype:
            entries = [e for e in entries if e.type == mtype]
        return entries[-limit:]

    async def search(self, session_id: str, query: str, limit: int = 10) -> list[MemoryEntry]:
        memory = self._sessions.get(session_id)
        if not memory:
            return []
        query_lower = query.lower()
        scored = []
        for entry in memory.entries:
            score = 0
            if query_lower in entry.content.lower():
                score += entry.content.lower().count(query_lower)
            if query_lower in entry.summary.lower():
                score += 2
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 3
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    async def summarize(self, session_id: str) -> SDKResult[str]:
        memory = self._sessions.get(session_id)
        if not memory:
            return SDKResult.ok("")
        entries = memory.entries
        if not entries:
            return SDKResult.ok("")
        recent = entries[-20:]
        summary = f"Session has {len(entries)} total entries. Recent topics: "
        topics = set()
        for e in recent:
            words = e.content.split()[:5]
            topics.add(" ".join(words))
        summary += "; ".join(list(topics)[:5])
        memory.compressed = summary
        return SDKResult.ok(summary)

    async def clear(self, session_id: str) -> SDKResult:
        if session_id in self._sessions:
            self._sessions[session_id].entries.clear()
            return SDKResult.ok()
        return SDKResult.fail(f"Session {session_id} not found")

    async def delete_entry(self, entry_id: str) -> SDKResult:
        for memory in self._sessions.values():
            for i, entry in enumerate(memory.entries):
                if entry.id == entry_id:
                    memory.entries.pop(i)
                    return SDKResult.ok()
        return SDKResult.fail(f"Entry {entry_id} not found")
