"""Standalone test support: stub the Hermes runtime import when absent.

Inside a Hermes checkout the real `agent.web_search_provider` is importable
and is used as-is. Outside one (CI, bare venv) we stub a structurally
equivalent base class so the provider module and tests can import.
"""

import sys
import types

try:  # exercised inside a Hermes checkout; falls back for CI/bare venvs
    import agent.web_search_provider  # noqa: F401
except ImportError:  # standalone runs (tests/CI)
    agent = types.ModuleType("agent")
    wsp = types.ModuleType("agent.web_search_provider")

    class WebSearchProvider:  # structural stub
        pass

    setattr(wsp, "WebSearchProvider", WebSearchProvider)
    setattr(agent, "web_search_provider", wsp)
    sys.modules.setdefault("agent", agent)
    sys.modules["agent.web_search_provider"] = wsp
