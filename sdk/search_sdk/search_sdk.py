import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote_plus, urlparse

import httpx

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class SearchResult:
    def __init__(self, title: str = "", url: str = "", snippet: str = "", source: str = ""):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source

    def to_dict(self) -> dict:
        return {"title": self.title, "url": self.url, "snippet": self.snippet, "source": self.source}


class SearchSDK(SDKModule):
    name = "search"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(30),
            headers={"User-Agent": "Mozilla/5.0 (compatible; MKCode/1.0)"},
        )
        logger.info("SearchSDK initialized")

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
        logger.info("SearchSDK shut down")

    async def search_duckduckgo(self, query: str, max_results: int = 10) -> list[SearchResult]:
        if not self._client:
            return []
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            resp = await self._client.get(url)
            resp.raise_for_status()
            return self._parse_ddg_html(resp.text, max_results)
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    def _parse_ddg_html(self, html: str, max_results: int) -> list[SearchResult]:
        results = []
        for match in re.finditer(
            r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>.*?'
            r'<a class="result__snippet".*?>(.*?)</a>',
            html, re.DOTALL,
        ):
            url = self._clean_url(match.group(1))
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()
            results.append(SearchResult(title=title, url=url, snippet=snippet, source="duckduckgo"))
            if len(results) >= max_results:
                break
        if not results:
            for match in re.finditer(
                r'class="result__body".*?href="(.*?)".*?class="result__title".*?>(.*?)</a>.*?'
                r'class="result__snippet".*?>(.*?)</',
                html, re.DOTALL,
            ):
                url = self._clean_url(match.group(1))
                title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()
                results.append(SearchResult(title=title, url=url, snippet=snippet, source="duckduckgo"))
                if len(results) >= max_results:
                    break
        return results

    def _clean_url(self, url: str) -> str:
        url = url.replace("&amp;", "&")
        if "//duckduckgo.com/l/?uddg=" in url:
            from urllib.parse import unquote
            m = re.search(r"uddg=([^&]+)", url)
            if m:
                return unquote(m.group(1))
        return url

    async def search_opencode(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self._client:
            return []
        try:
            prompt = (
                f"Search the web for: {query}\n\n"
                f"Return a JSON array of search results with 'title', 'url', and 'snippet' fields. "
                f"Return exactly {max_results} results. Only return valid JSON."
            )
            resp = await self._client.post(
                "https://opencode.ai/zen/v1/chat/completions",
                json={
                    "model": "deepseek-v4-flash-free",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            arr = self._extract_json_array(content)
            return [
                SearchResult(title=r.get("title", ""), url=r.get("url", ""), snippet=r.get("snippet", ""), source="opencode")
                for r in arr[:max_results]
            ]
        except Exception as e:
            logger.warning(f"OpenCode search failed: {e}")
            return []

    def _extract_json_array(self, text: str) -> list[dict]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\[.*?\]", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
            return []

    async def search(self, query: str, provider: str = "auto", max_results: int = 10) -> SDKResult[list[dict]]:
        results: list[SearchResult] = []

        if provider in ("auto", "duckduckgo"):
            results = await self.search_duckduckgo(query, max_results)

        if not results and provider in ("auto", "opencode"):
            results = await self.search_opencode(query, max_results)

        if not results:
            return SDKResult.fail(f"No results from any search provider for: {query}")

        return SDKResult.ok([r.to_dict() for r in results])

    async def fetch_page(self, url: str) -> SDKResult[str]:
        if not self._client:
            return SDKResult.fail("Client not initialized")
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            text = resp.text
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return SDKResult.ok(text[:10000])
        except Exception as e:
            return SDKResult.fail(str(e))
