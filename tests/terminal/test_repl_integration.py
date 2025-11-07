from __future__ import annotations

from io import StringIO

from techno_engine.terminal.app import repl, WELCOME


def test_repl_integration_help_and_quit():
    # Simulate a short interactive session: show help, then quit
    input_stream = StringIO(":help\n:quit\n")
    output_stream = StringIO()

    rc = repl(stdin=input_stream, stdout=output_stream)
    out = output_stream.getvalue()

    assert rc == 0
    # Welcome banner printed
    assert WELCOME in out
    # Help text printed
    assert "Commands:" in out
    # Prompt appears at least twice (before :help and before :quit)
    assert out.count("techno> ") >= 2
    # Quit message printed
    assert "Goodbye." in out

