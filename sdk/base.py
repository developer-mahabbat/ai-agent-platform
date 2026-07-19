import abc
import logging
from typing import Any, Generic, Optional, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SDKInterface(abc.ABC):
    @abc.abstractmethod
    async def initialize(self) -> None: ...

    @abc.abstractmethod
    async def shutdown(self) -> None: ...


@dataclass
class SDKContext:
    session_id: str = ""
    user_id: str = ""
    project_id: str = ""
    workspace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class SDKResult(Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: T = None, metadata: dict[str, Any] = None) -> "SDKResult[T]":
        return cls(success=True, data=data, metadata=metadata or {})

    @classmethod
    def fail(cls, error: str, metadata: dict[str, Any] = None) -> "SDKResult[T]":
        return cls(success=False, error=error, metadata=metadata or {})


class SDKModule(abc.ABC):
    name: str = ""
    version: str = "1.0.0"
    dependencies: list[str] = []

    def __init__(self, context: Optional[SDKContext] = None):
        self.context = context or SDKContext()
        self._initialized = False

    async def init(self) -> None:
        if not self._initialized:
            await self.initialize()
            self._initialized = True
            logger.info(f"{self.name} SDK initialized")

    async def close(self) -> None:
        if self._initialized:
            await self.shutdown()
            self._initialized = False
            logger.info(f"{self.name} SDK shut down")

    @abc.abstractmethod
    async def initialize(self) -> None: ...

    @abc.abstractmethod
    async def shutdown(self) -> None: ...

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
