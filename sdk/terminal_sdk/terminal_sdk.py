import asyncio
import logging
import os
import shlex
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class TerminalSDK(SDKModule):
    name = "terminal"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._workdir: str = os.getcwd()
        self._env: dict[str, str] = os.environ.copy()
        self._timeout: int = 120
        self._blocked_commands: list[str] = []

    async def initialize(self) -> None:
        logger.info("TerminalSDK initialized")

    async def shutdown(self) -> None:
        logger.info("TerminalSDK shut down")

    def _is_blocked(self, command: str) -> bool:
        cmd = command.strip().split()[0].lower() if command.strip() else ""
        return cmd in self._blocked_commands

    async def execute(self, command: str, timeout: Optional[int] = None) -> SDKResult[dict[str, Any]]:
        if self._is_blocked(command):
            return SDKResult.fail(f"Command blocked: {command.split()[0]}")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._workdir,
                env=self._env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout or self._timeout
            )
            return SDKResult.ok({
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "exit_code": proc.returncode,
                "command": command,
            })
        except asyncio.TimeoutError:
            return SDKResult.fail(f"Command timed out after {timeout or self._timeout}s")
        except Exception as e:
            return SDKResult.fail(str(e))

    async def execute_python(self, code: str) -> SDKResult[dict[str, Any]]:
        return await self.execute(f'python3 -c {shlex.quote(code)}')

    def set_workdir(self, path: str) -> None:
        self._workdir = path

    async def get_workdir(self) -> str:
        return self._workdir

    async def get_env(self, key: str) -> Optional[str]:
        return self._env.get(key)

    def set_env(self, key: str, value: str) -> None:
        self._env[key] = value

    def block_command(self, cmd: str) -> None:
        self._blocked_commands.append(cmd.lower())
