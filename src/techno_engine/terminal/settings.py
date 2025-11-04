from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    openai_api_key: str | None
    model: str = "gpt-4o-mini"


def load_settings() -> Settings:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        env_path = Path(".env")
        if env_path.exists():
            try:
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == "OPENAI_API_KEY" and v.strip():
                            key = v.strip()
                            break
            except Exception:
                pass
    return Settings(openai_api_key=key)
