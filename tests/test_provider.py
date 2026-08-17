import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from provider import _extract_body, _extract_title


def test_markdown_new_envelope_parses_title_and_body():
    payload = "Title: Example page\nMarkdown Content:\n# Hello\n\nBody"
    assert _extract_title(payload) == "Example page"
    assert _extract_body(payload) == "# Hello\n\nBody"


def test_html_title_fallback():
    payload = "<html><head><title>Fallback</title></head><body>text</body></html>"
    assert _extract_title(payload) == "Fallback"
