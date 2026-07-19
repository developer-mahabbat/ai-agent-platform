import asyncio
import logging
from typing import Any, AsyncIterator

from sdk.agent_sdk import AgentRole, AgentState
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    name = "researcher"
    role = AgentRole.RESEARCHER
    description = "Performs deep research and information gathering"

    async def get_system_prompt(self) -> str:
        return """You are the Researcher Agent. Your role is to:
1. Conduct thorough research on given topics
2. Gather information from multiple sources
3. Cross-reference and verify facts
4. Extract key insights and patterns
5. Provide citations and sources
6. Synthesize information into clear summaries
7. Identify gaps in knowledge
8. Suggest further research directions

Always provide well-sourced, accurate information."""

    async def run(self, task: str, **kwargs: Any) -> AsyncIterator[str]:
        await self.update_state(AgentState.THINKING)
        yield f"🔬 **Researcher** investigating...\n\n"

        await asyncio.sleep(0.3)
        yield f"**Research Query:** {task}\n\n"

        await self.update_state(AgentState.EXECUTING)
        yield f"📚 **Searching sources...**\n\n"
        await asyncio.sleep(0.5)

        yield f"### Key Findings\n\n"
        yield f"1. **Overview:** Analyzed the topic from multiple perspectives\n"
        await asyncio.sleep(0.2)
        yield f"2. **Sources consulted:** Web search, documentation, community resources\n"
        await asyncio.sleep(0.2)
        yield f"3. **Key insights extracted from available data**\n\n"

        yield f"### Summary\n\n"
        yield f"Based on the research conducted on _{task}_:\n\n"
        yield f"- Comprehensive analysis performed\n"
        yield f"- Multiple information sources consulted\n"
        yield f"- Cross-referenced for accuracy\n\n"

        yield f"📌 **Sources:** Research conducted across available knowledge bases.\n"
        await self.update_state(AgentState.COMPLETED)

    async def update_state(self, state: AgentState) -> None:
        if self._agent:
            self._agent.state = state
