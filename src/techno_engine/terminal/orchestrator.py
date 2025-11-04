from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .ai_client import AIClient
from . import tools as toolmod
from .schemas import (
    RenderSessionInput,
    CreateConfigInput,
    ReadConfigInput,
    WriteConfigInput,
)


@dataclass
class OrchestratorResult:
    text: str
    tool_result: Optional[Dict[str, Any]] = None


class Orchestrator:
    def __init__(self, client: AIClient) -> None:
        self.client = client
        self.messages: List[Dict[str, Any]] = []

    def _tool_specs(self) -> List[Dict[str, Any]]:
        return [
            {"name": "render_session", "description": "Render a session to a MIDI file"},
            {"name": "create_config", "description": "Create a config JSON file"},
            {"name": "list_configs", "description": "List saved configs"},
            {"name": "read_config", "description": "Read a config JSON file"},
            {"name": "write_config", "description": "Write a config JSON file"},
            {"name": "list_examples", "description": "List example configs"},
            {"name": "help_text", "description": "Return help usage"},
        ]

    def process(self, user_text: str, max_steps: int = 3) -> OrchestratorResult:
        self.messages.append({"role": "user", "content": user_text})
        tool_result: Optional[Dict[str, Any]] = None
        for _ in range(max_steps):
            resp = self.client.complete(self.messages, self._tool_specs())
            if not isinstance(resp, dict) or "type" not in resp:
                return OrchestratorResult(text="(error) invalid AI response")
            if resp["type"] == "text":
                return OrchestratorResult(text=str(resp.get("text", "")), tool_result=tool_result)
            if resp["type"] == "tool_call":
                name = resp.get("name")
                args = resp.get("args", {}) or {}
                try:
                    tool_result = self._run_tool(name, args)
                    self.messages.append({
                        "role": "tool",
                        "name": name,
                        "content": json.dumps(tool_result),
                    })
                except Exception as e:  # return error for retry
                    self.messages.append({
                        "role": "tool",
                        "name": name,
                        "content": json.dumps({"error": str(e)}),
                    })
                    tool_result = None
                continue
            return OrchestratorResult(text="(error) unsupported AI response type")
        return OrchestratorResult(text="(error) max steps reached", tool_result=tool_result)

    def _run_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "render_session":
            out = toolmod.render_session(RenderSessionInput(**args))
            return {"path": out.path, "bpm": out.bpm, "bars": out.bars, "summary": out.summary}
        if name == "create_config":
            return toolmod.create_config(CreateConfigInput(**args))
        if name == "list_configs":
            return {"items": toolmod.list_configs().items}
        if name == "read_config":
            return toolmod.read_config(ReadConfigInput(**args))
        if name == "write_config":
            return toolmod.write_config(WriteConfigInput(**args))
        if name == "list_examples":
            return {"items": toolmod.list_examples().items}
        if name == "help_text":
            return {"usage": toolmod.help_text().usage}
        raise ValueError(f"unknown tool: {name}")

