import logging
from pathlib import Path
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class DocumentSDK(SDKModule):
    name = "document"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._documents: dict[str, dict[str, Any]] = {}
        self._supported_extensions: set[str] = {".md", ".txt", ".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv", ".sql", ".sh", ".dockerfile", ".env"}

    async def initialize(self) -> None:
        logger.info("DocumentSDK initialized")

    async def shutdown(self) -> None:
        self._documents.clear()
        logger.info("DocumentSDK shut down")

    async def create(self, doc_id: str, title: str, content: str = "", doc_type: str = "markdown") -> SDKResult:
        self._documents[doc_id] = {
            "id": doc_id,
            "title": title,
            "content": content,
            "type": doc_type,
            "metadata": {},
        }
        return SDKResult.ok()

    async def read(self, doc_id: str) -> Optional[dict[str, Any]]:
        return self._documents.get(doc_id)

    async def update(self, doc_id: str, content: str) -> SDKResult:
        if doc_id not in self._documents:
            return SDKResult.fail(f"Document '{doc_id}' not found")
        self._documents[doc_id]["content"] = content
        return SDKResult.ok()

    async def delete(self, doc_id: str) -> SDKResult:
        if doc_id in self._documents:
            del self._documents[doc_id]
            return SDKResult.ok()
        return SDKResult.fail(f"Document '{doc_id}' not found")

    async def search(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for doc in self._documents.values():
            if query_lower in doc["title"].lower() or query_lower in doc["content"].lower():
                results.append(doc)
        return results

    async def list_all(self) -> list[dict[str, Any]]:
        return list(self._documents.values())

    async def import_file(self, filepath: str) -> SDKResult:
        path = Path(filepath)
        if not path.exists():
            return SDKResult.fail(f"File not found: {filepath}")
        if path.suffix.lower() not in self._supported_extensions:
            return SDKResult.fail(f"Unsupported file type: {path.suffix}")
        content = path.read_text(encoding="utf-8")
        doc_id = f"doc_{path.stem}"
        await self.create(doc_id, path.name, content)
        return SDKResult.ok()

    async def export_file(self, doc_id: str, output_path: str) -> SDKResult:
        doc = self._documents.get(doc_id)
        if not doc:
            return SDKResult.fail(f"Document '{doc_id}' not found")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(doc["content"], encoding="utf-8")
        return SDKResult.ok()
