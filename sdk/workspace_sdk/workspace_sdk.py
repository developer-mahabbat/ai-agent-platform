import logging
import os
from pathlib import Path
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class WorkspaceSDK(SDKModule):
    name = "workspace"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._root: Path = Path.cwd()
        self._workspaces: dict[str, Path] = {}
        self._active: Optional[str] = None

    async def initialize(self) -> None:
        self._workspaces["default"] = self._root
        self._active = "default"
        logger.info(f"WorkspaceSDK initialized (root: {self._root})")

    async def shutdown(self) -> None:
        self._workspaces.clear()
        logger.info("WorkspaceSDK shut down")

    async def create(self, name: str, path: Optional[str] = None) -> SDKResult:
        base = Path(path).resolve() if path else self._root / name
        base.mkdir(parents=True, exist_ok=True)
        self._workspaces[name] = base
        logger.info(f"Workspace created: {name} at {base}")
        return SDKResult.ok()

    async def switch(self, name: str) -> SDKResult:
        if name not in self._workspaces:
            return SDKResult.fail(f"Workspace '{name}' not found")
        self._active = name
        return SDKResult.ok()

    async def get_active(self) -> str:
        return self._active or "default"

    async def get_path(self, name: Optional[str] = None) -> Path:
        return self._workspaces.get(name or self._active or "default", self._root)

    async def list_workspaces(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "path": str(path), "active": name == self._active}
            for name, path in self._workspaces.items()
        ]

    async def delete(self, name: str) -> SDKResult:
        if name == "default":
            return SDKResult.fail("Cannot delete default workspace")
        if name not in self._workspaces:
            return SDKResult.fail(f"Workspace '{name}' not found")
        del self._workspaces[name]
        if self._active == name:
            self._active = "default"
        return SDKResult.ok()
