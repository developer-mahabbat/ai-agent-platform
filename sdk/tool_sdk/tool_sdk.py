import asyncio
import logging
import time
from typing import Any, AsyncIterator, Callable, Optional

from ..base import SDKModule, SDKResult
from .models import Tool, ToolCategory, ToolResult, ToolSpec

logger = logging.getLogger(__name__)


class ToolSDK(SDKModule):
    name = "tool"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._tools: dict[str, Tool] = {}

    async def initialize(self) -> None:
        await self._register_defaults()
        logger.info("ToolSDK initialized")

    async def shutdown(self) -> None:
        self._tools.clear()
        logger.info("ToolSDK shut down")

    async def _register_defaults(self) -> None:
        await self.register(
            ToolSpec(name="echo", description="Echo input back", category=ToolCategory.UTILITY, parameters={"text": {"type": "string"}}, required_params=["text"]),
            self._echo,
        )
        await self.register(
            ToolSpec(name="now", description="Get current date and time", category=ToolCategory.UTILITY),
            self._now,
        )
        await self.register(
            ToolSpec(name="calculate", description="Evaluate a mathematical expression", category=ToolCategory.UTILITY, parameters={"expression": {"type": "string"}}, required_params=["expression"]),
            self._calculate,
        )
        await self.register(
            ToolSpec(name="list_tools", description="List all available tools", category=ToolCategory.UTILITY, parameters={"category": {"type": "string"}}),
            self._list_tools,
        )
        await self.register(
            ToolSpec(name="read_file", description="Read a file from the filesystem", category=ToolCategory.FILESYSTEM, parameters={"path": {"type": "string"}}, required_params=["path"]),
            self._read_file,
        )
        await self.register(
            ToolSpec(name="write_file", description="Write content to a file", category=ToolCategory.FILESYSTEM, parameters={"path": {"type": "string"}, "content": {"type": "string"}}, required_params=["path", "content"]),
            self._write_file,
        )
        await self.register(
            ToolSpec(name="list_dir", description="List directory contents", category=ToolCategory.FILESYSTEM, parameters={"path": {"type": "string"}}, required_params=["path"]),
            self._list_dir,
        )
        await self.register(
            ToolSpec(name="run_command", description="Run a shell command", category=ToolCategory.TERMINAL, parameters={"command": {"type": "string"}, "timeout": {"type": "integer"}}, required_params=["command"], dangerous=True, timeout=60),
            self._run_command,
        )
        await self.register(
            ToolSpec(name="run_python", description="Execute Python code", category=ToolCategory.PYTHON, parameters={"code": {"type": "string"}, "timeout": {"type": "integer"}}, required_params=["code"], dangerous=True, timeout=30),
            self._run_python,
        )
        await self.register(
            ToolSpec(name="git_status", description="Show git status", category=ToolCategory.GIT, parameters={"path": {"type": "string"}}),
            self._git_status,
        )
        await self.register(
            ToolSpec(name="git_commit", description="Create a git commit", category=ToolCategory.GIT, parameters={"path": {"type": "string"}, "message": {"type": "string"}}, required_params=["message"]),
            self._git_commit,
        )
        await self.register(
            ToolSpec(name="http_get", description="Make an HTTP GET request", category=ToolCategory.HTTP, parameters={"url": {"type": "string"}, "timeout": {"type": "integer"}}, required_params=["url"]),
            self._http_get,
        )
        await self.register(
            ToolSpec(name="search_web", description="Search the web", category=ToolCategory.SEARCH, parameters={"query": {"type": "string"}, "max_results": {"type": "integer"}}, required_params=["query"]),
            self._search_web,
        )
        await self.register(
            ToolSpec(name="read_url", description="Fetch and extract text from a URL", category=ToolCategory.HTTP, parameters={"url": {"type": "string"}}, required_params=["url"]),
            self._read_url,
        )

    async def _echo(self, text: str = "") -> ToolResult:
        return ToolResult(output=text)

    async def _now(self) -> ToolResult:
        import datetime
        return ToolResult(output=datetime.datetime.now().isoformat())

    async def _calculate(self, expression: str = "") -> ToolResult:
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return ToolResult(output=str(result))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _list_tools(self, category: Optional[str] = None) -> ToolResult:
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.spec.category.value == category]
        names = "\n".join(f"  {t.spec.name}: {t.spec.description}" for t in tools)
        return ToolResult(output=f"Available tools:\n{names}")

    async def _read_file(self, path: str = "") -> ToolResult:
        try:
            with open(path, "r") as f:
                content = f.read()
            return ToolResult(output=content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _write_file(self, path: str = "", content: str = "") -> ToolResult:
        try:
            with open(path, "w") as f:
                f.write(content)
            return ToolResult(output=f"Written {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _list_dir(self, path: str = "") -> ToolResult:
        import os
        try:
            entries = os.listdir(path)
            return ToolResult(output="\n".join(entries))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _run_command(self, command: str = "", timeout: int = 30) -> ToolResult:
        import subprocess
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            output = result.stdout or result.stderr or "(no output)"
            return ToolResult(output=output)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _run_python(self, code: str = "", timeout: int = 10) -> ToolResult:
        import subprocess
        try:
            result = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=timeout)
            output = result.stdout or result.stderr or "(no output)"
            return ToolResult(output=output)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Python timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _git_status(self, path: str = ".") -> ToolResult:
        import subprocess
        try:
            result = subprocess.run(["git", "-C", path, "status", "--short"], capture_output=True, text=True)
            return ToolResult(output=result.stdout or "(clean)" if not result.stderr else result.stderr)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _git_commit(self, path: str = ".", message: str = "") -> ToolResult:
        import subprocess
        try:
            subprocess.run(["git", "-C", path, "add", "-A"], capture_output=True, text=True)
            result = subprocess.run(["git", "-C", path, "commit", "-m", message], capture_output=True, text=True)
            output = result.stdout or result.stderr
            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _http_get(self, url: str = "", timeout: int = 15) -> ToolResult:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                import re
                text = resp.text[:10000]
                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return ToolResult(output=text)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _search_web(self, query: str = "", max_results: int = 5) -> ToolResult:
        try:
            from ..search_sdk import SearchSDK
            search = SearchSDK()
            await search.initialize()
            result = await search.search(query, max_results=max_results)
            await search.shutdown()
            if result.success and result.data:
                lines = []
                for r in result.data:
                    lines.append(f"• {r['title']}\n  {r['snippet'][:200]}\n  {r['url']}")
                return ToolResult(output="\n\n".join(lines))
            return ToolResult(success=False, error="No search results")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _read_url(self, url: str = "") -> ToolResult:
        return await self._http_get(url=url)

    async def register(
        self, spec: ToolSpec, handler: Callable[..., Any]
    ) -> SDKResult:
        tool = Tool(spec=spec, handler=handler)
        self._tools[spec.name] = tool
        logger.info(f"Registered tool: {spec.name}")
        return SDKResult.ok()

    async def execute(
        self, name: str, params: dict[str, Any] | None = None, timeout: int | None = None
    ) -> ToolResult:
        start = time.monotonic()
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")
        if not tool.enabled:
            return ToolResult(success=False, error=f"Tool '{name}' is disabled")
        try:
            result = await asyncio.wait_for(
                tool.handler(**(params or {})),
                timeout=timeout or tool.spec.timeout,
            )
            result.duration_ms = (time.monotonic() - start) * 1000
            return result
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Tool '{name}' timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e), duration_ms=(time.monotonic() - start) * 1000)

    async def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    async def list_tools(self, category: Optional[ToolCategory] = None) -> list[Tool]:
        if category:
            return [t for t in self._tools.values() if t.spec.category == category]
        return list(self._tools.values())
