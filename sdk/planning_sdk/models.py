from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PlanTask:
    id: str
    title: str
    description: str = ""
    status: PlanStatus = PlanStatus.DRAFT
    priority: PlanPriority = PlanPriority.MEDIUM
    assigned_agent: str = ""
    dependencies: list[str] = field(default_factory=list)
    result: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class Plan:
    id: str
    goal: str
    tasks: list[PlanTask] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
