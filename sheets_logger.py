"""Logger que escribe cada lead procesado en una Google Sheet.

Usa un Service Account: no requiere OAuth de usuario y es lo correcto para
backend. Si por cualquier razon falla, el flujo principal NO debe romperse:
es mejor responder al usuario aunque no logueemos, y registrar el fallo
en logs del servidor.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from config import settings
from qualifier import QualificationResult

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER = [
    "timestamp_utc",
    "telegram_user",
    "telegram_chat_id",
    "lead_text",
    "qualified",
    "confidence",
    "reasoning",
    "company_type",
    "employees_estimate",
    "country_or_region",
    "country_detail",
    "automation_interest",
    "is_services_or_consulting",
    "has_min_5_employees",
    "is_spain_or_latam",
    "shows_automation_interest",
    "suspicious_input",
    "error",
]


@lru_cache(maxsize=1)
def _get_worksheet() -> gspread.Worksheet:
    creds = Credentials.from_service_account_file(
        settings.GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(settings.GOOGLE_SHEET_ID)
    try:
        ws = sheet.worksheet(settings.GOOGLE_SHEET_TAB)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=settings.GOOGLE_SHEET_TAB, rows=1000, cols=len(HEADER))
        ws.append_row(HEADER, value_input_option="RAW")
        return ws

    # Asegura encabezado si la pestania estaba vacia
    first_row = ws.row_values(1)
    if first_row != HEADER:
        if not first_row:
            ws.append_row(HEADER, value_input_option="RAW")
        else:
            logger.warning(
                "Encabezado existente difiere del esperado. Mantengo el existente."
            )
    return ws


def log_lead(
    lead_text: str,
    result: QualificationResult,
    telegram_user: str,
    telegram_chat_id: int | str,
) -> bool:
    """Devuelve True si logueo, False si fallo. Nunca lanza."""
    try:
        ws = _get_worksheet()
        ext = result.extracted or {}
        checks = result.criteria_checks or {}
        row = [
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            telegram_user,
            str(telegram_chat_id),
            lead_text[:1000],  # corta para que la celda no se vuelva enorme
            "SI" if result.qualified else "NO",
            result.confidence,
            result.reasoning,
            str(ext.get("company_type", "")),
            str(ext.get("employee_count_estimate", "")),
            str(ext.get("country_or_region", "")),
            str(ext.get("country_detail", "")),
            str(ext.get("automation_or_ai_interest", "")),
            "SI" if checks.get("is_services_or_consulting") else "NO",
            "SI" if checks.get("has_min_5_employees") else "NO",
            "SI" if checks.get("is_spain_or_latam") else "NO",
            "SI" if checks.get("shows_automation_interest") else "NO",
            "SI" if result.suspicious_input else "NO",
            result.error or "",
        ]
        ws.append_row(row, value_input_option="RAW")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Fallo escribiendo en Google Sheets")
        return False


def healthcheck() -> dict[str, Any]:
    """Para depurar conexion con Sheets desde un script."""
    try:
        ws = _get_worksheet()
        return {
            "ok": True,
            "sheet_title": ws.spreadsheet.title,
            "tab": ws.title,
            "rows": ws.row_count,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
