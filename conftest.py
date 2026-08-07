"""Configuracion compartida de pytest para orbyn-lead-bot.

`config.py` exige varias variables de entorno al importarse (falla en caliente
si faltan). Aqui las poblamos con valores ficticios ANTES de que cualquier test
importe `qualifier`/`config`, para que la suite corra sin un `.env` real y sin
tocar ninguna API (Groq, Telegram o Sheets se mockean o no se llaman).
"""

from __future__ import annotations

import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("GOOGLE_SHEET_ID", "test-sheet-id")
os.environ.setdefault("MAX_LEAD_LENGTH", "2000")
