import asyncio
import logging
from typing import Any, AsyncIterator

from sdk.agent_sdk import AgentRole, AgentState
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    name = "supervisor"
    role = AgentRole.SUPERVISOR
    description = "Coordinates and delegates tasks to specialized agents"

    async def get_system_prompt(self) -> str:
        return """You are the Supervisor Agent. Your role is to:
1. Analyze incoming user requests
2. Decompose complex tasks into sub-tasks
3. Assign sub-tasks to the appropriate specialized agents
4. Monitor execution progress
5. Synthesize results from multiple agents
6. Ensure quality and consistency
7. Handle errors and retry when necessary

Coordinate the workflow efficiently and provide clear, structured responses."""

    async def run(self, task: str, **kwargs: Any) -> AsyncIterator[str]:
        await self.update_state(AgentState.THINKING)
        yield f"🤖 **Supervisor** analyzing request...\n\n"

        await asyncio.sleep(0.3)
        yield f"📋 **Plan:** Breaking down task\n\n"

        await self.update_state(AgentState.PLANNING)
        yield f"1. Understanding requirements\n"
        await asyncio.sleep(0.2)
        yield f"2. Identifying sub-tasks\n"
        await asyncio.sleep(0.2)
        yield f"3. Assigning to specialized agents\n\n"

        await self.update_state(AgentState.EXECUTING)
        yield f"⚡ **Executing:** Coordinating agents for: _{task}_\n\n"

        await asyncio.sleep(0.3)
        yield f"✅ **Complete:** Supervisor has coordinated the workflow.\n"

        await self.update_state(AgentState.COMPLETED)

    async def update_state(self, state: AgentState) -> None:
        if self._agent:
            self._agent.state = state
