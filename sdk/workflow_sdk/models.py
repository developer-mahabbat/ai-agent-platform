from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowNode:
    id: str
    name: str
    type: str = "task"
    agent: str = ""
    tool: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    next_on_success: Optional[str] = None
    next_on_failure: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class WorkflowStep:
    id: str
    node_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    input: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    error: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class Workflow:
    id: str
    name: str
    nodes: list[WorkflowNode]
    steps: list[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
