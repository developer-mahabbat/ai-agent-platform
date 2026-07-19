# MKCode - AI Agent Platform

A production-grade autonomous AI agent platform with multi-agent collaboration, deep reasoning, web research, coding assistance, and tool execution.

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Open http://localhost:8000

## Architecture

```
mkcode/
├── sdk/              # Internal SDK modules
│   ├── agent_sdk/    # Agent management
│   ├── memory_sdk/   # Memory & context
│   ├── tool_sdk/     # Tool execution
│   ├── provider_sdk/ # AI model providers
│   ├── reasoning_sdk/# Reasoning pipelines
│   ├── planning_sdk/ # Task planning
│   ├── workflow_sdk/ # Workflow orchestration
│   ├── browser_sdk/  # Web browsing
│   ├── filesystem_sdk/# File operations
│   ├── terminal_sdk/ # Command execution
│   ├── workspace_sdk/ # Workspace management
│   ├── document_sdk/ # Document handling
│   ├── knowledge_sdk/ # Knowledge base
│   ├── retrieval_sdk/ # Information retrieval
│   ├── stream_sdk/   # Streaming
│   ├── events_sdk/   # Event system
│   ├── storage_sdk/  # Database storage
│   ├── security_sdk/ # Security
│   ├── plugin_sdk/   # Plugin system
│   ├── mcp_sdk/      # MCP protocol
│   └── telemetry_sdk/ # Telemetry
├── app/              # FastAPI application
│   ├── api/          # REST API routes
│   ├── core/         # DI container
│   ├── db/           # Database layer
│   ├── models/       # Pydantic schemas
│   ├── static/       # Frontend assets
│   └── templates/    # HTML templates
├── agents/           # Agent implementations
├── workflows/        # LangGraph workflows
├── tools/            # Tool implementations
├── plugins/          # Plugin directory
└── config/           # Configuration
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/chat` | POST | Create chat |
| `/api/chat/{id}/message` | POST | Send message (SSE) |
| `/api/chat/{id}` | GET | Get chat history |
| `/api/chats` | GET | List chats |
| `/api/agents` | GET | List agents |
| `/api/providers` | GET | List providers |
| `/api/tools` | GET | List tools |
| `/api/search` | POST | Search knowledge |
| `/api/metrics` | GET | Get metrics |

## Docker

```bash
docker-compose up
```

## Deployment (Render)

1. Push to GitHub
2. Connect repo to Render
3. Use `render.yaml` or set:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
