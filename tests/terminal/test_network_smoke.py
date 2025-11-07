from __future__ import annotations

import json
import os
import ssl
import urllib.request
import urllib.error
import pytest


def _tls_context():
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # pragma: no cover
        return ssl.create_default_context()


def _require_smoke_env():
    if os.environ.get("OPENAI_NETWORK_SMOKE") != "1":
        pytest.skip("network smoke disabled; set OPENAI_NETWORK_SMOKE=1 to enable")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip("missing OPENAI_API_KEY in environment")
    return key


def test_chat_completions_basic_roundtrip():
    key = _require_smoke_env()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=_tls_context(), timeout=20) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert isinstance(data.get("choices"), list)


def test_chat_completions_tools_header_roundtrip():
    key = _require_smoke_env()
    if os.environ.get("OPENAI_TOOL_SMOKE") != "1":
        pytest.skip("tool smoke disabled; set OPENAI_TOOL_SMOKE=1 to enable")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "call a function"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "render_session",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        "tool_choice": "auto",
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "OpenAI-Beta": "tools=true",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=_tls_context(), timeout=20) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        # We only assert the response shape is valid JSON with choices
        assert isinstance(data.get("choices"), list)

