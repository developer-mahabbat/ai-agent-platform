from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AgentRole(str, Enum):
    ASSISTANT = "assistant"
    SUPERVISOR = "supervisor"
    PLANNER = "planner"
    REASONER = "reasoner"
    CODER = "coder"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"
    RESEARCHER = "researcher"
    BROWSER = "browser"
    MEMORY = "memory"
    VISION = "vision"
    DOCUMENT = "document"
    WORKSPACE = "workspace"
    KNOWLEDGE = "knowledge"
    RETRIEVAL = "retrieval"
    SEARCH = "search"
    TASK = "task"
    REFLECTION = "reflection"
    EXECUTION = "execution"
    ROUTER = "router"
    SECURITY = "security"
    QUALITY = "quality"


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    REVIEWING = "reviewing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class AgentConfig:
    role: AgentRole
    model: str = "openai/gpt-4o"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 4096
    max_retries: int = 3
    timeout: int = 120
    streaming: bool = True
    memory_enabled: bool = True
    tool_permissions: list[str] = field(default_factory=lambda: ["*"])
    retry_policy: dict[str, Any] = field(default_factory=lambda: {"exponential_backoff": True, "max_delay": 60})
    system_prompt: str = ""
    instructions: list[str] = field(default_factory=list)


@dataclass
class Agent:
    id: str
    name: str
    role: AgentRole
    config: AgentConfig
    state: AgentState = AgentState.IDLE
    context: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
