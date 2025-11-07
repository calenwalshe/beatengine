from __future__ import annotations

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


def test_orchestrator_bass_generate_and_validate(tmp_path: Path):
    _tmp_dirs(tmp_path)
    # First generate MVP bass events, then validate (empty events allowed to smoke test schema)
    plan = [
        {
            "type": "tool_call",
            "name": "bass_generate",
            "args": {"bpm": 120.0, "ppq": 1920, "bars": 4, "mode": "mvp", "root_note": 45, "density": 0.4},
        },
        {
            "type": "tool_call",
            "name": "bass_validate",
            "args": {"bpm": 120.0, "ppq": 1920, "bars": 4, "density": 0.4, "events": []},
        },
        {"type": "text", "text": "ok"},
    ]
    orch = Orchestrator(MockClient(plan))
    res = orch.process("bass please", max_steps=6)
    assert res.text == "ok"
