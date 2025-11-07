from __future__ import annotations

import os

from techno_engine.terminal.app import TerminalApp


def test_repl_help_and_quit():
    app = TerminalApp()
    # help
    r = app.handle_line(":help")
    assert r.action == "ok"
    assert "Commands" in r.output
    # about
    r = app.handle_line(":about")
    assert r.action == "ok"
    assert "terminal UI" in r.output
    # quit
    r = app.handle_line(":quit")
    assert r.action == "quit"
    assert app.running is False


def test_repl_default_response_no_llm():
    app = TerminalApp()
    r = app.handle_line("make a 32 bar groove with ghost kicks at 128 bpm")
    assert r.action == "ok"
    assert "No AI. Ask Calen for key" in r.output
