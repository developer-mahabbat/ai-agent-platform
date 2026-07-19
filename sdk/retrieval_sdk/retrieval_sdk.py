import logging
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class RetrievalSDK(SDKModule):
    name = "retrieval"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._index: dict[str, list[dict[str, Any]]] = {}
        self._storage_backend = "memory"

    async def initialize(self) -> None:
        logger.info(f"RetrievalSDK initialized (backend: {self._storage_backend})")

    async def shutdown(self) -> None:
        self._index.clear()
        logger.info("RetrievalSDK shut down")

    async def index_document(self, doc_id: str, content: str, metadata: dict[str, Any] | None = None) -> SDKResult:
        words = content.lower().split()
        for word in set(words):
            if word not in self._index:
                self._index[word] = []
            entry = {"doc_id": doc_id, "metadata": metadata or {}}
            if entry not in self._index[word]:
                self._index[word].append(entry)
        logger.debug(f"Indexed document {doc_id}")
        return SDKResult.ok()

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        words = query.lower().split()
        scores: dict[str, float] = {}
        doc_meta: dict[str, dict] = {}
        for word in words:
            for entry in self._index.get(word, []):
                doc_id = entry["doc_id"]
                scores[doc_id] = scores.get(doc_id, 0) + 1
                doc_meta[doc_id] = entry["metadata"]
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {"doc_id": doc_id, "score": score, "metadata": doc_meta.get(doc_id, {})}
            for doc_id, score in ranked[:limit]
        ]

    async def remove_document(self, doc_id: str) -> SDKResult:
        removed = 0
        for word in list(self._index.keys()):
            before = len(self._index[word])
            self._index[word] = [e for e in self._index[word] if e["doc_id"] != doc_id]
            removed += before - len(self._index[word])
            if not self._index[word]:
                del self._index[word]
        return SDKResult.ok({"removed": removed})

    async def clear_index(self) -> SDKResult:
        self._index.clear()
        return SDKResult.ok()

    async def index_size(self) -> int:
        return sum(len(entries) for entries in self._index.values())
