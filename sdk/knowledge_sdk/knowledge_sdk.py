import logging
import uuid
from typing import Any, Optional

from ..base import SDKModule, SDKResult
from .models import KnowledgeEntry, KnowledgeSource

logger = logging.getLogger(__name__)


class KnowledgeSDK(SDKModule):
    name = "knowledge"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._entries: list[KnowledgeEntry] = []
        self._max_entries: int = 1000

    async def initialize(self) -> None:
        logger.info("KnowledgeSDK initialized")

    async def shutdown(self) -> None:
        self._entries.clear()
        logger.info("KnowledgeSDK shut down")

    async def store(self, query: str, content: str, sources: list[KnowledgeSource] | None = None, tags: list[str] | None = None) -> SDKResult[KnowledgeEntry]:
        if len(self._entries) >= self._max_entries:
            self._entries.pop(0)
        entry = KnowledgeEntry(
            id=f"know_{uuid.uuid4().hex[:12]}",
            query=query,
            content=content,
            sources=sources or [],
            tags=tags or [],
        )
        self._entries.append(entry)
        return SDKResult.ok(entry)

    async def search(self, query: str, limit: int = 10) -> list[KnowledgeEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self._entries:
            score = 0
            if query_lower in entry.query.lower():
                score += 5
            if query_lower in entry.content.lower():
                score += entry.content.lower().count(query_lower)
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 3
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    async def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        for e in self._entries:
            if e.id == entry_id:
                return e
        return None

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[KnowledgeEntry]:
        return self._entries[offset:offset + limit]

    async def delete(self, entry_id: str) -> SDKResult:
        for i, e in enumerate(self._entries):
            if e.id == entry_id:
                self._entries.pop(i)
                return SDKResult.ok()
        return SDKResult.fail(f"Entry {entry_id} not found")

    async def clear(self) -> SDKResult:
        self._entries.clear()
        return SDKResult.ok()

    async def count(self) -> int:
        return len(self._entries)
