from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ReasoningStrategy(str, Enum):
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    REACT = "react"
    PLAN_EXECUTE = "plan_execute"
    REFLECTION = "reflection"
    DECOMPOSE = "decompose"
    VERIFY = "verify"


@dataclass
class ReasoningStep:
    id: str
    index: int
    content: str
    confidence: float = 0.0
    parent_id: Optional[str] = None
    children: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningChain:
    id: str
    goal: str
    strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    steps: list[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    complete: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
