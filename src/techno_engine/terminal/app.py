from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

from .settings import load_settings
from .orchestrator import Orchestrator
from .ai_openai import OpenAIHTTPClient
from . import tools as toolmod


WELCOME = "Berlin Techno App — type :help for commands"


@dataclass
class Reply:
    action: str  # "ok", "quit"
    output: str


class TerminalApp:
    def __init__(self) -> None:
        self.running = True
        self._orch: Optional[Orchestrator] = None

    def handle_line(self, line: str) -> Reply:
        s = (line or "").strip()
        if not s:
            return Reply("ok", "")
        # Local commands
        if s in (":quit", ":q", ":exit"):
            self.running = False
            return Reply("quit", "Goodbye.")
        if s in (":help", ":h", "help"):
            return Reply("ok", self._help_text())
        if s in (":about", ":a"):
            return Reply("ok", "Berlin Techno App — terminal UI for generating techno MIDI via sandboxed tools.")
        # If API key present, route to orchestrator (M3); else M0 message
        orch = self._get_orchestrator()
        if orch is None:
            return Reply("ok", "No AI. Ask Calen for key and export OPENAI_API_KEY then retry. Try :help.")
        res = orch.process(s)
        return Reply("ok", res.text)

    def _help_text(self) -> str:
        return (
            "Commands:\n"
            "  :help          Show this help\n"
            "  :about         About this assistant\n"
            "  :quit          Exit the terminal\n\n"
            "Describe a groove in natural language (e.g., 'urgent 64-bar with crash lifts').\n"
            "Requires OPENAI_API_KEY to call sandboxed tools and return a .mid path.\n"
        )


def repl(stdin = sys.stdin, stdout = sys.stdout) -> int:
    app = TerminalApp()
    print(WELCOME, file=stdout)
    while app.running:
        print("techno> ", end="", file=stdout, flush=True)
        line = stdin.readline()
        if not line:
            break
        reply = app.handle_line(line)
        if reply.output:
            print(reply.output, file=stdout)
        if reply.action == "quit":
            break
    return 0

def _system_prompt() -> str:
    return (
        "You are Techno Assistant, a terminal-only helper for generating techno MIDI via strict tools. "
        "Stay in domain: groove generation, configs, rendering, documentation Q&A (architecture/roadmap/usage). "
        "Use tools only. Never run code/shell or browse. If asked off-domain, refuse politely and suggest a domain action. "
        "When acting, prefer the simplest tool path. Keep replies concise and include resulting file paths. "
        "For documentation questions: do not ask for confirmation; call search_docs with a clear query, then read_doc for the best candidate, and answer concisely using that content."
    )

def _developer_prompt() -> str:
    return (
        "Tools available: render_session, agent_handle, doc_answer, list_docs, read_doc, search_docs, create_config, list_configs, read_config, write_config, list_examples, help_text. "
        "Doc Q&A flow: prefer doc_answer(query) for concise context; optionally follow with read_doc for detail. Avoid asking the user to list docs unless they request it."
    )

def _build_orchestrator() -> Optional[Orchestrator]:
    s = load_settings()
    if not s.openai_api_key:
        return None
    client = OpenAIHTTPClient(api_key=s.openai_api_key, model=s.model)
    return Orchestrator(client, system_prompt=_system_prompt(), developer_prompt=_developer_prompt())

def TerminalApp__get_orchestrator(self) -> Optional[Orchestrator]:
    if self._orch is None:
        self._orch = _build_orchestrator()
    return self._orch

# Bind method to class without changing structure
TerminalApp._get_orchestrator = TerminalApp__get_orchestrator


if __name__ == "__main__":
    raise SystemExit(repl())
