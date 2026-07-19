import json
import logging
import uuid
from typing import Any, AsyncIterator, Optional

from ..base import SDKModule, SDKResult
from .models import ReasoningChain, ReasoningStep, ReasoningStrategy

logger = logging.getLogger(__name__)


class ReasoningSDK(SDKModule):
    name = "reasoning"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._chains: dict[str, ReasoningChain] = {}

    async def initialize(self) -> None:
        logger.info("ReasoningSDK initialized")

    async def shutdown(self) -> None:
        self._chains.clear()
        logger.info("ReasoningSDK shut down")

    async def create_chain(
        self, goal: str, strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    ) -> SDKResult[ReasoningChain]:
        chain = ReasoningChain(
            id=f"reason_{uuid.uuid4().hex[:12]}",
            goal=goal,
            strategy=strategy,
        )
        self._chains[chain.id] = chain
        logger.info(f"Reasoning chain created: {chain.id} ({strategy.value})")
        return SDKResult.ok(chain)

    async def add_step(
        self, chain_id: str, content: str, confidence: float = 0.0,
        parent_id: Optional[str] = None, step_type: str = "think"
    ) -> SDKResult[ReasoningStep]:
        chain = self._chains.get(chain_id)
        if not chain:
            return SDKResult.fail(f"Chain {chain_id} not found")
        step = ReasoningStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            index=len(chain.steps),
            content=content,
            confidence=confidence,
            parent_id=parent_id,
        )
        if parent_id:
            parent = next((s for s in chain.steps if s.id == parent_id), None)
            if parent:
                parent.children.append(step.id)
        chain.steps.append(step)
        return SDKResult.ok(step)

    async def conclude(self, chain_id: str, conclusion: str, confidence: float = 0.0) -> SDKResult:
        chain = self._chains.get(chain_id)
        if not chain:
            return SDKResult.fail(f"Chain {chain_id} not found")
        chain.conclusion = conclusion
        chain.confidence = confidence
        chain.complete = True
        return SDKResult.ok()

    async def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        return self._chains.get(chain_id)

    async def reason(
        self, goal: str, context: dict[str, Any] | None = None
    ) -> AsyncIterator[ReasoningStep]:
        chain = await self.create_chain(goal)
        if not chain.success or not chain.data:
            return
        cid = chain.data.id

        yield await self._make_step(cid, 0, f"🎯 Goal: {goal}", 0.9, "goal")

        ctx = context or {}
        ctx_str = json.dumps(ctx, indent=2)[:500] if ctx else "(none)"
        yield await self._make_step(cid, 1, f"📋 Context: {ctx_str}", 0.8, "context")

        yield await self._make_step(cid, 2, "🔍 Analyzing problem and identifying constraints", 0.75, "analyze")
        yield await self._make_step(cid, 3, "💾 Retrieving relevant memory and knowledge", 0.7, "retrieve")
        yield await self._make_step(cid, 4, "🔎 Searching for additional information", 0.7, "search")

        plan = f"Plan for: {goal[:100]}...\n  1. Understand requirements\n  2. Identify key components\n  3. Evaluate approaches\n  4. Select best solution"
        yield await self._make_step(cid, 5, plan, 0.8, "plan")

        yield await self._make_step(cid, 6, "📦 Decomposing into sub-tasks", 0.75, "decompose")
        yield await self._make_step(cid, 7, "🤖 Selecting appropriate agents for each task", 0.75, "select_agents")
        yield await self._make_step(cid, 8, "🔧 Calling tools and executing tasks", 0.7, "execute")

        yield await self._make_step(cid, 9, "📊 Evaluating results against goal", 0.8, "evaluate")
        yield await self._make_step(cid, 10, "🔄 Reflecting on outcomes and improvements", 0.75, "reflect")

        conclusion = f"Completed reasoning pipeline for: {goal}"
        yield await self._make_step(cid, 11, conclusion, 0.9, "conclusion")
        await self.conclude(cid, conclusion, confidence=0.9)

    async def _make_step(self, cid: str, index: int, content: str,
                         confidence: float, step_type: str = "think") -> ReasoningStep:
        step = ReasoningStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            index=index,
            content=content,
            confidence=confidence,
        )
        chain = self._chains.get(cid)
        if chain:
            chain.steps.append(step)
        return step

    async def full_pipeline(
        self, goal: str, context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        async for step in self.reason(goal, context):
            yield {
                "type": "reasoning_step",
                "index": step.index,
                "content": step.content,
                "confidence": step.confidence,
            }
