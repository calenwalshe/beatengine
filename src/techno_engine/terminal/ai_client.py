from __future__ import annotations

from typing import Any, Dict, List


class AIClient:
    """Interface for an AI client. In M2 tests, use a mock implementation.

    The `complete` method returns either:
      {"type": "tool_call", "name": str, "args": dict}
    or
      {"type": "text", "text": str}
    """

    def complete(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

