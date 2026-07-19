import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

from app.core.container import Container

logger = logging.getLogger(__name__)


class ChatWorkflow:
    def __init__(self, container: Optional[Container] = None):
        self.container = container or Container()

    async def process_message(
        self,
        message: str,
        chat_id: str = "",
        stream: bool = True,
        history: list[dict[str, str]] | None = None,
        search: bool = False,
        agents: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        history = history or []

        if agents:
            async for event in self._orchestrated_response(message, chat_id, history):
                yield event
            return

        if search:
            async for event in self._search_enhanced_response(message, chat_id, history):
                yield event
            return

        backend = self.container.opencode_backend

        try:
            if not backend._initialized:
                await backend.initialize()

            str_history = [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history[-10:]]

            async for event in backend.chat(message, history=str_history, stream=stream):
                if event.type.value == "token":
                    yield {"event": "token", "data": {"token": event.content, "chat_id": chat_id}}
                elif event.type.value == "think":
                    yield {"event": "reasoning", "data": {"type": "think", "message": event.content}}
                elif event.type.value == "tool_call":
                    yield {"event": "reasoning", "data": {"type": "tool", "message": event.content}}
                elif event.type.value == "tool_result":
                    yield {"event": "reasoning", "data": {"type": "tool_result", "message": event.content[:200]}}
                elif event.type.value == "search":
                    yield {"event": "reasoning", "data": {"type": "search", "message": event.content}}
                elif event.type.value == "complete":
                    yield {"event": "complete", "data": {"chat_id": chat_id}}
                elif event.type.value == "error":
                    yield {"event": "reasoning", "data": {"type": "error", "message": event.content}}

        except Exception as e:
            logger.error(f"OpenCode backend failed: {e}", exc_info=True)
            yield {"event": "reasoning", "data": {"type": "fallback", "message": "Backend failed, using direct mode"}}
            if stream:
                async for event in self._stream_response(message, chat_id, history):
                    yield event
            else:
                result = await self._generate_response(message, chat_id, history)
                yield {"event": "complete", "data": {"content": result}}

    async def _search_enhanced_response(
        self, message: str, chat_id: str, history: list[dict[str, str]]
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"event": "searching", "data": {"message": "Searching the web..."}}

        search_sdk = None
        results_data = []
        try:
            from sdk.search_sdk import SearchSDK
            search_sdk = SearchSDK()
            await search_sdk.initialize()
            raw_results = await search_sdk.search(message, max_results=10)
            if raw_results and raw_results.success and raw_results.data:
                results_data = raw_results.data
            await search_sdk.shutdown()
        except Exception as e:
            logger.warning(f"Search failed: {e}")

        context = ""
        if results_data:
            for i, r in enumerate(results_data[:10]):
                context += f"\n[{i+1}] {r.get('title', '')}\n   {r.get('snippet', '')[:300]}\n   Source: {r.get('url', '')}\n"

            yield {
                "event": "sources",
                "data": {
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("snippet", ""),
                            "domain": r.get("source", ""),
                        }
                        for r in results_data[:10]
                    ]
                },
            }
        else:
            yield {"event": "reasoning", "data": {"type": "search", "message": "Web search unavailable, using AI knowledge"}}

        cfg = self.container.config
        provider_sdk = self.container.provider_sdk

        sys_prompt = """You are MKCode, an AI agent with real-time web search capability.
Answer the user's question using the search results below. Cite sources with [1], [2], etc.
Be concise, accurate, and helpful."""

        if results_data:
            sys_prompt += "\n\nSearch results:\n" + context

        messages = [{"role": "system", "content": sys_prompt}]
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        try:
            full = ""
            async for chunk in provider_sdk.stream_chat(cfg.default_provider, cfg.default_model, messages):
                if chunk.startswith("data: "):
                    data_str = chunk[6:].strip()
                    if data_str and data_str not in ("[DONE]", ""):
                        try:
                            d = json.loads(data_str)
                            for c in d.get("choices", []):
                                token = c.get("delta", {}).get("content", "") or c.get("text", "")
                                if token:
                                    full += token
                                    yield {"event": "token", "data": {"token": token, "chat_id": chat_id}}
                        except json.JSONDecodeError:
                            pass
            if full:
                yield {"event": "complete", "data": {"chat_id": chat_id}}
                return
        except Exception as e:
            logger.error(f"Search-enhanced stream failed: {e}")

        yield {"event": "token", "data": {"token": f"(search unavailable) Answering from knowledge: {message}", "chat_id": chat_id}}
        yield {"event": "complete", "data": {"chat_id": chat_id}}

    async def _orchestrated_response(
        self, message: str, chat_id: str, history: list[dict[str, str]]
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"event": "reasoning", "data": {"type": "orchestrate", "message": "Orchestrating multi-agent workflow..."}}

        orchestrator = self.container.registry.get("orchestrator")

        if not orchestrator:
            yield {"event": "reasoning", "data": {"type": "orchestrate", "message": "Orchestrator unavailable, using direct response"}}
            async for event in self._stream_response(message, chat_id, history):
                yield event
            return

        try:
            gid = await orchestrator.build_default_agent_graph(message)
            graph = orchestrator._graphs.get(gid)
            if graph:
                graph.context["history"] = history[-5:]

            async for event in orchestrator.run(gid, {"goal": message, "chat_id": chat_id, "history": history[-5:]}):
                if event.type == "node_start":
                    yield {"event": "reasoning", "data": {"type": "agent", "message": f"🤖 {event.content}", "node_id": event.node_id}}
                elif event.type == "node_complete" and event.content:
                    yield {"event": "reasoning", "data": {"type": "result", "message": f"✅ {event.content[:200]}", "node_id": event.node_id}}
                elif event.type == "node_fail":
                    yield {"event": "reasoning", "data": {"type": "error", "message": f"⚠️ {event.content}", "node_id": event.node_id}}
                elif event.type == "graph_complete":
                    yield {"event": "reasoning", "data": {"type": "complete", "message": "Multi-agent workflow complete"}}

            summary = ""
            if graph:
                for key in ["planner_response", "researcher_response", "coder_response", "reasoner_response"]:
                    val = graph.context.get(key, "")
                    if val:
                        summary += val + "\n\n"

            if summary:
                for word in summary.split():
                    yield {"event": "token", "data": {"token": word + " ", "chat_id": chat_id}}
            else:
                async for event in self._stream_response(message, chat_id, history):
                    yield event
                return

            yield {"event": "complete", "data": {"chat_id": chat_id}}

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            async for event in self._stream_response(message, chat_id, history):
                yield event

    def _build_messages(self, message: str, history: list[dict[str, str]]) -> list[dict]:
        msgs = [{"role": "system", "content": "You are MKCode, an AI agent platform. Be concise, helpful, and direct."}]
        for h in history[-20:]:
            msgs.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        msgs.append({"role": "user", "content": message})
        return msgs

    async def _stream_response(
        self, message: str, chat_id: str, history: list[dict[str, str]]
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"event": "thinking", "data": {"message": ""}}

        cfg = self.container.config
        provider_sdk = self.container.provider_sdk
        messages = self._build_messages(message, history)

        try:
            full = ""
            async for chunk in provider_sdk.stream_chat(cfg.default_provider, cfg.default_model, messages):
                if chunk.startswith("data: "):
                    data_str = chunk[6:].strip()
                    if data_str and data_str not in ("[DONE]", ""):
                        try:
                            d = json.loads(data_str)
                            for c in d.get("choices", []):
                                token = c.get("delta", {}).get("content", "") or c.get("text", "")
                                if token:
                                    full += token
                                    yield {"event": "token", "data": {"token": token, "chat_id": chat_id}}
                        except json.JSONDecodeError:
                            pass
            if full:
                yield {"event": "complete", "data": {"chat_id": chat_id}}
                return
            raise ValueError("empty response")
        except Exception as e:
            logger.error(f"Stream failed: {e}", exc_info=True)

        yield {"event": "token", "data": {"token": f"(offline) You said: {message}", "chat_id": chat_id}}
        yield {"event": "complete", "data": {"chat_id": chat_id}}

    async def _generate_response(
        self, message: str, chat_id: str, history: list[dict[str, str]]
    ) -> str:
        cfg = self.container.config
        provider_sdk = self.container.provider_sdk
        messages = self._build_messages(message, history)

        try:
            result = await provider_sdk.chat_completion(cfg.default_provider, cfg.default_model, messages, stream=False)
            if result.success and result.data:
                choice = result.data.get("choices", [{}])[0]
                return choice.get("message", {}).get("content", "") or choice.get("text", "")
        except Exception as e:
            logger.warning(f"Completion failed: {e}")

        return f"(offline) You said: {message}"
