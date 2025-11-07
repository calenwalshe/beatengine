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
    ReadDocInput,
    SearchDocsInput,
    DocAnswerInput,
)


@dataclass
class OrchestratorResult:
    text: str
    tool_result: Optional[Dict[str, Any]] = None


class Orchestrator:
    def __init__(self, client: AIClient, system_prompt: Optional[str] = None, developer_prompt: Optional[str] = None) -> None:
        self.client = client
        self.messages: List[Dict[str, Any]] = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
        if developer_prompt:
            self.messages.append({"role": "system", "content": developer_prompt})

    def _tool_specs(self) -> List[Dict[str, Any]]:
        obj = lambda props, req=None: {
            "type": "object",
            "properties": props,
            "required": req or [],
            "additionalProperties": False,
        }
        str_t = {"type": "string"}
        num_t = {"type": "number"}
        int_t = {"type": "integer"}
        bool_t = {"type": "boolean"}
        inline_cfg = obj({
            "mode": {"type": "string", "enum": ["m1", "m2", "m4"]},
            "bpm": num_t,
            "ppq": int_t,
            "bars": int_t,
        })
        specs = [
            {
                "name": "render_session",
                "description": "Render a session to a MIDI file",
                "parameters": obj({
                    "config_path": str_t,
                    "inline_config": inline_cfg,
                })
            },
            {
                "name": "bass_generate",
                "description": "Generate bass events (MVP or scored)",
                "parameters": obj({
                    "version": str_t,
                    "bpm": num_t,
                    "ppq": int_t,
                    "bars": int_t,
                    "seed": int_t,
                    "mode": {"type": "string", "enum": ["mvp", "scored"]},
                    "root_note": int_t,
                    "density": num_t,
                    "min_dur_steps": num_t,
                    "style": str_t,
                    "kick_masks_by_bar": {"type": "array"},
                    "hat_masks_by_bar": {"type": "array"},
                    "clap_masks_by_bar": {"type": "array"}
                })
            },
            {
                "name": "bass_validate",
                "description": "Validate and lock bass events (density/monophony)",
                "parameters": obj({
                    "version": str_t,
                    "bpm": num_t,
                    "ppq": int_t,
                    "bars": int_t,
                    "density": num_t,
                    "events": {"type": "array"}
                })
            },
            {
                "name": "doc_answer",
                "description": "Summarize documentation relevant to a query",
                "parameters": obj({
                    "query": str_t,
                    "max_sources": int_t,
                    "context_window": int_t,
                }, req=["query"]),
            },
            {
                "name": "list_docs",
                "description": "List available documentation files",
                "parameters": obj({}),
            },
            {
                "name": "read_doc",
                "description": "Read a documentation file (optionally a range)",
                "parameters": obj({
                    "name": str_t,
                    "start_line": int_t,
                    "max_lines": int_t,
                }, req=["name"]),
            },
            {
                "name": "search_docs",
                "description": "Search documentation files for a query",
                "parameters": obj({
                    "query": str_t,
                    "max_results": int_t,
                }, req=["query"]),
            },
            {
                "name": "agent_handle",
                "description": "Interpret a natural-language request offline and render a groove",
                "parameters": obj({
                    "prompt": str_t,
                }, req=["prompt"]),
            },
            {
                "name": "create_config",
                "description": "Create a config JSON file",
                "parameters": obj({
                    "name": str_t,
                    "params": {"type": "object"},
                }, req=["name", "params"]),
            },
            {
                "name": "list_configs",
                "description": "List saved configs",
                "parameters": obj({}),
            },
            {
                "name": "read_config",
                "description": "Read a config JSON file",
                "parameters": obj({"name": str_t}, req=["name"]),
            },
            {
                "name": "write_config",
                "description": "Write a config JSON file",
                "parameters": obj({"name": str_t, "body": str_t}, req=["name", "body"]),
            },
            {
                "name": "list_examples",
                "description": "List example configs",
                "parameters": obj({}),
            },
            {
                "name": "help_text",
                "description": "Return help usage",
                "parameters": obj({}),
            },
        ]
        specs.append({
            "name": "make_bass_for_config",
            "description": "Render drums from config and generate+validate a scored bassline (returns two paths)",
            "parameters": obj({
                "config_path": str_t,
                "drums_out": str_t,
                "bass_out": str_t,
                "key": str_t,
                "mode": str_t,
                "density": num_t,
                "root_note": int_t,
            }, req=["config_path"]),
        })
        return specs

    def process(self, user_text: str, max_steps: int = 6) -> OrchestratorResult:
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
                tool_call_id = resp.get("tool_call_id")
                args = resp.get("args", {}) or {}
                args_json = resp.get("args_json", "{}")
                # Record assistant message with tool call so the follow-up is valid
                self.messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": args_json,
                            },
                        }
                    ],
                })
                try:
                    tool_result = self._run_tool(name, args)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(tool_result),
                    })
                except Exception as e:  # return error for retry
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
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
        if name == "doc_answer":
            out = toolmod.doc_answer(DocAnswerInput(**args))
            return {
                "summary": out.summary,
                "sources": [
                    {"path": s.path, "line": s.line} for s in out.sources
                ],
            }
        if name == "agent_handle":
            result = toolmod.agent_handle(args.get("prompt", ""))
            return result
        if name == "create_config":
            return toolmod.create_config(CreateConfigInput(**args))
        if name == "list_docs":
            return {"items": toolmod.list_docs().items}
        if name == "read_doc":
            out = toolmod.read_doc(ReadDocInput(**args))
            return {"path": out.path, "body": out.body}
        if name == "search_docs":
            out = toolmod.search_docs(SearchDocsInput(**args))
            return {"results": [
                {"path": h.path, "line": h.line, "snippet": h.snippet} for h in out.results
            ]}
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
        if name == "bass_generate":
            return toolmod.bass_generate(args)
        if name == "bass_validate":
            return toolmod.bass_validate(args)
        if name == "make_bass_for_config":
            return toolmod.make_bass_for_config(args)
        raise ValueError(f"unknown tool: {name}")
