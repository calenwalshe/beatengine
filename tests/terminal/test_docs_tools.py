from __future__ import annotations

from techno_engine.terminal import tools
from techno_engine.terminal.schemas import ReadDocInput, SearchDocsInput, DocAnswerInput


def test_list_and_read_docs():
    items = tools.list_docs().items
    assert "README.md" in items
    out = tools.read_doc(ReadDocInput(name="docs/ARCHITECTURE.md", start_line=1, max_lines=10))
    assert out.path.endswith("docs/ARCHITECTURE.md")
    assert len(out.body) > 0


def test_search_docs_finds_engine():
    res = tools.search_docs(SearchDocsInput(query="Techno Rhythm Engine", max_results=5))
    assert res.results
    assert any("README.md" in r.path or "ARCHITECTURE.md" in r.path for r in res.results)


def test_doc_answer_returns_summary():
    out = tools.doc_answer(DocAnswerInput(query="architecture"))
    assert out.summary
    assert out.sources
