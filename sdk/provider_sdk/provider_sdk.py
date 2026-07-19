import logging
from typing import Any, AsyncIterator, Optional

import httpx

from ..base import SDKModule, SDKResult
from .models import ModelInfo, Provider, ProviderConfig

logger = logging.getLogger(__name__)


class ProviderSDK(SDKModule):
    name = "provider"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._providers: dict[str, Provider] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120))
        await self._register_defaults()
        logger.info("ProviderSDK initialized")

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
        self._providers.clear()
        logger.info("ProviderSDK shut down")

    async def _register_defaults(self) -> None:
        defaults = [
            ProviderConfig(
                name="opencode",
                base_url="https://opencode.ai/zen/v1",
                models=[
                    ModelInfo(id="deepseek-v4-flash-free", name="DeepSeek V4 Flash Free", provider="opencode", max_tokens=16384, supports_reasoning=True, supports_streaming=True),
                    ModelInfo(id="hy3-free", name="Hy3 Free", provider="opencode", max_tokens=8192),
                    ModelInfo(id="big-pickle", name="Big Pickle", provider="opencode", max_tokens=8192),
                    ModelInfo(id="mimo-v2.5-free", name="MiMo V2.5 Free", provider="opencode", max_tokens=8192),
                    ModelInfo(id="north-mini-code-free", name="North Mini Code Free", provider="opencode", max_tokens=8192),
                    ModelInfo(id="nemotron-3-ultra-free", name="Nemotron 3 Ultra Free", provider="opencode", max_tokens=8192),
                ],
                default_model="deepseek-v4-flash-free",
            ),
            ProviderConfig(
                name="openai",
                base_url="https://api.openai.com/v1",
                models=[
                    ModelInfo(id="gpt-4o", name="GPT-4o", provider="openai", max_tokens=16384),
                    ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", provider="openai", max_tokens=16384),
                    ModelInfo(id="o3-mini", name="o3 Mini", provider="openai", max_tokens=16384, supports_reasoning=True),
                ],
                default_model="gpt-4o",
            ),
            ProviderConfig(
                name="anthropic",
                base_url="https://api.anthropic.com/v1",
                models=[
                    ModelInfo(id="claude-sonnet-4-6", name="Claude Sonnet", provider="anthropic", max_tokens=8192),
                    ModelInfo(id="claude-haiku-3-5", name="Claude Haiku", provider="anthropic", max_tokens=8192),
                ],
                default_model="claude-sonnet-4-6",
            ),
            ProviderConfig(
                name="deepseek",
                base_url="https://api.deepseek.com/v1",
                models=[
                    ModelInfo(id="deepseek-chat", name="DeepSeek Chat", provider="deepseek", max_tokens=8192, supports_reasoning=True),
                ],
                default_model="deepseek-chat",
            ),
            ProviderConfig(
                name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                models=[
                    ModelInfo(id="openrouter/auto", name="OpenRouter Auto", provider="openrouter", max_tokens=16384),
                ],
                default_model="openrouter/auto",
            ),
        ]
        for cfg in defaults:
            await self.register_provider(cfg)

    async def register_provider(self, config: ProviderConfig) -> SDKResult[Provider]:
        config.extra_headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; MKCode/1.0)")
        try:
            provider = Provider(name=config.name, config=config, models_count=len(config.models))
            self._providers[config.name] = provider
            logger.info(f"Registered provider: {config.name}")
            return SDKResult.ok(provider)
        except Exception as e:
            return SDKResult.fail(str(e))

    async def get_provider(self, name: str) -> Optional[Provider]:
        return self._providers.get(name)

    async def list_providers(self) -> list[Provider]:
        return list(self._providers.values())

    async def chat_completion(
        self,
        provider_name: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs: Any,
    ) -> SDKResult[dict[str, Any]]:
        provider = self._providers.get(provider_name)
        if not provider:
            return SDKResult.fail(f"Provider '{provider_name}' not found")
        if not self._client:
            return SDKResult.fail("HTTP client not initialized")
        try:
            url = f"{provider.config.base_url}/chat/completions"
            headers = dict(provider.config.extra_headers)
            headers["Content-Type"] = "application/json"
            if provider.config.api_key:
                headers["Authorization"] = f"Bearer {provider.config.api_key}"
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
                **kwargs,
            }
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return SDKResult.ok(response.json())
        except httpx.HTTPStatusError as e:
            return SDKResult.fail(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
        except Exception as e:
            return SDKResult.fail(str(e))

    async def stream_chat(
        self, provider_name: str, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> AsyncIterator[str]:
        provider = self._providers.get(provider_name)
        if not provider or not self._client:
            yield f"data: {{{{error: 'Provider not available'}}}}\n\n"
            return
        try:
            url = f"{provider.config.base_url}/chat/completions"
            headers = dict(provider.config.extra_headers)
            headers["Content-Type"] = "application/json"
            if provider.config.api_key:
                headers["Authorization"] = f"Bearer {provider.config.api_key}"
            payload = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 4096),
                "stream": True,
                **{k: v for k, v in kwargs.items() if k not in ("temperature", "max_tokens")},
            }
            async with self._client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line + "\n\n"
        except Exception as e:
            yield f"data: {{{{error: '{str(e)}'}}}}\n\n"
