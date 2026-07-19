import asyncio
import logging
from typing import Any, AsyncIterator

from sdk.agent_sdk import AgentRole, AgentState
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    name = "planner"
    role = AgentRole.PLANNER
    description = "Creates detailed execution plans from high-level goals"

    async def get_system_prompt(self) -> str:
        return """You are the Planner Agent. Your role is to:
1. Create detailed step-by-step plans from high-level goals
2. Identify dependencies between tasks
3. Estimate effort and complexity
4. Define clear success criteria
5. Identify potential risks and mitigation strategies
6. Break down complex problems into manageable chunks

Always output clear, structured, actionable plans."""

    async def run(self, task: str, **kwargs: Any) -> AsyncIterator[str]:
        await self.update_state(AgentState.THINKING)
        yield f"📐 **Planner** creating plan...\n\n"

        await asyncio.sleep(0.3)
        yield f"**Goal:** {task}\n\n"
        yield f"**Plan:**\n\n"
        yield f"1. **Phase 1:** Requirements analysis\n"
        await asyncio.sleep(0.2)
        yield f"   - Define scope and constraints\n"
        yield f"   - Identify key deliverables\n\n"
        yield f"2. **Phase 2:** Architecture design\n"
        await asyncio.sleep(0.2)
        yield f"   - Design component structure\n"
        yield f"   - Define interfaces and data flow\n\n"
        yield f"3. **Phase 3:** Implementation\n"
        await asyncio.sleep(0.2)
        yield f"   - Build core components\n"
        yield f"   - Integrate and test\n\n"
        yield f"4. **Phase 4:** Review and finalize\n"
        await asyncio.sleep(0.2)
        yield f"   - Code review\n"
        yield f"   - Documentation\n"
        yield f"   - Deployment\n\n"

        yield f"✅ Plan created with 4 phases and {kwargs.get('estimated_tasks', 8)} estimated tasks.\n"
        await self.update_state(AgentState.COMPLETED)

    async def update_state(self, state: AgentState) -> None:
        if self._agent:
            self._agent.state = state
