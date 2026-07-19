import logging
from typing import Any, Optional, Type
from .base import SDKModule, SDKContext

logger = logging.getLogger(__name__)


class SDKRegistry:
    _instance: Optional["SDKRegistry"] = None

    def __new__(cls) -> "SDKRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._modules = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, name: str, module: SDKModule) -> None:
        self._modules[name] = module
        logger.debug(f"Registered SDK module: {name}")

    def get(self, name: str) -> Optional[SDKModule]:
        return self._modules.get(name)

    def get_all(self) -> dict[str, SDKModule]:
        return dict(self._modules)

    async def init_all(self, context: Optional[SDKContext] = None) -> None:
        for name, module in self._modules.items():
            if context:
                module.context = context
            await module.init()
        self._initialized = True
        logger.info(f"All SDK modules initialized ({len(self._modules)} modules)")

    async def shutdown_all(self) -> None:
        for name, module in self._modules.items():
            await module.close()
        self._initialized = False
        logger.info("All SDK modules shut down")

    @property
    def initialized(self) -> bool:
        return self._initialized


registry = SDKRegistry()
