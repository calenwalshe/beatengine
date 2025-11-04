from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from techno_engine.terminal.orchestrator import Orchestrator
from techno_engine.terminal.ai_client import AIClient


class MockClient(AIClient):
    def __init__(self, plan: List[Dict[str, Any]]):
        self.plan = list(plan)

    def complete(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.plan:
            return {"type": "text", "text": "(mock end)"}
        return self.plan.pop(0)


def _tmp_dirs(tmp_path: Path):
    os.environ["TECH_ENGINE_CONFIGS_DIR"] = str(tmp_path / "configs")
    os.environ["TECH_ENGINE_OUT_DIR"] = str(tmp_path / "out")


def test_orchestrator_renders_mid(tmp_path: Path):
    _tmp_dirs(tmp_path)
    # First call: tool call to render_session; second: final text
    plan = [
        {
            "type": "tool_call",
            "name": "render_session",
            "args": {"inline_config": {"mode": "m1", "bpm": 132, "ppq": 1920, "bars": 4}},
        },
        {"type": "text", "text": "Rendered"},
    ]
    orch = Orchestrator(MockClient(plan))
    res = orch.process("make something", max_steps=3)
    assert res.text == "Rendered"
    assert res.tool_result and Path(res.tool_result["path"]).exists()


def test_orchestrator_offdomain_refusal(tmp_path: Path):
    _tmp_dirs(tmp_path)
    plan = [{"type": "text", "text": "Sorry, I can only generate techno MIDI or assist with configs."}]
    orch = Orchestrator(MockClient(plan))
    res = orch.process("open a web browser")
    assert "Sorry" in res.text


def test_orchestrator_retry_on_invalid_args(tmp_path: Path):
    _tmp_dirs(tmp_path)
    plan = [
        {"type": "tool_call", "name": "render_session", "args": {}},  # invalid
        {
            "type": "tool_call",
            "name": "render_session",
            "args": {"inline_config": {"mode": "m1", "bpm": 130, "ppq": 1920, "bars": 4}},
        },
        {"type": "text", "text": "Done"},
    ]
    orch = Orchestrator(MockClient(plan))
    res = orch.process("generate something", max_steps=5)
    assert res.text == "Done"
    assert res.tool_result and Path(res.tool_result["path"]).exists()

