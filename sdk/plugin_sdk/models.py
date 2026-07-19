from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class PluginManifest:
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    dependencies: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)


@dataclass
class PluginHook:
    event: str
    handler: Callable
    priority: int = 0


@dataclass
class Plugin:
    manifest: PluginManifest
    hooks: list[PluginHook] = field(default_factory=list)
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)
