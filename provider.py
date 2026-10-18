"""Cloudflare markdown.new web extract provider — keyless, local plugin.

Fetches pages through Cloudflare's free page-to-markdown service
(https://markdown.new/<url>). No API key required. Returns the same
``Title:`` / ``Markdown Content:`` envelope format as Jina Reader, so the
parsers share shape.

Security posture (see SECURITY.md):

* only absolute ``http``/``https`` URLs are accepted — each URL is
  validated before it is ever used in a request;
* outbound traffic goes to exactly one host: ``https://markdown.new``;
* responses are streamed with a hard byte cap so a hostile or broken
  upstream cannot exhaust memory;
* requests always carry a timeout; transient 429/5xx responses are
  retried once with a short bounded backoff;
* per-URL failures are returned as data (never raised), matching the
  legacy web_extract_tool post-processing pipeline.

Extract-only: pair with the ddgs search backend. Registered as backend
name ``markdown-new`` — set ``web.extract_backend: markdown-new`` in
config.yaml.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List
from urllib.parse import urlparse

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

_MDNEW_BASE = "https://markdown.new/"
_FETCH_TIMEOUT_SECS = 30
_MAX_URL_LENGTH = 2048
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_RETRIES = 1
_RETRY_BACKOFF_SECS = 4.0
_MAX_RETRY_AFTER_SECS = 15.0
_USER_AGENT = (
    "hermes-web-markdown-new/1.1 "
    "(+https://github.com/Tsurgcom/hermes-web-markdown-new)"
)


def _validate_url(url: str) -> str:
    """Return a whitespace-trimmed URL that is safe to send, or raise ValueError.

    Rules (deliberately strict — this is the only gate before the URL is
    placed in an outbound request path):

    * non-empty, <= _MAX_URL_LENGTH characters;
    * no whitespace or ASCII control characters (blocks header/request
      smuggling via crafted URLs);
    * absolute URL with scheme http or https and a hostname — anything
      else (relative paths, ``file:``, ``ftp:``, ``javascript:``) is
      rejected instead of being silently concatenated onto the base.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        raise ValueError("empty URL")
    if len(cleaned) > _MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds {_MAX_URL_LENGTH} characters")
    for ch in cleaned:
        if ch.isspace() or ord(ch) < 0x20:
            raise ValueError("URL contains whitespace or control characters")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("only absolute http(s) URLs are supported")
    return cleaned


def _retry_delay(resp: Any) -> float:
    """Respect Retry-After when sane, else fall back to the default backoff."""
    raw = (resp.headers or {}).get("Retry-After", "")
    try:
        delay = float(str(raw).strip())
    except (TypeError, ValueError):
        return _RETRY_BACKOFF_SECS
    if delay <= 0 or delay > _MAX_RETRY_AFTER_SECS:
        return _RETRY_BACKOFF_SECS
    return delay


def _fetch_markdown(url: str) -> str:
    """GET one URL through markdown.new and return the response text.

    Raises RuntimeError / requests.RequestException on failure; the caller
    converts that into a per-URL error entry.
    """
    import requests

    last_error: Exception | None = None
    for attempt in range(_ALLOWED_RETRIES + 1):
        try:
            with requests.get(
                _MDNEW_BASE + url,
                timeout=_FETCH_TIMEOUT_SECS,
                headers={"Accept": "text/markdown", "User-Agent": _USER_AGENT},
                stream=True,
            ) as resp:
                # Transient upstream conditions: back off once, then retry.
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < _ALLOWED_RETRIES:
                    delay = _retry_delay(resp)
                    logger.info(
                        "markdown.new returned %s for %s — retrying in %.0fs",
                        resp.status_code, url, delay,
                    )
                    time.sleep(delay)
                    continue
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

                # Stream with a hard byte cap: never buffer an unbounded body.
                chunks: List[bytes] = []
                received = 0
                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > _MAX_RESPONSE_BYTES:
                        raise RuntimeError(
                            f"markdown.new response exceeds "
                            f"{_MAX_RESPONSE_BYTES} byte limit"
                        )
                    chunks.append(chunk)
                encoding = resp.encoding or "utf-8"
                return b"".join(chunks).decode(encoding, errors="replace")
        except Exception as exc:  # noqa: BLE001 — per-URL errors are data
            last_error = exc
            # Only the transient conditions above are worth a second try;
            # anything else fails fast on the final attempt.
            if attempt >= _ALLOWED_RETRIES:
                raise
            if isinstance(exc, (RuntimeError, ValueError)):
                raise
            logger.info("markdown.new request error for %s: %s", url, exc)
            time.sleep(_RETRY_BACKOFF_SECS)
    raise RuntimeError(f"markdown.new extract failed: {last_error}")


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
        with an ``error`` field (never raised).
        """
        import requests

        results: List[Dict[str, Any]] = []
        for url in urls:
            try:
                clean = _validate_url(url)
            except ValueError as exc:
                logger.warning("markdown.new rejected URL %r: %s", url, exc)
                results.append(
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "error": f"invalid URL: {exc}",
                    }
                )
                continue
            try:
                text = _fetch_markdown(clean)
            except (requests.RequestException, RuntimeError) as exc:
                logger.warning("markdown.new extract failed for %s: %s", clean, exc)
                results.append(
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "error": f"markdown.new extract failed: {exc}",
                    }
                )
                continue
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
