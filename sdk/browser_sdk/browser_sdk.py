import logging
from typing import Any, Optional

import httpx

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class BrowserSDK(SDKModule):
    name = "browser"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._client: Optional[httpx.AsyncClient] = None
        self._headless: bool = True
        self._viewport: dict[str, int] = {"width": 1280, "height": 720}

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(30),
            headers={"User-Agent": "Mozilla/5.0 (compatible; MKCode/1.0)"},
        )
        logger.info("BrowserSDK initialized")

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
        logger.info("BrowserSDK shut down")

    async def fetch_page(self, url: str) -> SDKResult[str]:
        if not self._client:
            return SDKResult.fail("HTTP client not initialized")
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return SDKResult.ok(response.text)
        except httpx.HTTPStatusError as e:
            return SDKResult.fail(f"HTTP {e.response.status_code}")
        except Exception as e:
            return SDKResult.fail(str(e))

    async def fetch_json(self, url: str) -> SDKResult[dict]:
        if not self._client:
            return SDKResult.fail("HTTP client not initialized")
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return SDKResult.ok(response.json())
        except Exception as e:
            return SDKResult.fail(str(e))

    async def screenshot(self, url: str) -> SDKResult[bytes]:
        return SDKResult.fail("Screenshot requires Playwright integration")

    async def click(self, selector: str) -> SDKResult:
        return SDKResult.fail("Browser automation requires Playwright integration")

    async def type_text(self, selector: str, text: str) -> SDKResult:
        return SDKResult.fail("Browser automation requires Playwright integration")

    async def extract_text(self, html: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def extract_links(self, html: str, base_url: str = "") -> list[dict[str, str]]:
        import re
        links = []
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html):
            href = match.group(1)
            if href.startswith("http"):
                links.append({"url": href})
            elif base_url:
                from urllib.parse import urljoin
                links.append({"url": urljoin(base_url, href)})
        return links
