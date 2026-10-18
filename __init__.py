"""markdown.new web extract plugin — keyless page-to-markdown.

The backing service (https://markdown.new) is a third-party project by
elbeyoglu.com — not Cloudflare official; all extracted content transits it.
"""

from __future__ import annotations

try:
    from .provider import MarkdownNewWebSearchProvider
except ImportError:  # pragma: no cover - supports direct test collection
    from provider import MarkdownNewWebSearchProvider


def register(ctx) -> None:
    """Register the markdown.new provider with the plugin context."""
    ctx.register_web_search_provider(MarkdownNewWebSearchProvider())
