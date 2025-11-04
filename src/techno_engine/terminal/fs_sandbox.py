from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple


def get_base_dirs() -> Tuple[Path, Path]:
    """Return (configs_dir, out_dir) as Paths.

    Allows override via env:
      TECH_ENGINE_CONFIGS_DIR, TECH_ENGINE_OUT_DIR
    Defaults to ./configs and ./out
    """
    cfg = Path(os.environ.get("TECH_ENGINE_CONFIGS_DIR", "configs")).resolve()
    out = Path(os.environ.get("TECH_ENGINE_OUT_DIR", "out")).resolve()
    return cfg, out


def ensure_dirs() -> Tuple[Path, Path]:
    cfg, out = get_base_dirs()
    cfg.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    return cfg, out


def safe_join(base: Path, *parts: str) -> Path:
    """Join parts to base and ensure final path stays within base."""
    path = base.joinpath(*parts).resolve()
    if not str(path).startswith(str(base)):
        raise ValueError("Path traversal detected")
    return path

