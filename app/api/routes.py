import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.db import get_db, Database
from app.models.schemas import (
    ChatCreate, ChatResponse, ChatHistoryResponse,
    MessageCreate, MessageResponse,
    AgentCreate, AgentResponse,
    TaskCreate, TaskResponse,
    PlanCreate, PlanResponse,
    SearchRequest, SearchResponse,
    ToolCallRequest, ToolCallResponse,
    GenerateRequest, GenerateResponse,
    ErrorResponse,
)
from workflows import ChatWorkflow
from app.core.container import Container

logger = logging.getLogger(__name__)

router = APIRouter()


def get_container() -> Container:
    return Container()


def get_workflow() -> ChatWorkflow:
    return ChatWorkflow()


@router.get("/health")
async def health_check(container: Container = Depends(get_container)):
    return {
        "status": "ok",
        "app": container.config.app_name,
        "version": container.config.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/status")
async def get_status(container: Container = Depends(get_container)):
    tools = await container.tool_sdk.list_tools()
    return {
        "app": container.config.app_name,
        "version": container.config.app_version,
        "providers": len(container.provider_sdk._providers) if hasattr(container.provider_sdk, '_providers') else 0,
        "agents": len(container.agent_sdk._agents) if hasattr(container.agent_sdk, '_agents') else 0,
        "tools": [t.spec.name for t in tools],
        "memory_sessions": list(container.memory_sdk._sessions.keys()) if hasattr(container.memory_sdk, '_sessions') else [],
        "graphs": list(container.orchestrator_sdk._graphs.keys()) if hasattr(container.orchestrator_sdk, '_graphs') else [],
        "uptime": datetime.utcnow().isoformat(),
    }


@router.post("/chat")
async def create_chat(
    chat: ChatCreate,
    db: Database = Depends(get_db),
):
    chat_id = f"chat_{uuid.uuid4().hex[:12]}"
    session_id = chat.session_id or f"session_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    existing = db.fetch_one("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not existing:
        db.execute(
            "INSERT INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
            (session_id, chat.title, now),
        )

    db.execute(
        """INSERT INTO chats (id, session_id, title, model, provider, system_prompt, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (chat_id, session_id, chat.title, chat.model, chat.provider, chat.system_prompt, now, now),
    )
    db.commit()

    return ChatResponse(
        id=chat_id,
        session_id=session_id,
        title=chat.title,
        model=chat.model,
        provider=chat.provider,
        created_at=now,
        updated_at=now,
    )


@router.post("/chat/{chat_id}/message")
async def send_message(
    chat_id: str,
    message: MessageCreate,
    db: Database = Depends(get_db),
    workflow: ChatWorkflow = Depends(get_workflow),
):
    chat = db.fetch_one("SELECT * FROM chats WHERE id = ?", (chat_id,))
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    db.execute(
        "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (msg_id, chat_id, message.role, message.content, now),
    )
    db.execute(
        "UPDATE chats SET updated_at = ? WHERE id = ?",
        (now, chat_id),
    )
    db.commit()

    if message.stream:
        return StreamingResponse(
            stream_response(workflow, message.content, chat_id, search=message.search, agents=message.agents),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    else:
        result = []
        async for event in workflow.process_message(message.content, chat_id, stream=False, search=message.search, agents=message.agents):
            result.append(event)
        content = result[-1]["data"]["content"] if result else ""

        assistant_id = f"msg_{uuid.uuid4().hex[:12]}"
        db.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (assistant_id, chat_id, "assistant", content, datetime.utcnow().isoformat()),
        )
        db.commit()

        return MessageResponse(
            id=assistant_id,
            chat_id=chat_id,
            role="assistant",
            content=content,
            created_at=datetime.utcnow().isoformat(),
        )


async def stream_response(workflow: ChatWorkflow, message: str, chat_id: str, search: bool = False, agents: bool = False):
    async for event in workflow.process_message(message, chat_id, stream=True, search=search, agents=agents):
        yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"


@router.get("/chat/{chat_id}")
async def get_chat_history(
    chat_id: str,
    db: Database = Depends(get_db),
):
    chat = db.fetch_one("SELECT * FROM chats WHERE id = ?", (chat_id,))
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.fetch(
        "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
        (chat_id,),
    )

    return ChatHistoryResponse(
        chat=ChatResponse(
            id=chat["id"],
            session_id=chat["session_id"],
            title=chat["title"],
            model=chat.get("model", ""),
            provider=chat.get("provider", ""),
            created_at=chat["created_at"],
            updated_at=chat["updated_at"],
        ),
        messages=[
            MessageResponse(
                id=m["id"],
                chat_id=m["chat_id"],
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"],
            )
            for m in messages
        ],
    )


@router.get("/chats")
async def list_chats(
    session_id: str = "",
    limit: int = 50,
    db: Database = Depends(get_db),
):
    if session_id:
        chats = db.fetch(
            "SELECT * FROM chats WHERE session_id = ? ORDER BY updated_at DESC LIMIT ?",
            (session_id, limit),
        )
    else:
        chats = db.fetch(
            "SELECT * FROM chats ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )

    return [
        ChatResponse(
            id=c["id"],
            session_id=c["session_id"],
            title=c["title"],
            model=c.get("model", ""),
            provider=c.get("provider", ""),
            created_at=c["created_at"],
            updated_at=c["updated_at"],
        )
        for c in chats
    ]


@router.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str, db: Database = Depends(get_db)):
    db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    db.commit()
    return {"status": "deleted", "chat_id": chat_id}


@router.post("/agents")
async def create_agent(
    agent_data: AgentCreate,
    container: Container = Depends(get_container),
):
    from sdk.agent_sdk import AgentConfig, AgentRole

    role_map = {
        "supervisor": AgentRole.SUPERVISOR,
        "planner": AgentRole.PLANNER,
        "coder": AgentRole.CODER,
        "researcher": AgentRole.RESEARCHER,
        "reasoner": AgentRole.REASONER,
        "reviewer": AgentRole.REVIEWER,
        "debugger": AgentRole.DEBUGGER,
        "browser": AgentRole.BROWSER,
        "memory": AgentRole.MEMORY,
        "search": AgentRole.SEARCH,
        "task": AgentRole.TASK,
        "reflection": AgentRole.REFLECTION,
        "execution": AgentRole.EXECUTION,
        "router": AgentRole.ROUTER,
        "security": AgentRole.SECURITY,
        "quality": AgentRole.QUALITY,
        "assistant": AgentRole.ASSISTANT,
    }

    role = role_map.get(agent_data.role.lower(), AgentRole.ASSISTANT)
    config = AgentConfig(
        role=role,
        model=agent_data.model or container.config.default_model,
        system_prompt=agent_data.instructions,
    )

    result = await container.agent_sdk.create_agent(
        name=agent_data.name,
        role=role,
        config=config,
    )

    if not result.success or not result.data:
        raise HTTPException(status_code=400, detail=result.error)

    agent = result.data
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        role=agent.role.value,
        model=agent.config.model,
    )


@router.get("/agents")
async def list_agents(container: Container = Depends(get_container)):
    agents = await container.agent_sdk.list_agents()
    return [
        AgentResponse(
            id=a.id,
            name=a.name,
            role=a.role.value,
            model=a.config.model,
            state=a.state.value,
        )
        for a in agents
    ]


@router.post("/search")
async def search(
    request: SearchRequest,
    container: Container = Depends(get_container),
):
    provider = getattr(request, "provider", "auto")
    max_results = getattr(request, "max_results", 10)
    result = await container.search_sdk.search(request.query, provider=provider, max_results=max_results)
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error)
    return SearchResponse(
        query=request.query,
        results=result.data or [],
        sources=list(set(r.get("url", "") for r in (result.data or []))),
    )


@router.post("/research")
async def research(
    request: SearchRequest,
    container: Container = Depends(get_container),
):
    query = request.query
    result = await container.search_sdk.search(query, max_results=8)

    if not result.success or not result.data:
        raise HTTPException(status_code=502, detail="Search failed")

    sources_text = "\n\n".join(
        f"Source {i+1}: {r['title']}\n{r['snippet'][:500]}\nURL: {r['url']}"
        for i, r in enumerate(result.data[:8])
    )

    provider_sdk = container.provider_sdk
    cfg = container.config
    prompt = f"""Synthesize the following search results into a comprehensive research report.

Query: {query}

Sources:
{sources_text}

Provide: key findings, notable insights, source citations."""
    messages = [
        {"role": "system", "content": "You are a Research Agent. Synthesize information clearly."},
        {"role": "user", "content": prompt},
    ]

    try:
        resp = await provider_sdk.chat_completion(cfg.default_provider, cfg.default_model, messages)
        if resp.success and resp.data:
            content = (resp.data.get("choices", [{}])[0]
                       .get("message", {}).get("content", ""))
            return {"query": query, "report": content, "sources": sources_text}
    except Exception as e:
        logger.warning(f"Research synthesis failed: {e}")

    return {"query": query, "report": "Research synthesis unavailable.", "sources": sources_text}


@router.post("/orchestrate")
async def orchestrate(
    request: SearchRequest,
    container: Container = Depends(get_container),
):
    orchestrator = container.orchestrator_sdk
    gid = await orchestrator.build_default_agent_graph(request.query)
    graph = container.orchestrator_sdk._graphs.get(gid)

    events = []
    async for event in orchestrator.run(gid, {"goal": request.query}):
        events.append(event.to_dict())

    summary = ""
    if graph:
        for key in ["planner_response", "researcher_response", "coder_response", "reasoner_response"]:
            val = graph.context.get(key, "")
            if val:
                summary += val + "\n\n"

    return {
        "query": request.query,
        "events": events,
        "summary": summary or "(no agent output)",
    }


@router.post("/generate")
async def generate(
    request: GenerateRequest,
    container: Container = Depends(get_container),
):
    provider_sdk = container.provider_sdk
    cfg = container.config

    content = []
    content.append({"type": "text", "text": request.prompt})
    if request.image:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{request.image}"}})
    elif request.image_url:
        content.append({"type": "image_url", "image_url": {"url": request.image_url}})

    messages = [{"role": "user", "content": content}]
    if request.system_prompt:
        messages.insert(0, {"role": "system", "content": request.system_prompt})

    try:
        result = await provider_sdk.chat_completion(
            "opencode", request.model, messages,
            temperature=request.temperature, max_tokens=request.max_tokens,
        )
        if result.success and result.data:
            text = (result.data.get("choices", [{}])[0]
                    .get("message", {}).get("content", ""))
            return GenerateResponse(success=True, content=text, model=request.model, provider="opencode")
        return GenerateResponse(success=False, error=result.error or "Empty response", model=request.model)
    except Exception as e:
        return GenerateResponse(success=False, error=str(e), model=request.model)


@router.post("/opencode/chat")
async def opencode_chat(
    request: SearchRequest,
    container: Container = Depends(get_container),
):
    backend = container.opencode_backend
    if not backend._initialized:
        await backend.initialize()

    events = []
    async for event in backend.search_and_answer(request.query):
        events.append(event.to_dict())

    return {"query": request.query, "events": events}


@router.post("/opencode/tool")
async def opencode_tool_call(
    request: ToolCallRequest,
    container: Container = Depends(get_container),
):
    backend = container.opencode_backend
    if not backend._initialized:
        await backend.initialize()

    events = []
    async for event in backend.chat(
        f"Execute: {request.tool} with {json.dumps(request.params)}",
        tools_enabled=False,
        stream=False,
    ):
        events.append(event.to_dict())

    return {"events": events}


@router.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str,
    request: ToolCallRequest,
    container: Container = Depends(get_container),
):
    result = await container.tool_sdk.execute(tool_name, request.params)
    return ToolCallResponse(
        success=result.success,
        output=result.output,
        error=result.error,
        duration_ms=result.duration_ms,
    )


@router.get("/tools")
async def list_tools(container: Container = Depends(get_container)):
    tools = await container.tool_sdk.list_tools()
    return [
        {
            "name": t.spec.name,
            "description": t.spec.description,
            "category": t.spec.category.value,
            "enabled": t.enabled,
        }
        for t in tools
    ]


@router.get("/providers")
async def list_providers(container: Container = Depends(get_container)):
    providers = await container.provider_sdk.list_providers()
    return [
        {
            "name": p.name,
            "models": [{"id": m.id, "name": m.name} for m in p.config.models],
            "available": p.is_available,
        }
        for p in providers
    ]


@router.get("/memory/{session_id}")
async def get_memory(
    session_id: str,
    container: Container = Depends(get_container),
):
    entries = await container.memory_sdk.retrieve(session_id)
    return {"session_id": session_id, "entries": [{"id": e.id, "type": e.type.value, "content": e.content[:200], "summary": e.summary} for e in entries]}


@router.post("/memory/{session_id}")
async def store_memory(
    session_id: str,
    entry: MessageCreate,
    container: Container = Depends(get_container),
):
    from sdk.memory_sdk.models import MemoryType
    result = await container.memory_sdk.store(session_id, entry.content, MemoryType.CONVERSATION)
    if result.success:
        return {"status": "stored", "id": result.data.id if result.data else None}
    return {"status": "error", "error": result.error}


@router.get("/models")
async def list_models(container: Container = Depends(get_container)):
    models = []
    for p in await container.provider_sdk.list_providers():
        for m in p.config.models:
            models.append({"provider": p.name, "id": m.id, "name": m.name})
    return models


@router.get("/projects")
async def list_projects(db: Database = Depends(get_db)):
    projects = db.fetch("SELECT * FROM projects ORDER BY updated_at DESC")
    return projects


@router.post("/projects")
async def create_project(
    name: str,
    description: str = "",
    path: str = "",
    db: Database = Depends(get_db),
):
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO projects (id, name, description, path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, name, description, path, now, now),
    )
    db.commit()
    return {"id": project_id, "name": name, "created_at": now}


@router.get("/metrics")
async def get_metrics(container: Container = Depends(get_container)):
    metrics = await container.telemetry_sdk.get_metrics()
    return metrics


@router.post("/reset")
async def reset_session(
    session_id: str,
    container: Container = Depends(get_container),
):
    await container.memory_sdk.clear(session_id)
    return {"status": "reset", "session_id": session_id}
