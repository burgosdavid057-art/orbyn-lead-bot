"""Carga y valida configuracion desde .env."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get(key: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(
            f"Falta la variable de entorno {key}. Copia .env.example a .env y completa."
        )
    return value or ""


class Settings:
    TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN", required=True)
    TELEGRAM_WEBHOOK_SECRET = _get("TELEGRAM_WEBHOOK_SECRET", required=True)

    GROQ_API_KEY = _get("GROQ_API_KEY", required=True)
    GROQ_MODEL = _get("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

    GOOGLE_SHEET_ID = _get("GOOGLE_SHEET_ID", required=True)
    GOOGLE_SHEET_TAB = _get("GOOGLE_SHEET_TAB", "Leads")
    GOOGLE_CREDENTIALS_PATH = _get(
        "GOOGLE_CREDENTIALS_PATH", str(BASE_DIR / "google-credentials.json")
    )

    MAX_LEAD_LENGTH = int(_get("MAX_LEAD_LENGTH", "2000"))
    DEBUG = _get("DEBUG", "false").lower() == "true"


settings = Settings()
