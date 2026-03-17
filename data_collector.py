"""
Data Collector
==============
Gathers current market information for a sector using:
1. DuckDuckGo instant-answer / search (no API key required)
2. Light HTML scraping of result snippets

The collected text is returned as a structured dict that the AI analyzer
can use to write the report.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger("data_collector")

# DuckDuckGo HTML search URL (no JS, no key)
DDG_URL = "https://html.duckduckgo.com/html/"

INDIA_TRADE_QUERIES = [
    "{sector} India trade opportunities 2024 2025",
    "{sector} India export import market growth",
    "{sector} India industry news latest",
    "India {sector} sector government policy FDI",
]


class DataCollector:
    def __init__(self) -> None:
        self.timeout = httpx.Timeout(settings.REQUEST_TIMEOUT)

    # ── Public API ──────────────────────────────────────────────────────────────

    async def collect(self, sector: str) -> dict[str, Any]:
        """
        Run multiple searches concurrently and aggregate snippets.

        Returns a dict with keys:
            sector, timestamp, snippets (list of {title, snippet, url})
        """
        queries = [q.format(sector=sector) for q in INDIA_TRADE_QUERIES]
        tasks   = [self._search_ddg(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        snippets: list[dict] = []
        for r in results:
            if isinstance(r, list):
                snippets.extend(r)

        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[dict] = []
        for item in snippets:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)

        unique = unique[: settings.SEARCH_MAX_RESULTS * len(queries)]

        logger.info("Collected %d snippets for sector='%s'", len(unique), sector)
        return {
            "sector": sector,
            "timestamp": datetime.utcnow().isoformat(),
            "snippets": unique,
        }

    # ── Internal helpers ────────────────────────────────────────────────────────

    async def _search_ddg(self, query: str) -> list[dict]:
        """Perform a DuckDuckGo HTML search and return result snippets."""
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "Mozilla/5.0 (compatible; TradeOpportunitiesBot/1.0)"},
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.post(DDG_URL, data={"q": query, "b": ""})
                resp.raise_for_status()
                return self._parse_ddg_html(resp.text)
        except Exception as exc:
            logger.warning("DuckDuckGo search failed for query '%s': %s", query, exc)
            return []

    @staticmethod
    def _parse_ddg_html(html: str) -> list[dict]:
        """Extract result titles, snippets, and URLs from DuckDuckGo HTML."""
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for result in soup.select(".result"):
            title_tag   = result.select_one(".result__title")
            snippet_tag = result.select_one(".result__snippet")
            link_tag    = result.select_one(".result__url")

            title   = title_tag.get_text(strip=True)   if title_tag   else ""
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            url     = link_tag.get_text(strip=True)    if link_tag    else ""

            # Skip ads / empty results
            if not title or not snippet:
                continue

            # Normalise URL (DuckDuckGo sometimes gives relative paths)
            if url and not url.startswith("http"):
                url = "https://" + url.lstrip("/")

            items.append({"title": title, "snippet": snippet, "url": url})

        return items
