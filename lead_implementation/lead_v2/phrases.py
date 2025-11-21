from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from random import Random


@dataclass
class PhraseConfig:
    min_bars: int
    max_bars: int
    call_response_pattern: str
    phrase_forms: List[str]
    phrase_end_resolution_degrees: List[int]


@dataclass
class PhraseSegment:
    phrase_id: int
    bar_indices: List[int]
    role: str  # 'CALL' | 'RESP'
    form_label: str  # e.g. 'A', 'A'', 'B'
    is_terminal: bool = False
    resolution_degrees: List[int] = field(default_factory=list)


@dataclass
class PhrasePlan:
    segments: List[PhraseSegment] = field(default_factory=list)


def plan_phrases(num_bars: int, cfg: PhraseConfig, rng: Optional[Random]) -> PhrasePlan:
    """Plan phrases over num_bars according to PhraseConfig.

    Behaviour:
    - Sample phrase lengths within [min_bars, max_bars].
    - Align lengths to multiples of the call/response pattern for stability.
    - Assign per-bar roles, form labels, and mark resolution bars.
    """
    if rng is None:
        rng = Random(0)

    segments: List[PhraseSegment] = []
    pattern = (cfg.call_response_pattern or "CR").upper()
    if not pattern:
        pattern = "CR"
    pattern_len = max(1, len(pattern))

    min_bars = max(1, cfg.min_bars)
    max_bars = max(min_bars, cfg.max_bars)

    bar = 0
    phrase_id = 0
    form_labels = cfg.phrase_forms or ["A"]

    while bar < num_bars:
        if min_bars == max_bars:
            target_len = min_bars
        else:
            target_len = rng.randint(min_bars, max_bars)
        if target_len % pattern_len != 0:
            target_len = ((target_len // pattern_len) + 1) * pattern_len
        phrase_len = min(target_len, num_bars - bar)
        if phrase_len <= 0:
            break

        form_label = form_labels[min(phrase_id, len(form_labels) - 1)]

        for offset in range(phrase_len):
            role_char = pattern[offset % pattern_len]
            role = "CALL" if role_char == "C" else "RESP"
            global_bar = bar + offset
            is_terminal = offset == phrase_len - 1
            segments.append(
                PhraseSegment(
                    phrase_id=phrase_id,
                    bar_indices=[global_bar],
                    role=role,
                    form_label=form_label,
                    is_terminal=is_terminal,
                    resolution_degrees=cfg.phrase_end_resolution_degrees if is_terminal else [],
                )
            )

        bar += phrase_len
        phrase_id += 1

    return PhrasePlan(segments=segments)
