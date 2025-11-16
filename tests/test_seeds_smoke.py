from __future__ import annotations


def test_seeds_module_imports() -> None:
    """Smoke test: importing the seeds module should succeed."""
    import techno_engine.seeds  # noqa: F401

