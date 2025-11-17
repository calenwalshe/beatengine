import json
from pathlib import Path

import subprocess
import sys


def _make_minimal_seed(root: Path, seed_id: str = "seed_test_delete") -> Path:
    seeds_root = root / "seeds"
    seed_dir = seeds_root / seed_id
    (seed_dir / "drums").mkdir(parents=True, exist_ok=True)
    (seed_dir / "drums" / "main.mid").write_bytes(b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x00\x60MTrk\x00\x00\x00\x00")

    meta = {
        "seed_id": seed_id,
        "created_at": "2025-01-01T00:00:00Z",
        "engine_mode": "m4",
        "bpm": 130.0,
        "bars": 4,
        "ppq": 1920,
        "rng_seed": 1,
        "config_path": "config.json",
        "render_path": "drums/main.mid",
        "tags": ["test"],
        "summary": "test seed",
        "prompt": "",
        "assets": [
            {
                "role": "main",
                "kind": "midi",
                "path": "drums/main.mid",
                "description": "primary render",
            }
        ],
    }
    (seed_dir / "metadata.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    (seed_dir / "config.json").write_text(json.dumps({"mode": "m4", "bpm": 130.0, "ppq": 1920, "bars": 4, "seed": 1}))
    return seeds_root


def _run_seed_cli(tmp_path: Path, args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
    env = dict(**{k: v for k, v in dict(**dict()).items()})
    env.update({"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})

    cmd = [sys.executable, "-m", "techno_engine.seed_cli"] + args
    return subprocess.run(
        cmd,
        cwd=tmp_path,
        input=input_text.encode() if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def test_seed_cli_delete_yes(tmp_path: Path) -> None:
    seeds_root = _make_minimal_seed(tmp_path)
    seed_id = "seed_test_delete"

    proc = _run_seed_cli(
        tmp_path,
        ["delete", seed_id, "--root", str(seeds_root), "--yes"],
    )
    assert proc.returncode == 0, proc.stdout.decode() + proc.stderr.decode()

    # Seed directory should be gone
    assert not (seeds_root / seed_id).exists()


def test_seed_cli_delete_missing(tmp_path: Path) -> None:
    seeds_root = tmp_path / "seeds"
    seeds_root.mkdir(parents=True, exist_ok=True)

    proc = _run_seed_cli(
        tmp_path,
        ["delete", "does_not_exist", "--root", str(seeds_root), "--yes"],
    )
    assert proc.returncode != 0


def test_seed_cli_delete_prompt_abort(tmp_path: Path) -> None:
    seeds_root = _make_minimal_seed(tmp_path, seed_id="seed_abort")
    seed_id = "seed_abort"

    proc = _run_seed_cli(
        tmp_path,
        ["delete", seed_id, "--root", str(seeds_root)],
        input_text="n\n",
    )
    # Non-zero exit because we aborted
    assert proc.returncode != 0
    # Seed directory should still exist
    assert (seeds_root / seed_id).is_dir()
