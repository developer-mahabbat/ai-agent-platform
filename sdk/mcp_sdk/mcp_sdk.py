import asyncio
import json
import logging
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class MCPSDK(SDKModule):
    name = "mcp"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._servers: dict[str, dict[str, Any]] = {}
        self._tools: dict[str, dict[str, Any]] = {}

    async def initialize(self) -> None:
        logger.info("MCPSDK initialized")

    async def shutdown(self) -> None:
        self._servers.clear()
        self._tools.clear()
        logger.info("MCPSDK shut down")

    async def register_server(self, name: str, config: dict[str, Any]) -> SDKResult:
        self._servers[name] = config
        logger.info(f"MCP server registered: {name}")
        return SDKResult.ok()

    async def register_tool(self, server: str, name: str, spec: dict[str, Any]) -> SDKResult:
        key = f"{server}:{name}"
        self._tools[key] = {"server": server, "name": name, "spec": spec}
        logger.info(f"MCP tool registered: {key}")
        return SDKResult.ok()

    async def call_tool(self, server: str, tool: str, params: dict[str, Any] | None = None) -> SDKResult:
        server_config = self._servers.get(server)
        if not server_config:
            return SDKResult.fail(f"MCP server '{server}' not found")
        if server_config.get("type") == "local":
            return await self._call_local(server_config, tool, params or {})
        elif server_config.get("type") == "remote":
            return await self._call_remote(server_config, tool, params or {})
        return SDKResult.fail(f"Unknown MCP server type: {server_config.get('type')}")

    async def _call_local(self, config: dict[str, Any], tool: str, params: dict[str, Any]) -> SDKResult:
        import subprocess
        command = config.get("command", [])
        if not command:
            return SDKResult.fail("No command configured for MCP server")
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            request = json.dumps({"tool": tool, "params": params})
            stdout, stderr = await proc.communicate(request.encode(), timeout=30)
            if proc.returncode != 0:
                return SDKResult.fail(stderr.decode()[:500])
            return SDKResult.ok(json.loads(stdout.decode()))
        except asyncio.TimeoutError:
            return SDKResult.fail("MCP tool timed out")
        except Exception as e:
            return SDKResult.fail(str(e))

    async def _call_remote(self, config: dict[str, Any], tool: str, params: dict[str, Any]) -> SDKResult:
        import httpx
        try:
            url = config.get("url", "")
            headers = config.get("headers", {})
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{url}/call/{tool}",
                    json=params,
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
                return SDKResult.ok(response.json())
        except Exception as e:
            return SDKResult.fail(str(e))

    async def list_tools(self, server: Optional[str] = None) -> list[dict[str, Any]]:
        if server:
            return [t for t in self._tools.values() if t["server"] == server]
        return list(self._tools.values())

    async def list_servers(self) -> list[dict[str, Any]]:
        return [{"name": k, **v} for k, v in self._servers.items()]
