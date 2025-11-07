from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List
import ssl
try:  # Prefer certifi bundle for broader CA support
    import certifi  # type: ignore
    _HAS_CERTIFI = True
except Exception:  # pragma: no cover
    certifi = None  # type: ignore
    _HAS_CERTIFI = False

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
                        "parameters": t.get("parameters", {"type": "object", "properties": {}, "additionalProperties": True}),
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
                "OpenAI-Beta": "tools=true",
            },
            method="POST",
        )
        # Use a CA bundle with certifi when available to avoid local trust store issues
        context = ssl.create_default_context(cafile=certifi.where()) if _HAS_CERTIFI else ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=context) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
            return {"type": "text", "text": f"OpenAI error: {e.code} {e.reason}: {detail}"}
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
            return {
                "type": "tool_call",
                "name": name,
                "args": args,
                "args_json": arg_str,
                "tool_call_id": call.get("id"),
            }
        content = msg.get("content") or ""
        return {"type": "text", "text": content}
