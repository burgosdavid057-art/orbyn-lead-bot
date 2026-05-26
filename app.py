"""Webhook Flask que recibe updates de Telegram.

Ruta unica: POST /webhook
  - Valida el header X-Telegram-Bot-Api-Secret-Token (anti suplantacion)
  - Extrae el texto del lead del mensaje
  - Llama al clasificador (sincrono: cabe holgado en el timeout de Telegram)
  - Responde al chat con el resultado
  - Loguea en Sheets (best-effort, no rompe la respuesta al usuario)

Procesamiento sincrono porque bajo Phusion Passenger (Plesk) los daemon
threads pueden morir si el worker se recicla. Groq con timeout=20s +
Sheets ~1s + Telegram ~1s entra de sobra en los 60s que Telegram espera.

Respondemos SIEMPRE 200 a Telegram (incluso si nuestra logica fallo)
porque si devolvemos error Telegram reintenta y duplica filas en la Sheet.
"""
from __future__ import annotations

import logging

from flask import Flask, request, jsonify

from config import settings
from qualifier import qualify, format_response_for_user
from sheets_logger import log_lead
from telegram_client import send_message

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

HELP_TEXT = (
    "Hola, soy el bot de cualificacion de leads de Orbyn (demo).\n\n"
    "Envianme los datos de un lead en texto libre. Ejemplo:\n"
    "_Empresa de consultoria de RRHH, 18 empleados, Bogota, quieren automatizar el seguimiento de candidatos._\n\n"
    "Te respondere si encaja con el ICP y registrare el resultado."
)


@app.get("/")
def index():
    return jsonify({"service": "orbyn-lead-bot", "status": "ok"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/webhook")
def webhook():
    # 1. Validacion del secreto: solo Telegram conoce este token
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Webhook con secreto invalido desde %s", request.remote_addr)
        return jsonify({"ok": False, "error": "invalid_secret"}), 403

    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message")
    if not message:
        return jsonify({"ok": True})  # ignoramos updates que no son mensajes

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    user = message.get("from", {})
    user_label = user.get("username") or f"id:{user.get('id')}"
    text = (message.get("text") or "").strip()

    if not chat_id:
        return jsonify({"ok": True})

    # Comandos especiales
    if text in ("/start", "/help"):
        _send_safe(chat_id, HELP_TEXT)
        return jsonify({"ok": True})

    if not text:
        _send_safe(chat_id, "Solo proceso mensajes de texto. Envia los datos del lead en texto libre.")
        return jsonify({"ok": True})

    # Sincrono: cabe en el timeout. Si algo revienta dentro respondemos 200
    # igual a Telegram para evitar reintentos duplicados.
    try:
        result = qualify(text)
        response_text = format_response_for_user(result)
        _send_safe(chat_id, response_text)

        ok = log_lead(text, result, user_label, chat_id)
        if not ok:
            logger.warning("Lead procesado pero no logueado en Sheets (chat_id=%s)", chat_id)
    except Exception:  # noqa: BLE001
        logger.exception("Fallo procesando lead chat_id=%s", chat_id)
        _send_safe(
            chat_id,
            "Hubo un error procesando el lead. Revisa los logs del servidor.",
        )

    return jsonify({"ok": True})


def _send_safe(chat_id: int, text: str) -> None:
    try:
        send_message(chat_id, text)
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo enviar mensaje a chat %s", chat_id)


if __name__ == "__main__":
    # Solo para desarrollo local: en Plesk arranca via passenger_wsgi.py
    app.run(host="0.0.0.0", port=5000, debug=settings.DEBUG)
