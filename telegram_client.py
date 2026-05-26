"""Cliente minimalista para la Telegram Bot API."""
from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)

API_BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


class TelegramTransientError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    retry=retry_if_exception_type(TelegramTransientError),
    reraise=True,
)
def _post(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{API_BASE}/{method}"
    try:
        resp = requests.post(url, json=payload, timeout=10)
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise TelegramTransientError(str(exc)) from exc

    if resp.status_code in (429, 500, 502, 503, 504):
        raise TelegramTransientError(f"{resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} fallo: {data}")
    return data["result"]


def send_message(chat_id: int | str, text: str, parse_mode: str = "Markdown") -> None:
    """Envia un mensaje. Si falla con parse_mode (texto rompe Markdown), reintenta sin formato."""
    try:
        _post("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        })
    except RuntimeError as exc:
        # Si Markdown falla por caracteres especiales, reenviar como texto plano
        if "parse" in str(exc).lower() or "entity" in str(exc).lower():
            logger.warning("Markdown fallo, reenvio como texto plano: %s", exc)
            _post("sendMessage", {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            })
        else:
            raise


def set_webhook(url: str, secret_token: str) -> dict[str, Any]:
    return _post("setWebhook", {
        "url": url,
        "secret_token": secret_token,
        "allowed_updates": ["message"],
        "drop_pending_updates": True,
    })


def delete_webhook() -> dict[str, Any]:
    return _post("deleteWebhook", {"drop_pending_updates": True})


def get_webhook_info() -> dict[str, Any]:
    resp = requests.get(f"{API_BASE}/getWebhookInfo", timeout=10)
    return resp.json().get("result", {})


def get_me() -> dict[str, Any]:
    resp = requests.get(f"{API_BASE}/getMe", timeout=10)
    return resp.json().get("result", {})
