"""Beatengine lead_v2 package.

This package contains the theory-aware lead generator implementation.
The code here is scaffolded to align with the Lead Generator v2 roadmap.
Concrete algorithmic details should be filled in by a coding agent.
"""

from .theory import KeySpec, HarmonyTrack, LeadNoteLogical, LeadNoteEvent
from .generate import generate_lead_v2
