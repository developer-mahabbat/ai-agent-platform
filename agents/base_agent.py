import abc
import logging
from typing import Any, AsyncIterator, Optional

from sdk.base import SDKContext, SDKResult
from sdk.agent_sdk import Agent, AgentConfig, AgentRole, AgentState

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    name: str = ""
    role: AgentRole = AgentRole.ASSISTANT
    description: str = ""

    def __init__(self, context: Optional[SDKContext] = None):
        self.context = context or SDKContext()
        self._agent: Optional[Agent] = None

    @abc.abstractmethod
    async def run(self, task: str, **kwargs: Any) -> AsyncIterator[str]:
        ...

    @abc.abstractmethod
    async def get_system_prompt(self) -> str:
        ...

    async def initialize(self, agent_sdk=None) -> Agent:
        config = AgentConfig(
            role=self.role,
            system_prompt=await self.get_system_prompt(),
        )
        if agent_sdk:
            result = await agent_sdk.create_agent(
                name=self.name,
                role=self.role,
                config=config,
            )
            if result.success and result.data:
                self._agent = result.data
        return self._agent

    async def get_agent(self) -> Optional[Agent]:
        return self._agent
