import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from ..base import SDKModule, SDKResult
from .models import Workflow, WorkflowNode, WorkflowStatus, WorkflowStep

logger = logging.getLogger(__name__)


class WorkflowSDK(SDKModule):
    name = "workflow"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._workflows: dict[str, Workflow] = {}

    async def initialize(self) -> None:
        logger.info("WorkflowSDK initialized")

    async def shutdown(self) -> None:
        self._workflows.clear()
        logger.info("WorkflowSDK shut down")

    async def create_workflow(self, name: str, nodes: list[WorkflowNode] | None = None) -> SDKResult[Workflow]:
        workflow = Workflow(id=f"wf_{uuid.uuid4().hex[:12]}", name=name, nodes=nodes or [])
        self._workflows[workflow.id] = workflow
        logger.info(f"Workflow created: {workflow.id}")
        return SDKResult.ok(workflow)

    async def add_node(self, workflow_id: str, node: WorkflowNode) -> SDKResult:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return SDKResult.fail(f"Workflow {workflow_id} not found")
        workflow.nodes.append(node)
        return SDKResult.ok()

    async def execute(
        self, workflow_id: str, initial_input: dict[str, Any] | None = None
    ) -> AsyncIterator[WorkflowStep]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return

        workflow.status = WorkflowStatus.RUNNING
        workflow.updated_at = datetime.utcnow()

        for node in workflow.nodes:
            step = WorkflowStep(
                id=f"step_{uuid.uuid4().hex[:8]}",
                node_id=node.id,
                status=WorkflowStatus.RUNNING,
                input=initial_input or {},
                started_at=datetime.utcnow(),
            )
            workflow.steps.append(step)

            try:
                await asyncio.sleep(0.2)
                step.status = WorkflowStatus.COMPLETED
                step.output = f"Completed: {node.name}"
                step.completed_at = datetime.utcnow()
            except Exception as e:
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                workflow.status = WorkflowStatus.FAILED

            yield step

            if step.status == WorkflowStatus.FAILED:
                break

        if workflow.status != WorkflowStatus.FAILED:
            workflow.status = WorkflowStatus.COMPLETED
        workflow.updated_at = datetime.utcnow()

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    async def pause(self, workflow_id: str) -> SDKResult:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return SDKResult.fail(f"Workflow {workflow_id} not found")
        wf.status = WorkflowStatus.PAUSED
        return SDKResult.ok()

    async def resume(self, workflow_id: str) -> SDKResult:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return SDKResult.fail(f"Workflow {workflow_id} not found")
        wf.status = WorkflowStatus.RUNNING
        return SDKResult.ok()

    async def cancel(self, workflow_id: str) -> SDKResult:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return SDKResult.fail(f"Workflow {workflow_id} not found")
        wf.status = WorkflowStatus.CANCELLED
        return SDKResult.ok()
