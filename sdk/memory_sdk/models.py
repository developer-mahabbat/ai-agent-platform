from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    SESSION = "session"
    WORKSPACE = "workspace"
    PROJECT = "project"
    PINNED = "pinned"
    KNOWLEDGE = "knowledge"
    SEMANTIC = "semantic"
    COMPRESSED = "compressed"


@dataclass
class MemoryEntry:
    id: str
    type: MemoryType
    content: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class Memory:
    session_id: str
    entries: list[MemoryEntry] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    compressed: str = ""
