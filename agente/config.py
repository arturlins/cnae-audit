"""Configuration read from environment variables at call time (so tests and T06 can override)."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_IBGE_BASE_URL = "https://servicodados.ibge.gov.br/api/v2/cnae"
DEFAULT_REGRAS_PATH = PROJECT_ROOT / "data" / "regras_cnae.json"


def ibge_base_url() -> str:
    return os.getenv("IBGE_BASE_URL", DEFAULT_IBGE_BASE_URL).rstrip("/")


def ibge_timeout_s() -> float:
    return float(os.getenv("IBGE_TIMEOUT_S", "5"))


def regras_path() -> Path:
    raw = os.getenv("REGRAS_PATH")
    if not raw:
        return DEFAULT_REGRAS_PATH
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path
