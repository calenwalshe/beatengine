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
    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    if not key or not os.environ.get("OPENAI_MODEL"):
        env_path = Path(".env")
        if env_path.exists():
            try:
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if not key and k == "OPENAI_API_KEY" and v:
                            key = v
                        if not os.environ.get("OPENAI_MODEL") and k == "OPENAI_MODEL" and v:
                            model = v
            except Exception:
                pass
    return Settings(openai_api_key=key, model=model)
