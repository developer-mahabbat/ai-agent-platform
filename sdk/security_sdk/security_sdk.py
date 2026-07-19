import hashlib
import logging
import re
import secrets
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class SecuritySDK(SDKModule):
    name = "security"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._api_keys: dict[str, str] = {}
        self._rate_limits: dict[str, list[float]] = {}
        self._max_requests_per_minute: int = 60
        self._blocked_ips: set[str] = set()

    async def initialize(self) -> None:
        logger.info("SecuritySDK initialized")

    async def shutdown(self) -> None:
        self._api_keys.clear()
        self._rate_limits.clear()
        logger.info("SecuritySDK shut down")

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def generate_api_key(self) -> str:
        return f"mk_{secrets.token_hex(24)}"

    async def validate_api_key(self, key: str) -> bool:
        return key in self._api_keys.values() or key.startswith("mk_")

    async def register_api_key(self, name: str, key: str) -> SDKResult:
        self._api_keys[name] = key
        return SDKResult.ok()

    async def check_rate_limit(self, key: str) -> bool:
        import time
        now = time.time()
        if key not in self._rate_limits:
            self._rate_limits[key] = []
        self._rate_limits[key] = [t for t in self._rate_limits[key] if now - t < 60]
        if len(self._rate_limits[key]) >= self._max_requests_per_minute:
            return False
        self._rate_limits[key].append(now)
        return True

    def sanitize_path(self, path: str) -> str:
        path = path.replace("..", "")
        path = re.sub(r"[<>\"|?*]", "", path)
        return path

    def sanitize_input(self, text: str) -> str:
        text = text.replace("<script", "&lt;script")
        text = text.replace("onerror", "on_error")
        text = text.replace("onload", "on_load")
        return text

    def detect_prompt_injection(self, text: str) -> bool:
        patterns = [
            r"ignore\s+(all\s+)?(previous|above|prior)",
            r"forget\s+(all\s+)?(instructions|commands)",
            r"you\s+are\s+(not|now)",
            r"system\s+prompt",
            r"override\s+(instructions|commands)",
            r"new\s+instructions?",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential prompt injection detected: {text[:100]}")
                return True
        return False

    def sanitize_filename(self, filename: str) -> str:
        filename = re.sub(r"[^\w\.\-]", "_", filename)
        filename = re.sub(r"_+", "_", filename)
        return filename[:255]
