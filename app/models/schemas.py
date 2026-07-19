from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    session_id: str = ""
    title: str = "New Chat"
    model: str = ""
    provider: str = ""
    system_prompt: str = ""


class ChatResponse(BaseModel):
    id: str
    session_id: str
    title: str
    model: str
    provider: str
    message_count: int = 0
    last_message: str = ""
    created_at: str = ""
    updated_at: str = ""


class MessageCreate(BaseModel):
    chat_id: str
    role: str = "user"
    content: str
    stream: bool = True
    search: bool = False
    agents: bool = False


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    tool_calls: list[dict] = []
    tokens_input: int = 0
    tokens_output: int = 0
    created_at: str = ""


class ChatHistoryResponse(BaseModel):
    chat: ChatResponse
    messages: list[MessageResponse] = []


class AgentCreate(BaseModel):
    name: str
    role: str = "assistant"
    model: str = ""
    instructions: str = ""
    temperature: float = 0.7


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    model: str
    state: str = "idle"


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    agent_id: str = ""
    priority: str = "medium"
    dependencies: list[str] = []


class TaskResponse(BaseModel):
    id: str
    title: str
    status: str
    agent_id: str = ""
    result: str = ""
    error: str = ""
    created_at: str = ""


class PlanCreate(BaseModel):
    goal: str
    tasks: list[TaskCreate] = []


class PlanResponse(BaseModel):
    id: str
    goal: str
    status: str
    tasks: list[TaskResponse] = []
    created_at: str = ""


class ProviderConfig(BaseModel):
    name: str
    base_url: str = ""
    api_key: str = ""
    default_model: str = ""
    models: list[str] = []


class MemoryEntry(BaseModel):
    id: str = ""
    type: str = "conversation"
    content: str
    tags: list[str] = []


class SearchRequest(BaseModel):
    query: str
    provider: str = "duckduckgo"
    max_results: int = 10


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]] = []
    sources: list[str] = []


class ToolCallRequest(BaseModel):
    tool: str
    params: dict[str, Any] = {}


class ToolCallResponse(BaseModel):
    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0


class StreamEvent(BaseModel):
    event: str
    data: Any = None
    timestamp: str = ""


class GenerateRequest(BaseModel):
    prompt: str
    image: Optional[str] = ""
    image_url: Optional[str] = ""
    model: str = "deepseek-v4-flash-free"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False


class GenerateResponse(BaseModel):
    success: bool
    content: str = ""
    error: str = ""
    model: str = ""
    provider: str = "opencode"


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    code: int = 400
