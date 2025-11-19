from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class LeadNote:
    bar: int
    step: int
    length: int
    pitch: int


@dataclass
class ValidationResult:
    ok: bool
    reasons: List[str]


def _per_bar_density(notes: List[LeadNote]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for n in notes:
        counts[n.bar] = counts.get(n.bar, 0) + 1
    return counts


def validate_density(notes: List[LeadNote], bounds: Tuple[int, int]) -> ValidationResult:
    """Check that per-bar density is within the given bounds.

    This is deliberately simple for now; it returns a ValidationResult so
    future checks can be combined without changing the signature.
    """

    lo, hi = bounds
    reasons: List[str] = []
    for bar, count in _per_bar_density(notes).items():
        if count < lo:
            reasons.append(f"bar {bar}: too sparse ({count} < {lo})")
        if count > hi:
            reasons.append(f"bar {bar}: too dense ({count} > {hi})")
    return ValidationResult(ok=not reasons, reasons=reasons)


def validate_register(notes: List[LeadNote], lo: int, hi: int) -> ValidationResult:
    reasons: List[str] = []
    for n in notes:
        if n.pitch < lo or n.pitch > hi:
            reasons.append(f"note {n.pitch} out of register [{lo},{hi}]")
    return ValidationResult(ok=not reasons, reasons=reasons)
