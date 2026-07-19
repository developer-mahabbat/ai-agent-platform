import logging
from typing import Any, Optional

from sdk.agent_sdk import AgentRole
from .base_agent import BaseAgent
from .supervisor_agent import SupervisorAgent
from .planner_agent import PlannerAgent
from .coder_agent import CoderAgent
from .researcher_agent import ResearcherAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    _agents: dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: type[BaseAgent]) -> None:
        cls._agents[name] = agent_class
        logger.debug(f"Registered agent class: {name}")

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> Optional[BaseAgent]:
        agent_class = cls._agents.get(name)
        if not agent_class:
            logger.error(f"Unknown agent: {name}")
            return None
        return agent_class(**kwargs)

    @classmethod
    def create_by_role(cls, role: AgentRole, **kwargs: Any) -> Optional[BaseAgent]:
        for name, agent_class in cls._agents.items():
            if hasattr(agent_class, "role") and agent_class.role == role:
                return agent_class(**kwargs)
        return None

    @classmethod
    def list_agents(cls) -> list[str]:
        return list(cls._agents.keys())


AgentFactory.register("supervisor", SupervisorAgent)
AgentFactory.register("planner", PlannerAgent)
AgentFactory.register("coder", CoderAgent)
AgentFactory.register("researcher", ResearcherAgent)
