import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class FileSystemSDK(SDKModule):
    name = "filesystem"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._workspace_root: Path = Path.cwd()
        self._allowed_extensions: set[str] = set()
        self._blocked_patterns: list[str] = []

    async def initialize(self) -> None:
        logger.info("FileSystemSDK initialized")

    async def shutdown(self) -> None:
        logger.info("FileSystemSDK shut down")

    def set_workspace(self, path: str) -> None:
        self._workspace_root = Path(path).resolve()

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self._workspace_root / p
        return p.resolve()

    def _is_safe(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self._workspace_root.resolve())
            return True
        except ValueError:
            return False

    async def read_file(self, path: str) -> SDKResult[str]:
        try:
            full = self._resolve_path(path)
            if not self._is_safe(full):
                return SDKResult.fail("Path outside workspace")
            if not full.exists():
                return SDKResult.fail(f"File not found: {path}")
            if not full.is_file():
                return SDKResult.fail(f"Not a file: {path}")
            content = full.read_text(encoding="utf-8")
            return SDKResult.ok(content)
        except Exception as e:
            return SDKResult.fail(str(e))

    async def write_file(self, path: str, content: str) -> SDKResult:
        try:
            full = self._resolve_path(path)
            if not self._is_safe(full):
                return SDKResult.fail("Path outside workspace")
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            logger.info(f"Wrote file: {full}")
            return SDKResult.ok()
        except Exception as e:
            return SDKResult.fail(str(e))

    async def delete_file(self, path: str) -> SDKResult:
        try:
            full = self._resolve_path(path)
            if not self._is_safe(full):
                return SDKResult.fail("Path outside workspace")
            if full.is_file():
                full.unlink()
            elif full.is_dir():
                shutil.rmtree(full)
            else:
                return SDKResult.fail(f"Not found: {path}")
            return SDKResult.ok()
        except Exception as e:
            return SDKResult.fail(str(e))

    async def list_dir(self, path: str = ".") -> SDKResult[list[dict[str, Any]]]:
        try:
            full = self._resolve_path(path)
            if not self._is_safe(full):
                return SDKResult.fail("Path outside workspace")
            if not full.is_dir():
                return SDKResult.fail(f"Not a directory: {path}")
            entries = []
            for entry in sorted(full.iterdir()):
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(self._workspace_root)),
                    "type": "directory" if entry.is_dir() else "file",
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
            return SDKResult.ok(entries)
        except Exception as e:
            return SDKResult.fail(str(e))

    async def exists(self, path: str) -> bool:
        return self._resolve_path(path).exists()

    async def mkdir(self, path: str) -> SDKResult:
        try:
            full = self._resolve_path(path)
            if not self._is_safe(full):
                return SDKResult.fail("Path outside workspace")
            full.mkdir(parents=True, exist_ok=True)
            return SDKResult.ok()
        except Exception as e:
            return SDKResult.fail(str(e))

    async def copy(self, src: str, dst: str) -> SDKResult:
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            if not self._is_safe(src_path) or not self._is_safe(dst_path):
                return SDKResult.fail("Path outside workspace")
            if src_path.is_file():
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copytree(src_path, dst_path)
            return SDKResult.ok()
        except Exception as e:
            return SDKResult.fail(str(e))

    async def move(self, src: str, dst: str) -> SDKResult:
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            if not self._is_safe(src_path) or not self._is_safe(dst_path):
                return SDKResult.fail("Path outside workspace")
            shutil.move(str(src_path), str(dst_path))
            return SDKResult.ok()
        except Exception as e:
            return SDKResult.fail(str(e))

    async def get_info(self, path: str) -> SDKResult[dict[str, Any]]:
        try:
            full = self._resolve_path(path)
            if not full.exists():
                return SDKResult.fail(f"Not found: {path}")
            stat = full.stat()
            return SDKResult.ok({
                "name": full.name,
                "path": str(full.relative_to(self._workspace_root)) if self._is_safe(full) else str(full),
                "type": "directory" if full.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "permissions": oct(stat.st_mode)[-3:],
            })
        except Exception as e:
            return SDKResult.fail(str(e))
