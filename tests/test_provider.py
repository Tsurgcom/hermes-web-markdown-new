"""Tests for the markdown.new provider: parsing, URL validation, extract shape."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from provider import _extract_body, _extract_title, _validate_url, _MAX_RESPONSE_BYTES
from provider import MarkdownNewWebSearchProvider


# --- parsing (original contract) ---

def test_markdown_new_envelope_parses_title_and_body():
    payload = "Title: Example page\nMarkdown Content:\n# Hello\n\nBody"
    assert _extract_title(payload) == "Example page"
    assert _extract_body(payload) == "# Hello\n\nBody"


def test_html_title_fallback():
    payload = "<html><head><title>Fallback</title></head><body>text</body></html>"
    assert _extract_title(payload) == "Fallback"


# --- URL validation (new safety gate) ---

def test_valid_urls_pass():
    assert _validate_url("https://example.com") == "https://example.com"
    assert _validate_url(" http://example.com/a?b=1 ") == "http://example.com/a?b=1"


def test_relative_and_non_http_schemes_rejected():
    for bad in ("example.com/page", "/etc/passwd", "file:///etc/passwd",
                "ftp://example.com", "javascript:alert(1)", "//example.com"):
        try:
            _validate_url(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad!r} should have been rejected")


def test_control_chars_and_whitespace_rejected():
    try:
        _validate_url("https://example.com/\r\nInjected: header")
    except ValueError:
        pass
    else:
        raise AssertionError("CRLF in URL should have been rejected")


def test_empty_and_overlong_urls_rejected():
    try:
        _validate_url("")
    except ValueError:
        pass
    else:
        raise AssertionError("empty URL should have been rejected")
    try:
        _validate_url("https://example.com/" + "a" * 3000)
    except ValueError:
        pass
    else:
        raise AssertionError("overlong URL should have been rejected")


# --- extract(): error shape and happy path (requests mocked) ---

def _fake_response(status=200, text="Title: T\nMarkdown Content:\nBody", headers=None):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = headers or {}
    resp.encoding = "utf-8"
    resp.iter_content = lambda chunk_size: iter([text.encode("utf-8")])
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_extract_returns_error_entry_on_invalid_url_never_raises():
    provider = MarkdownNewWebSearchProvider()
    results = provider.extract(["notaurl", "https://ok.example.com"])
    assert results[0]["error"].startswith("invalid URL:")
    assert results[0]["content"] == ""
    assert not results[1].get("error", "").startswith("invalid URL:")


def test_extract_success_envelope_shape():
    provider = MarkdownNewWebSearchProvider()
    with patch("requests.get", return_value=_fake_response()):
        results = provider.extract(["https://example.com"])
    r = results[0]
    assert r["url"] == "https://example.com"
    assert r["title"] == "T"
    assert r["content"] == "Body"
    assert r["metadata"]["sourceURL"] == "https://example.com"


def test_extract_403_becomes_per_url_error():
    provider = MarkdownNewWebSearchProvider()
    with patch("requests.get", return_value=_fake_response(status=403)):
        results = provider.extract(["https://example.com"])
    assert "403" in results[0]["error"]


def test_extract_429_retries_then_errors():
    provider = MarkdownNewWebSearchProvider()
    responses = [_fake_response(status=429), _fake_response(status=429)]
    with patch("requests.get", side_effect=responses), patch("time.sleep") as sleeper:
        results = provider.extract(["https://example.com"])
    assert "rate limit" in results[0]["error"]
    sleeper.assert_called()  # one bounded backoff happened


def test_extract_enforces_size_cap():
    provider = MarkdownNewWebSearchProvider()
    big = "x" * (_MAX_RESPONSE_BYTES + 1)
    resp = _fake_response(text=big)
    resp.iter_content = lambda chunk_size: iter(
        [big.encode("utf-8")[i:i + 65536] for i in range(0, len(big), 65536)]
    )
    with patch("requests.get", return_value=resp):
        results = provider.extract(["https://example.com"])
    assert "byte limit" in results[0]["error"]
