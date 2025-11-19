from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class PhraseRole:
    bar_index: int
    role: str  # CALL, CALL_VAR, RESP, RESP_VAR


def build_phrase_roles(phrase_length_bars: int, total_bars: int) -> List[PhraseRole]:
    """Assign phrase roles (CALL / variants / RESP) across bars.

    For now this is a simple deterministic mapping based on the spec:

    - If phrase length is 2 bars: [CALL, CALL_VAR] repeating.
    - If phrase length is 4 bars: [CALL, CALL_VAR, RESP, RESP_VAR] repeating.
    - If total_bars is not a multiple of phrase_length_bars, the pattern
      wraps as needed.
    """

    if phrase_length_bars <= 0:
        phrase_length_bars = 2

    if phrase_length_bars == 2:
        pattern = ["CALL", "CALL_VAR"]
    else:
        pattern = ["CALL", "CALL_VAR", "RESP", "RESP_VAR"]

    roles: List[PhraseRole] = []
    for bar in range(total_bars):
        idx = bar % len(pattern)
        roles.append(PhraseRole(bar_index=bar, role=pattern[idx]))
    return roles
