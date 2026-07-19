import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Optional

from ..base import SDKModule, SDKResult
from .models import Agent, AgentConfig, AgentRole, AgentState

logger = logging.getLogger(__name__)


class AgentSDK(SDKModule):
    name = "agent"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._agents: dict[str, Agent] = {}
        self._hooks: dict[str, list[Callable]] = {}

    async def initialize(self) -> None:
        logger.info("AgentSDK initializing")

    async def shutdown(self) -> None:
        self._agents.clear()
        logger.info("AgentSDK shut down")

    def register_hook(self, event: str, hook: Callable) -> None:
        self._hooks.setdefault(event, []).append(hook)

    async def emit(self, event: str, **data: Any) -> None:
        for hook in self._hooks.get(event, []):
            try:
                await hook(data) if asyncio.iscoroutinefunction(hook) else hook(data)
            except Exception as e:
                logger.error(f"Hook error for {event}: {e}")

    async def create_agent(
        self,
        name: str,
        role: AgentRole,
        config: Optional[AgentConfig] = None,
        **kwargs: Any,
    ) -> SDKResult[Agent]:
        try:
            agent_id = f"agent_{uuid.uuid4().hex[:12]}"
            agent = Agent(
                id=agent_id,
                name=name,
                role=role,
                config=config or AgentConfig(role=role),
                **kwargs,
            )
            self._agents[agent_id] = agent
            await self.emit("agent.created", agent=agent)
            logger.info(f"Agent created: {name} ({role.value})")
            return SDKResult.ok(agent)
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            return SDKResult.fail(str(e))

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    async def update_state(self, agent_id: str, state: AgentState) -> SDKResult:
        agent = self._agents.get(agent_id)
        if not agent:
            return SDKResult.fail(f"Agent {agent_id} not found")
        agent.state = state
        agent.updated_at = datetime.utcnow()
        await self.emit("agent.state_changed", agent_id=agent_id, state=state)
        return SDKResult.ok()

    async def list_agents(self, role: Optional[AgentRole] = None) -> list[Agent]:
        if role:
            return [a for a in self._agents.values() if a.role == role]
        return list(self._agents.values())

    async def delete_agent(self, agent_id: str) -> SDKResult:
        if agent_id in self._agents:
            del self._agents[agent_id]
            await self.emit("agent.deleted", agent_id=agent_id)
            return SDKResult.ok()
        return SDKResult.fail(f"Agent {agent_id} not found")

    async def send_message(self, agent_id: str, message: str) -> SDKResult[str]:
        agent = self._agents.get(agent_id)
        if not agent:
            return SDKResult.fail(f"Agent {agent_id} not found")
        await self.emit("agent.message", agent_id=agent_id, message=message)
        return SDKResult.ok(f"[{agent.name}]: Processing...")

    async def run_with_stream(
        self, agent_id: str, task: str
    ) -> AsyncIterator[str]:
        agent = self._agents.get(agent_id)
        if not agent:
            yield f"Error: Agent {agent_id} not found"
            return
        await self.update_state(agent_id, AgentState.THINKING)
        yield f"🧠 {agent.name} thinking...\n"
        await asyncio.sleep(0.5)
        await self.update_state(agent_id, AgentState.EXECUTING)
        yield f"⚡ {agent.name} executing task: {task}\n"
        await asyncio.sleep(0.3)
        yield f"✅ {agent.name} completed\n"
        await self.update_state(agent_id, AgentState.COMPLETED)
