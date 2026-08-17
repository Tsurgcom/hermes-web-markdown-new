"""Cloudflare markdown.new web extract provider — keyless, local plugin.

Fetches pages through Cloudflare's free page-to-markdown service
(https://markdown.new/<url>). No API key required. Returns the same
``Title:`` / ``Markdown Content:`` envelope format as Jina Reader, so the
parsers share shape.

Extract-only: pair with the ddgs search backend. Registered as backend
name ``markdown-new`` — set ``web.extract_backend: markdown-new`` in
config.yaml.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

_MDNEW_BASE = "https://markdown.new/"
_FETCH_TIMEOUT_SECS = 30


class MarkdownNewWebSearchProvider(WebSearchProvider):
    """Extract web page content as markdown via Cloudflare markdown.new."""

    @property
    def name(self) -> str:
        return "markdown-new"

    @property
    def display_name(self) -> str:
        return "Cloudflare markdown.new"

    def is_available(self) -> bool:
        """Keyless — always usable as long as the requests dep is importable."""
        try:
            import requests  # noqa: F401
            return True
        except Exception:
            return False

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        return {
            "success": False,
            "error": (
                "markdown-new is an extract-only backend (Cloudflare "
                "markdown.new). Use the ddgs search backend for web_search."
            ),
        }

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Fetch each URL through markdown.new and return markdown content.

        One result dict per URL; per-URL failures are returned as entries
        with an ``error`` field (never raised), matching the legacy
        web_extract_tool post-processing pipeline.
        """
        import requests

        results: List[Dict[str, Any]] = []
        for url in urls:
            try:
                resp = requests.get(
                    _MDNEW_BASE + url,
                    timeout=_FETCH_TIMEOUT_SECS,
                    headers={"Accept": "text/markdown"},
                )
                if resp.status_code == 429:
                    raise RuntimeError(
                        "markdown.new rate limit hit. Try again shortly."
                    )
                if resp.status_code == 403:
                    raise RuntimeError(
                        "markdown.new refused the request (403). The page may "
                        "block the converter, or the service requires an API key."
                    )
                resp.raise_for_status()
                text = resp.text
                title = _extract_title(text)
                content = _extract_body(text)
                results.append(
                    {
                        "url": url,
                        "title": title,
                        "content": content,
                        "raw_content": text,
                        "metadata": {"sourceURL": url, "title": title},
                    }
                )
            except Exception as exc:  # noqa: BLE001 — per-URL errors are data
                logger.warning("markdown.new extract failed for %s: %s", url, exc)
                results.append(
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "error": f"markdown.new extract failed: {exc}",
                    }
                )
        return results

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Cloudflare markdown.new",
            "badge": "free · no key · extract",
            "tag": (
                "Keyless markdown extraction via Cloudflare markdown.new — "
                "pair with the ddgs search backend. No env vars."
            ),
            "env_vars": [],
        }


def _extract_title(text: str) -> str:
    """Pull the ``Title:`` line both services prefix to every response."""
    m = re.search(r"^Title:\s*(.+)$", text, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_body(text: str) -> str:
    """Strip the header block; return the markdown body."""
    marker = "Markdown Content:"
    idx = text.find(marker)
    if idx != -1:
        return text[idx + len(marker):].strip()
    # No marker (e.g. error page) — keep everything after the Title line.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lower().startswith("title:"):
            return "\n".join(lines[i + 1:]).strip()
    return text.strip()
