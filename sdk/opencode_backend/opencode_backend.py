import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Optional

import httpx

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class BackendEventType(str, Enum):
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    REASON = "reason"
    SEARCH = "search"
    AGENT_THINK = "agent_think"
    OBSERVATION = "observation"
    ERROR = "error"
    COMPLETE = "complete"
    TOKEN = "token"


@dataclass
class BackendEvent:
    type: BackendEventType
    content: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {"type": self.type.value, "content": self.content, "data": self.data, "timestamp": self.timestamp}


class OpenCodeBackend(SDKModule):
    name = "opencode_backend"
    version = "2.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = "https://opencode.ai/zen/v1"
        self._model = "deepseek-v4-flash-free"
        self._max_tool_rounds = 10

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; MKCode/2.0)",
            },
        )
        logger.info("OpenCodeBackend initialized")

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
        logger.info("OpenCodeBackend shut down")

    def _tool_definitions(self) -> str:
        return """You have access to these tools. To call a tool, respond with:
<tool>
{
  "name": "tool_name",
  "arguments": { "arg1": "val1" }
}
</tool>

Available tools:
1. **search_web** - Search the web for information
   Arguments: {"query": "string", "max_results": "integer (optional, default 5)"}

2. **read_url** - Fetch and extract text from a URL
   Arguments: {"url": "string"}

3. **calculate** - Evaluate a math expression
   Arguments: {"expression": "string"}

4. **read_file** - Read a file from the filesystem
   Arguments: {"path": "string"}

5. **list_dir** - List directory contents
   Arguments: {"path": "string"}

6. **run_python** - Execute Python code
   Arguments: {"code": "string"}

7. **now** - Get current date/time
   Arguments: {}"""

    async def chat(
        self,
        message: str,
        system_prompt: str = "",
        history: list[dict[str, str]] | None = None,
        tools_enabled: bool = True,
        stream: bool = True,
    ) -> AsyncIterator[BackendEvent]:
        yield BackendEvent(BackendEventType.THINK, "Processing through OpenCode AI backend")

        sys_prompt = system_prompt or self._default_system_prompt()
        if tools_enabled:
            sys_prompt += "\n\n" + self._tool_definitions()

        messages = [{"role": "system", "content": sys_prompt}]
        for h in (history or [])[-20:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        all_content = ""
        tool_rounds = 0

        while tool_rounds < self._max_tool_rounds:
            response_text = ""
            async for chunk in self._stream_chat(messages):
                if chunk.get("type") == "token":
                    response_text += chunk["content"]
                    yield BackendEvent(BackendEventType.TOKEN, chunk["content"])
                elif chunk.get("type") == "error":
                    yield BackendEvent(BackendEventType.ERROR, chunk["content"])

            if not response_text:
                yield BackendEvent(BackendEventType.ERROR, "No response from AI")
                break

            all_content += response_text

            tool_call = self._parse_tool_call(response_text)
            if not tool_call:
                yield BackendEvent(BackendEventType.COMPLETE, response_text)
                if stream:
                    yield BackendEvent(BackendEventType.COMPLETE, response_text)
                break

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})
            logger.info(f"Tool call: {tool_name}({tool_args})")

            yield BackendEvent(BackendEventType.TOOL_CALL, f"Calling tool: {tool_name}",
                               data={"tool": tool_name, "arguments": tool_args})

            tool_result = await self._execute_tool(tool_name, tool_args)

            yield BackendEvent(BackendEventType.TOOL_RESULT, tool_result[:500],
                               data={"tool": tool_name, "result": tool_result[:1000]})

            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "tool", "content": tool_result, "tool_call_id": tool_name})
            messages.append({"role": "user", "content": "Continue with the tool result above and provide your response."})

            tool_rounds += 1

        if tool_rounds >= self._max_tool_rounds:
            yield BackendEvent(BackendEventType.ERROR, "Max tool call rounds reached")

    def _default_system_prompt(self) -> str:
        return """You are MKCode, an advanced AI assistant powered by the OpenCode AI backend.
You have access to web search, code execution, file reading, and more.
Be concise, accurate, and helpful. Use tools when you need current information
or to perform actions. Think step by step for complex problems."""

    async def _stream_chat(self, messages: list[dict]) -> AsyncIterator[dict]:
        if not self._client:
            yield {"type": "error", "content": "Client not initialized"}
            return
        try:
            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 8192,
                "stream": True,
            }
            async with self._client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str and data_str not in ("[DONE]", ""):
                            try:
                                d = json.loads(data_str)
                                for c in d.get("choices", []):
                                    token = c.get("delta", {}).get("content", "") or c.get("text", "")
                                    if token:
                                        yield {"type": "token", "content": token}
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield {"type": "error", "content": str(e)}

    async def chat_completion(self, messages: list[dict]) -> SDKResult[str]:
        if not self._client:
            return SDKResult.fail("Client not initialized")
        try:
            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 8192,
                "stream": False,
            }
            resp = await self._client.post(f"{self._base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = (data.get("choices", [{}])[0].get("message", {}).get("content", "") or
                       data.get("choices", [{}])[0].get("text", ""))
            return SDKResult.ok(content)
        except Exception as e:
            return SDKResult.fail(str(e))

    def _parse_tool_call(self, text: str) -> Optional[dict]:
        m = re.search(r"<tool>\s*(\{.*?\})\s*</tool>", text, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
            return {"name": data.get("name", ""), "arguments": data.get("arguments", {})}
        except json.JSONDecodeError:
            return None

    async def _execute_tool(self, name: str, args: dict) -> str:
        from app.core.container import Container
        c = Container()
        tool_sdk = c.tool_sdk
        if not tool_sdk._initialized:
            await tool_sdk.initialize()
        result = await tool_sdk.execute(name, args)
        if result.success:
            return result.output[:2000] if result.output else "(empty result)"
        return f"Error: {result.error}"

    async def search_and_answer(self, query: str) -> AsyncIterator[BackendEvent]:
        yield BackendEvent(BackendEventType.SEARCH, f"Researching: {query}")

        if self._client:
            try:
                url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                resp = await self._client.get(url, follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; MKCode/2.0)"})
                if resp.status_code == 200:
                    results = self._parse_search_results(resp.text, 5)
                    if results:
                        yield BackendEvent(BackendEventType.OBSERVATION,
                            f"Found {len(results)} search results")
                    else:
                        yield BackendEvent(BackendEventType.OBSERVATION,
                            "No search results parsed, using AI knowledge")
                else:
                    yield BackendEvent(BackendEventType.OBSERVATION,
                        f"Search returned status {resp.status_code}")
            except Exception as e:
                logger.warning(f"Search error: {e}")
                yield BackendEvent(BackendEventType.OBSERVATION, "Search unavailable, using AI knowledge")

        async for event in self.chat(query, tools_enabled=False):
            yield event

    def _parse_search_results(self, html: str, max_results: int) -> list[dict]:
        results = []
        for m in re.finditer(
            r'class="result__body".*?href="(.*?)".*?class="result__title".*?>(.*?)</a>.*?'
            r'class="result__snippet".*?>(.*?)</',
            html, re.DOTALL,
        ):
            url = m.group(1).replace("&amp;", "&")
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", m.group(3)).strip()
            results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= max_results:
                break
        if not results:
            for m in re.finditer(
                r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>.*?'
                r'<a class="result__snippet".*?>(.*?)</a>',
                html, re.DOTALL,
            ):
                url = m.group(1).replace("&amp;", "&")
                title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                snippet = re.sub(r"<[^>]+>", "", m.group(3)).strip()
                results.append({"title": title, "url": url, "snippet": snippet})
                if len(results) >= max_results:
                    break
        return results
