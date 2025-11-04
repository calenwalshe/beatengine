from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List

from .ai_client import AIClient


class OpenAIHTTPClient(AIClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        # Minimal schema; tool will validate inputs server-side
                        "parameters": {"type": "object", "properties": {}, "additionalProperties": True},
                    },
                }
                for t in tools
            ],
            "tool_choice": "auto",
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Return a text response so the orchestrator can surface the error
            return {"type": "text", "text": f"OpenAI error: {e.code} {e.reason}"}
        except Exception as e:  # timeout, network, etc.
            return {"type": "text", "text": f"OpenAI error: {e}"}

        choice = (data.get("choices") or [{}])[0]
        msg = (choice.get("message") or {})
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            call = tool_calls[0]
            fn = call.get("function", {})
            name = fn.get("name")
            arg_str = fn.get("arguments") or "{}"
            try:
                args = json.loads(arg_str)
            except Exception:
                args = {}
            return {"type": "tool_call", "name": name, "args": args}
        content = msg.get("content") or ""
        return {"type": "text", "text": content}

