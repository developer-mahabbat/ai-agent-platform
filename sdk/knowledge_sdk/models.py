from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class KnowledgeSource:
    url: str = ""
    title: str = ""
    snippet: str = ""
    source_type: str = "web"


@dataclass
class KnowledgeEntry:
    id: str
    query: str
    content: str
    sources: list[KnowledgeSource] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    relevance: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
