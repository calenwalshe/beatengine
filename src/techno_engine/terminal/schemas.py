from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass
class EngineConfigSubset:
    mode: str = "m1"
    bpm: float = 132.0
    ppq: int = 1920
    bars: int = 8

    def validate(self) -> None:
        if self.mode not in {"m1", "m2", "m4"}:
            self.mode = "m1"
        self.bpm = clamp(float(self.bpm), 110.0, 150.0)
        self.ppq = int(self.ppq) if int(self.ppq) > 0 else 1920
        self.bars = max(1, int(self.bars))


@dataclass
class RenderSessionInput:
    config_path: Optional[str] = None
    inline_config: Optional[Dict[str, Any]] = None

    def ensure_valid(self) -> None:
        if not self.config_path and not self.inline_config:
            raise ValueError("must provide config_path or inline_config")


@dataclass
class RenderSessionOutput:
    path: str
    bpm: float
    bars: int
    summary: str
    config: Dict[str, Any] | None = None


@dataclass
class CreateConfigInput:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReadConfigInput:
    name: str


@dataclass
class WriteConfigInput:
    name: str
    body: str


@dataclass
class ListOutput:
    items: list[str]


@dataclass
class HelpInput:
    topic: Optional[str] = None


@dataclass
class HelpOutput:
    usage: str


# Documentation tools

@dataclass
class ListDocsOutput:
    items: list[str]


@dataclass
class ReadDocInput:
    name: str
    start_line: int | None = None  # 1-based
    max_lines: int | None = 200


@dataclass
class ReadDocOutput:
    path: str
    body: str


@dataclass
class SearchDocsInput:
    query: str
    max_results: int | None = 10


@dataclass
class SearchHit:
    path: str
    line: int
    snippet: str


@dataclass
class SearchDocsOutput:
    results: list[SearchHit]


@dataclass
class DocSource:
    path: str
    line: int


@dataclass
class DocAnswerInput:
    query: str
    max_sources: int | None = 2
    context_window: int | None = 10


@dataclass
class DocAnswerOutput:
    summary: str
    sources: list[DocSource]
