import logging
from typing import Any, Optional

from app.config import config
from app.db import Database, db as global_db
from sdk.registry import SDKRegistry, registry as global_registry
from sdk.agent_sdk import AgentSDK
from sdk.memory_sdk import MemorySDK
from sdk.tool_sdk import ToolSDK
from sdk.provider_sdk import ProviderSDK
from sdk.reasoning_sdk import ReasoningSDK
from sdk.planning_sdk import PlanningSDK
from sdk.workflow_sdk import WorkflowSDK
from sdk.browser_sdk import BrowserSDK
from sdk.filesystem_sdk import FileSystemSDK
from sdk.terminal_sdk import TerminalSDK
from sdk.workspace_sdk import WorkspaceSDK
from sdk.document_sdk import DocumentSDK
from sdk.knowledge_sdk import KnowledgeSDK
from sdk.retrieval_sdk import RetrievalSDK
from sdk.stream_sdk import StreamSDK
from sdk.events_sdk import EventSDK
from sdk.storage_sdk import StorageSDK
from sdk.security_sdk import SecuritySDK
from sdk.plugin_sdk import PluginSDK
from sdk.mcp_sdk import MCPSDK
from sdk.telemetry_sdk import TelemetrySDK
from sdk.search_sdk import SearchSDK
from sdk.orchestrator_sdk import OrchestratorSDK
from sdk.opencode_backend import OpenCodeBackend

logger = logging.getLogger(__name__)


class Container:
    _instance: Optional["Container"] = None

    def __new__(cls) -> "Container":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.config = config
        self.registry: SDKRegistry = global_registry
        self.db: Database = global_db

        self.agent_sdk = AgentSDK()
        self.memory_sdk = MemorySDK()
        self.tool_sdk = ToolSDK()
        self.provider_sdk = ProviderSDK()
        self.reasoning_sdk = ReasoningSDK()
        self.planning_sdk = PlanningSDK()
        self.workflow_sdk = WorkflowSDK()
        self.browser_sdk = BrowserSDK()
        self.filesystem_sdk = FileSystemSDK()
        self.terminal_sdk = TerminalSDK()
        self.workspace_sdk = WorkspaceSDK()
        self.document_sdk = DocumentSDK()
        self.knowledge_sdk = KnowledgeSDK()
        self.retrieval_sdk = RetrievalSDK()
        self.stream_sdk = StreamSDK()
        self.events_sdk = EventSDK()
        self.storage_sdk = StorageSDK()
        self.security_sdk = SecuritySDK()
        self.plugin_sdk = PluginSDK()
        self.mcp_sdk = MCPSDK()
        self.telemetry_sdk = TelemetrySDK()
        self.search_sdk = SearchSDK()
        self.orchestrator_sdk = OrchestratorSDK()
        self.opencode_backend = OpenCodeBackend()

        self._register_all()
        self._initialized = True

    def _register_all(self) -> None:
        modules = [
            ("agent", self.agent_sdk),
            ("memory", self.memory_sdk),
            ("tool", self.tool_sdk),
            ("provider", self.provider_sdk),
            ("reasoning", self.reasoning_sdk),
            ("planning", self.planning_sdk),
            ("workflow", self.workflow_sdk),
            ("browser", self.browser_sdk),
            ("filesystem", self.filesystem_sdk),
            ("terminal", self.terminal_sdk),
            ("workspace", self.workspace_sdk),
            ("document", self.document_sdk),
            ("knowledge", self.knowledge_sdk),
            ("retrieval", self.retrieval_sdk),
            ("stream", self.stream_sdk),
            ("events", self.events_sdk),
            ("storage", self.storage_sdk),
            ("security", self.security_sdk),
            ("plugin", self.plugin_sdk),
            ("mcp", self.mcp_sdk),
            ("telemetry", self.telemetry_sdk),
            ("search", self.search_sdk),
            ("orchestrator", self.orchestrator_sdk),
            ("opencode_backend", self.opencode_backend),
        ]
        for name, module in modules:
            self.registry.register(name, module)

    async def init_all(self) -> None:
        logger.info("Initializing all SDK modules...")
        await self.registry.init_all()
        logger.info("All SDK modules initialized")

    async def shutdown_all(self) -> None:
        logger.info("Shutting down all SDK modules...")
        await self.registry.shutdown_all()
        logger.info("All SDK modules shut down")


container = Container()
