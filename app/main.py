import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import config
from app.core.container import Container

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mkcode")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {config.app_name} v{config.app_version} starting...")
    container = Container()
    container.db.connect()
    await container.init_all()
    logger.info(f"✅ {config.app_name} ready on {config.server_host}:{config.server_port}")
    yield
    await container.shutdown_all()
    container.db.close()
    logger.info(f"👋 {config.app_name} shut down")


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = Path(__file__).parent / "templates" / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>MKCode AI Agent Platform</h1><p>Frontend not found</p>")


@app.get("/chat/{chat_id}", response_class=HTMLResponse)
async def chat_page(chat_id: str):
    index_path = Path(__file__).parent / "templates" / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Chat</h1>")


def main():
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        workers=config.server_workers,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
