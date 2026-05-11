"""Runtime configuration for MarketPulse."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_path: Path = Path(os.getenv("MARKETPULSE_DATA", "data/sample_market.csv"))
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    model_name: str = os.getenv("MARKETPULSE_MODEL", "gemini-1.5-flash")


def load_settings() -> Settings:
    return Settings()
