from __future__ import annotations

import os

from techno_engine.terminal.settings import load_settings
from techno_engine.terminal.app import TerminalApp


def test_settings_reads_openai_model_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-2025-08-07")
    s = load_settings()
    assert s.openai_api_key == "sk-test"
    assert s.model == "gpt-5-2025-08-07"


def test_app_uses_model_env_for_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-2025-08-07")
    app = TerminalApp()
    orch = app._get_orchestrator()
    assert orch is not None
    # The OpenAIHTTPClient stores the selected model on the client
    assert getattr(orch.client, "model", None) == "gpt-5-2025-08-07"

