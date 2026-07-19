import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from ..base import SDKModule, SDKResult
from .models import Plan, PlanPriority, PlanStatus, PlanTask

logger = logging.getLogger(__name__)


class PlanningSDK(SDKModule):
    name = "planning"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._plans: dict[str, Plan] = {}

    async def initialize(self) -> None:
        logger.info("PlanningSDK initialized")

    async def shutdown(self) -> None:
        self._plans.clear()
        logger.info("PlanningSDK shut down")

    async def create_plan(self, goal: str, context: dict[str, Any] | None = None) -> SDKResult[Plan]:
        plan = Plan(id=f"plan_{uuid.uuid4().hex[:12]}", goal=goal, context=context or {})
        self._plans[plan.id] = plan
        logger.info(f"Plan created: {plan.id}")
        return SDKResult.ok(plan)

    async def add_task(
        self,
        plan_id: str,
        title: str,
        description: str = "",
        priority: PlanPriority = PlanPriority.MEDIUM,
        assigned_agent: str = "",
        dependencies: list[str] | None = None,
    ) -> SDKResult[PlanTask]:
        plan = self._plans.get(plan_id)
        if not plan:
            return SDKResult.fail(f"Plan {plan_id} not found")
        task = PlanTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            priority=priority,
            assigned_agent=assigned_agent,
            dependencies=dependencies or [],
        )
        plan.tasks.append(task)
        return SDKResult.ok(task)

    async def update_task_status(self, task_id: str, status: PlanStatus) -> SDKResult:
        for plan in self._plans.values():
            for task in plan.tasks:
                if task.id == task_id:
                    task.status = status
                    if status in (PlanStatus.COMPLETED, PlanStatus.FAILED):
                        task.completed_at = datetime.utcnow()
                    return SDKResult.ok()
        return SDKResult.fail(f"Task {task_id} not found")

    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    async def list_plans(self, status: Optional[PlanStatus] = None) -> list[Plan]:
        if status:
            return [p for p in self._plans.values() if p.status == status]
        return list(self._plans.values())

    async def get_next_tasks(self, plan_id: str) -> list[PlanTask]:
        plan = self._plans.get(plan_id)
        if not plan:
            return []
        ready = []
        for task in plan.tasks:
            if task.status != PlanStatus.DRAFT:
                continue
            deps_met = all(
                any(t.id == dep and t.status == PlanStatus.COMPLETED for t in plan.tasks)
                for dep in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return ready

    async def complete_plan(self, plan_id: str) -> SDKResult:
        plan = self._plans.get(plan_id)
        if not plan:
            return SDKResult.fail(f"Plan {plan_id} not found")
        plan.status = PlanStatus.COMPLETED
        plan.updated_at = datetime.utcnow()
        return SDKResult.ok()
