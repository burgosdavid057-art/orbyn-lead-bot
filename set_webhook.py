"""Configura o consulta el webhook de Telegram.

Uso:
  python set_webhook.py info
  python set_webhook.py set https://tu-dominio.com/webhook
  python set_webhook.py delete
"""
import sys

from config import settings
from telegram_client import set_webhook, delete_webhook, get_webhook_info, get_me


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "info":
        me = get_me()
        info = get_webhook_info()
        print("Bot:")
        print(f"  username: @{me.get('username')}")
        print(f"  id:       {me.get('id')}")
        print(f"  name:     {me.get('first_name')}")
        print("Webhook actual:")
        for k, v in info.items():
            print(f"  {k}: {v}")
        return

    if cmd == "set":
        if len(sys.argv) < 3:
            print("Falta la URL. Ejemplo: python set_webhook.py set https://davidburgos.dev/orbyn-bot/webhook")
            sys.exit(1)
        url = sys.argv[2]
        result = set_webhook(url, settings.TELEGRAM_WEBHOOK_SECRET)
        print(f"Webhook configurado en: {url}")
        print(f"Respuesta Telegram: {result}")
        return

    if cmd == "delete":
        result = delete_webhook()
        print(f"Webhook eliminado: {result}")
        return

    print(f"Comando desconocido: {cmd}")
    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    main()
