import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class AppConfig:
    app_name: str = "MKCode"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_workers: int = 1
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    database_url: str = "sqlite:///mkcode.db"
    database_echo: bool = False

    secret_key: str = "change-me-to-a-random-secret"
    api_key: str = ""

    default_provider: str = "opencode"
    default_model: str = "deepseek-v4-flash-free"
    fallback_model: str = "deepseek-v4-flash-free"

    max_tokens: int = 4096
    temperature: float = 0.7
    streaming: bool = True

    rate_limit_per_minute: int = 60
    max_file_size_mb: int = 10
    max_chat_history: int = 200

    plugin_dirs: list[str] = field(default_factory=lambda: ["plugins", ".opencode/plugins"])
    workspace_root: str = "."
    data_dir: str = "data"

    telemetry_enabled: bool = False
    memory_enabled: bool = True
    workspace_enabled: bool = True

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        cfg = cls()

        if path and Path(path).exists():
            data = json.loads(Path(path).read_text())
            for key, value in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)

        env_map = {
            "MKCODE_DEBUG": ("debug", lambda v: v.lower() == "true"),
            "MKCODE_LOG_LEVEL": ("log_level", str),
            "MKCODE_HOST": ("server_host", str),
            "MKCODE_PORT": ("server_port", int),
            "MKCODE_DATABASE_URL": ("database_url", str),
            "MKCODE_SECRET_KEY": ("secret_key", str),
            "MKCODE_API_KEY": ("api_key", str),
            "MKCODE_DEFAULT_PROVIDER": ("default_provider", str),
            "MKCODE_DEFAULT_MODEL": ("default_model", str),
            "MKCODE_TEMPERATURE": ("temperature", float),
            "MKCODE_MAX_TOKENS": ("max_tokens", int),
            "OPENAI_API_KEY": ("api_key", str),
        }

        for env_var, (attr, transform) in env_map.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    setattr(cfg, attr, transform(value))
                except (ValueError, TypeError):
                    pass

        os.makedirs(cfg.data_dir, exist_ok=True)

        return cfg


config = AppConfig.load()
