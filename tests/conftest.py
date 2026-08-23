from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def disable_langsmith_network_tracing(monkeypatch):
    """Unit tests should never send traces or depend on network access."""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
