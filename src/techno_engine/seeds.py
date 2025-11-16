"""Seed-beats support: metadata model and save/load helpers.

This module underpins the "seed beat" feature by providing:
- A `SeedMetadata` dataclass capturing config, prompt, and file metadata.
- `save_seed` to persist the exact config and metadata into a seeds/ tree.
- `load_seed` to restore an `EngineConfig` + `SeedMetadata` by seed_id.

Higher-level CLIs and a TUI explorer will build on top of this.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import EngineConfig, load_engine_config


@dataclass
class SeedMetadata:
    """Metadata describing a single seed beat.

    This is intentionally TUI/CLI-friendly: most fields are simple scalars
    or small lists, and the JSON encoding is stable for future tooling.
    """

    seed_id: str
    created_at: str
    engine_mode: str
    bpm: float
    bars: int
    ppq: int
    rng_seed: int
    config_path: str
    render_path: str
    log_path: Optional[str] = None

    prompt: Optional[str] = None
    prompt_context: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    parent_seed_id: Optional[str] = None
    file_version: int = 1


def seeds_module_version() -> str:
    """Return a placeholder version string for smoke tests and demos."""

    return "0.2-seeds-metadata"


def _default_seeds_root() -> Path:
    return Path("seeds")


def _ensure_seeds_root(seeds_root: Path) -> None:
    seeds_root.mkdir(parents=True, exist_ok=True)


def _generate_seed_id(config: EngineConfig) -> str:
    """Generate a human-ish seed identifier.

    Uses UTC timestamp plus mode and RNG seed to avoid collisions and
    give a rough hint about the origin of the beat.
    """

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    mode = str(config.mode).lower()
    return f"{now}_{mode}_{int(config.seed)}"


def _index_path(seeds_root: Path) -> Path:
    return seeds_root / "index.json"


def _load_index(seeds_root: Path) -> list[SeedMetadata] | None:
    idx_path = _index_path(seeds_root)
    if not idx_path.is_file():
        return None
    try:
        raw = json.loads(idx_path.read_text())
    except Exception:
        return None
    metas: list[SeedMetadata] = []
    for entry in raw:
        try:
            metas.append(SeedMetadata(**entry))
        except Exception:
            continue
    return metas


def rebuild_index(seeds_root: str | Path | None = None) -> list[SeedMetadata]:
    """Rebuild index.json under the given seeds root.

    Scans all seed directories, reads metadata.json, writes a compact index,
    and returns the loaded SeedMetadata list.
    """

    root = Path(seeds_root) if seeds_root is not None else _default_seeds_root()
    _ensure_seeds_root(root)

    metas: list[SeedMetadata] = []
    for seed_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        meta_path = seed_dir / "metadata.json"
        if not meta_path.is_file():
            continue
        try:
            data = json.loads(meta_path.read_text())
            metas.append(SeedMetadata(**data))
        except Exception:
            continue

    idx_path = _index_path(root)
    idx_path.write_text(json.dumps([asdict(m) for m in metas], indent=2, sort_keys=True))
    return metas


def update_index(meta: SeedMetadata, seeds_root: str | Path | None = None) -> None:
    """Update or create index.json entry for a single seed."""

    root = Path(seeds_root) if seeds_root is not None else _default_seeds_root()
    _ensure_seeds_root(root)

    existing = _load_index(root) or []
    by_id = {m.seed_id: m for m in existing}
    by_id[meta.seed_id] = meta
    metas = list(by_id.values())

    idx_path = _index_path(root)
    idx_path.write_text(json.dumps([asdict(m) for m in metas], indent=2, sort_keys=True))


def save_seed(
    config: EngineConfig,
    config_path: str,
    render_path: str,
    *,
    prompt: str | None = None,
    summary: str | None = None,
    tags: List[str] | None = None,
    log_path: str | None = None,
    prompt_context: Dict[str, Any] | None = None,
    seeds_root: str | Path | None = None,
    parent_seed_id: str | None = None,
) -> SeedMetadata:
    """Persist a seed's config and metadata under the seeds/ tree.

    Parameters
    ----------
    config:
        The `EngineConfig` used to render the beat.
    config_path:
        Path to the JSON config file that produced `config`. This exact
        JSON is copied into the seed folder to enable perfect replay.
    render_path:
        Path to the rendered MIDI file. We record it but do not move it.
    prompt / summary / tags / prompt_context:
        Optional metadata describing the prompt and high-level intent.
    seeds_root:
        Base directory for seeds. Defaults to `seeds/` under the CWD.
    parent_seed_id:
        Optional parent identifier for future lineage tracking.
    """

    root = Path(seeds_root) if seeds_root is not None else _default_seeds_root()
    _ensure_seeds_root(root)

    seed_id = _generate_seed_id(config)
    seed_dir = root / seed_id
    seed_dir.mkdir(parents=True, exist_ok=False)

    # Copy the original config JSON into the seed folder.
    src_cfg_path = Path(config_path)
    if not src_cfg_path.is_file():
        raise FileNotFoundError(f"Config path does not exist: {config_path}")
    raw_cfg = json.loads(src_cfg_path.read_text())

    dest_cfg_path = seed_dir / "config.json"
    dest_cfg_path.write_text(json.dumps(raw_cfg, indent=2, sort_keys=True))

    created_at = datetime.now(timezone.utc).isoformat()

    meta = SeedMetadata(
        seed_id=seed_id,
        created_at=created_at,
        engine_mode=str(config.mode).lower(),
        bpm=float(config.bpm),
        bars=int(config.bars),
        ppq=int(config.ppq),
        rng_seed=int(config.seed),
        config_path=str(dest_cfg_path.name),
        render_path=render_path,
        log_path=log_path,
        prompt=prompt,
        prompt_context=prompt_context,
        summary=summary,
        tags=list(tags) if tags is not None else [],
        parent_seed_id=parent_seed_id,
        file_version=1,
    )

    meta_path = seed_dir / "metadata.json"
    meta_path.write_text(json.dumps(asdict(meta), indent=2, sort_keys=True))

    # Keep index in sync for fast listing / TUI use.
    update_index(meta, seeds_root=root)

    return meta


def load_seed(
    seed_id: str,
    *,
    seeds_root: str | Path | None = None,
) -> Tuple[EngineConfig, SeedMetadata]:
    """Load an `EngineConfig` and `SeedMetadata` for a stored seed.

    This expects the layout created by `save_seed`:

    - `<seeds_root>/<seed_id>/config.json`
    - `<seeds_root>/<seed_id>/metadata.json`
    """

    root = Path(seeds_root) if seeds_root is not None else _default_seeds_root()
    seed_dir = root / seed_id

    meta_path = seed_dir / "metadata.json"
    cfg_path = seed_dir / "config.json"

    if not meta_path.is_file():
        raise FileNotFoundError(f"Missing metadata for seed_id={seed_id}: {meta_path}")
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Missing config for seed_id={seed_id}: {cfg_path}")

    meta_raw = json.loads(meta_path.read_text())
    metadata = SeedMetadata(**meta_raw)

    config = load_engine_config(str(cfg_path))
    return config, metadata


def import_config_outputs(
    config_dir: str | Path = "configs",
    seeds_root: str | Path | None = None,
) -> list[SeedMetadata]:
    """Import seeds for configs that declare an out path and have a rendered MIDI.

    This is a one-shot helper for pulling legacy demo renders (m0/m2/m3/m4,
    bass_mvp, etc.) into the seed index so the explorer can see them.
    """

    cfg_root = Path(config_dir)
    metas: list[SeedMetadata] = []

    for cfg_path in sorted(cfg_root.glob("*.json")):
        try:
            raw = json.loads(cfg_path.read_text())
        except Exception:
            continue
        out_rel = raw.get("out")
        if not out_rel:
            continue
        out_path = Path(out_rel)
        if not out_path.is_absolute():
            out_path = Path.cwd() / out_path
        if not out_path.is_file():
            continue

        cfg = load_engine_config(str(cfg_path))
        mode = str(raw.get("mode", cfg.mode)).lower()
        tags = [mode, "legacy_import"]
        summary = f"Imported legacy beat from {cfg_path.name}"

        meta = save_seed(
            cfg,
            config_path=str(cfg_path),
            render_path=str(raw.get("out", cfg.out)),
            summary=summary,
            tags=tags,
            seeds_root=seeds_root,
        )
        metas.append(meta)

    return metas

def import_mid_as_seed(
    midi_path: str | Path,
    *,
    mode: str = "external",
    bpm: float = 0.0,
    bars: int = 0,
    ppq: int = 1920,
    prompt: str | None = None,
    summary: str | None = None,
    tags: List[str] | None = None,
    seeds_root: str | Path | None = None,
) -> SeedMetadata:
    """Import an arbitrary MIDI file as a seed.

    This creates a minimal EngineConfig that points at the given MIDI path and
    writes a private config JSON alongside the seed metadata so the explorer
    can surface the file. It is primarily intended for legacy or external
    renders where the original config is not tracked.
    """

    midi = Path(midi_path)
    if not midi.is_file():
        raise FileNotFoundError(f"MIDI path does not exist: {midi}")

    root = Path(seeds_root) if seeds_root is not None else _default_seeds_root()
    _ensure_seeds_root(root)

    # Minimal config just to satisfy EngineConfig/seed machinery.
    cfg = EngineConfig(
        mode=mode,
        bpm=float(bpm),
        ppq=int(ppq),
        bars=int(bars),
        seed=0,
        out=str(midi),
    )

    # Write a small config JSON that records the origin MIDI path.
    tmp_cfg = root / "_import_mid_config.json"
    raw_cfg: Dict[str, Any] = {
        "mode": mode,
        "bpm": bpm,
        "ppq": ppq,
        "bars": bars,
        "seed": 0,
        "out": str(midi),
        "origin_mid_path": str(midi),
    }
    tmp_cfg.write_text(json.dumps(raw_cfg, indent=2, sort_keys=True))

    try:
        meta = save_seed(
            cfg,
            config_path=str(tmp_cfg),
            render_path=str(midi),
            prompt=prompt,
            summary=summary,
            tags=tags,
            seeds_root=root,
        )
    finally:
        try:
            tmp_cfg.unlink()
        except OSError:
            pass

    return meta
