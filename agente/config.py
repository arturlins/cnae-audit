"""Configuration read from environment variables at call time (so tests and T06 can override)."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Loads .env once at import; real environment variables take precedence over the file.
load_dotenv(PROJECT_ROOT / ".env", override=False)

DEFAULT_IBGE_BASE_URL = "https://servicodados.ibge.gov.br/api/v2/cnae"
DEFAULT_REGRAS_PATH = PROJECT_ROOT / "data" / "regras_cnae.json"
DEFAULT_GEMINI_MODEL_ID = "gemini-3.7-flash"
DEFAULT_AGENTOS_DB = PROJECT_ROOT / "tmp" / "agentos.db"

AGENT_ID = "verificador-cnae"
TOOL_CALL_LIMIT = 6


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


def gemini_model_id() -> str:
    return os.getenv("GEMINI_MODEL_ID", DEFAULT_GEMINI_MODEL_ID)


def agentos_db_path() -> Path:
    raw = os.getenv("AGENTOS_DB")
    if not raw:
        return DEFAULT_AGENTOS_DB
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def agentos_port() -> int:
    return int(os.getenv("AGENTOS_PORT", "7777"))


def agentos_url() -> str:
    return os.getenv("AGENTOS_URL", f"http://localhost:{agentos_port()}").rstrip("/")


def agentos_timeout_s() -> float:
    return float(os.getenv("AGENTOS_TIMEOUT_S", "90"))


def os_security_key() -> str | None:
    return os.getenv("OS_SECURITY_KEY") or None
