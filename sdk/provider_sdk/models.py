from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_reasoning: bool = False
    supports_vision: bool = False
    supports_tools: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class ProviderConfig:
    name: str
    base_url: str = ""
    api_key: str = ""
    api_type: str = "openai"
    models: list[ModelInfo] = field(default_factory=list)
    default_model: str = ""
    fallback_models: list[str] = field(default_factory=list)
    extra_headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 120
    max_retries: int = 3
    priority: int = 0


@dataclass
class Provider:
    name: str
    config: ProviderConfig
    is_available: bool = True
    models_count: int = 0
