"""Lead-line generation package for Beatengine.

This package implements a rhythm-aware, style-aware lead generator
that builds on the drum slot grid and seed metadata. See
`docs/LEAD_GENERATOR_ROADMAP.md` for the high-level design.
"""

from .lead_engine import generate_lead  # noqa: F401
