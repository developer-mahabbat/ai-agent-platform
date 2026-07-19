from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class ToolCategory(str, Enum):
    FILESYSTEM = "filesystem"
    TERMINAL = "terminal"
    PYTHON = "python"
    GIT = "git"
    GITHUB = "github"
    HTTP = "http"
    SEARCH = "search"
    BROWSER = "browser"
    MEMORY = "memory"
    VISION = "vision"
    DATABASE = "database"
    DOCKER = "docker"
    UTILITY = "utility"
    MCP = "mcp"
    CUSTOM = "custom"


@dataclass
class ToolSpec:
    name: str
    description: str
    category: ToolCategory
    parameters: dict[str, Any] = field(default_factory=dict)
    required_params: list[str] = field(default_factory=list)
    returns: str = "str"
    timeout: int = 30
    permission_required: bool = False
    dangerous: bool = False


@dataclass
class ToolResult:
    success: bool = True
    output: str = ""
    error: str = ""
    data: Any = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Tool:
    spec: ToolSpec
    handler: Callable[..., Awaitable[ToolResult]]
    enabled: bool = True
