import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Optional

from ..base import SDKModule, SDKResult
from .models import Plugin, PluginHook, PluginManifest

logger = logging.getLogger(__name__)


class PluginSDK(SDKModule):
    name = "plugin"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._plugins: dict[str, Plugin] = {}
        self._plugin_dirs: list[Path] = []

    async def initialize(self) -> None:
        self._plugin_dirs = [
            Path("plugins"),
            Path(".opencode/plugins"),
        ]
        await self._discover_plugins()
        logger.info("PluginSDK initialized")

    async def shutdown(self) -> None:
        self._plugins.clear()
        logger.info("PluginSDK shut down")

    async def _discover_plugins(self) -> None:
        for plugin_dir in self._plugin_dirs:
            if plugin_dir.is_dir():
                for py_file in plugin_dir.glob("*.py"):
                    try:
                        await self.load_from_file(str(py_file))
                    except Exception as e:
                        logger.error(f"Failed to load plugin {py_file}: {e}")

    async def register(self, manifest: PluginManifest, hooks: list[PluginHook] | None = None) -> SDKResult:
        if manifest.name in self._plugins:
            return SDKResult.fail(f"Plugin '{manifest.name}' already registered")
        plugin = Plugin(manifest=manifest, hooks=hooks or [])
        self._plugins[manifest.name] = plugin
        logger.info(f"Plugin registered: {manifest.name} v{manifest.version}")
        return SDKResult.ok()

    async def load_from_file(self, filepath: str) -> SDKResult:
        path = Path(filepath).resolve()
        if not path.exists():
            return SDKResult.fail(f"Plugin file not found: {filepath}")
        module_name = f"plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            return SDKResult.fail(f"Failed to load module from {filepath}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        if hasattr(module, "manifest"):
            manifest = module.manifest
        else:
            manifest = PluginManifest(name=path.stem, description="Loaded from file")
        hooks = []
        if hasattr(module, "hooks"):
            hooks = module.hooks
        return await self.register(manifest, hooks)

    async def unregister(self, name: str) -> SDKResult:
        if name in self._plugins:
            del self._plugins[name]
            logger.info(f"Plugin unregistered: {name}")
            return SDKResult.ok()
        return SDKResult.fail(f"Plugin '{name}' not found")

    async def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    async def list_plugins(self, enabled_only: bool = False) -> list[Plugin]:
        plugins = list(self._plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if p.enabled]
        return plugins

    async def enable(self, name: str) -> SDKResult:
        plugin = self._plugins.get(name)
        if not plugin:
            return SDKResult.fail(f"Plugin '{name}' not found")
        plugin.enabled = True
        return SDKResult.ok()

    async def disable(self, name: str) -> SDKResult:
        plugin = self._plugins.get(name)
        if not plugin:
            return SDKResult.fail(f"Plugin '{name}' not found")
        plugin.enabled = False
        return SDKResult.ok()

    async def execute_hooks(self, event: str, context: dict[str, Any] | None = None) -> None:
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            for hook in plugin.hooks:
                if hook.event == event:
                    try:
                        await hook.handler(context or {})
                    except Exception as e:
                        logger.error(f"Plugin hook error ({plugin.manifest.name}/{hook.event}): {e}")
