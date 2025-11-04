from __future__ import annotations

import sys
from dataclasses import dataclass


WELCOME = "Techno Assistant (terminal) — type :help for commands"


@dataclass
class Reply:
    action: str  # "ok", "quit"
    output: str


class TerminalApp:
    def __init__(self) -> None:
        self.running = True

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
            return Reply("ok", "Techno Assistant — terminal UI for generating techno MIDI via sandboxed tools.")
        # M0: no LLM yet — nudge user to local help
        return Reply("ok", "(M0) No AI connected yet. Try :help or describe what you want (will route to AI in M1).")

    def _help_text(self) -> str:
        return (
            "Commands:\n"
            "  :help          Show this help\n"
            "  :about         About this assistant\n"
            "  :quit          Exit the terminal\n\n"
            "Describe a groove in natural language (e.g., 'urgent 64-bar with crash lifts').\n"
            "In M1+, the assistant will route to sandboxed tools and return a .mid path.\n"
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


if __name__ == "__main__":
    raise SystemExit(repl())

