from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    openai_api_key: str | None
    model: str = "gpt-4o-mini"


def load_settings() -> Settings:
    return Settings(openai_api_key=os.environ.get("OPENAI_API_KEY"))

