"""Entry point para Plesk + Phusion Passenger.

Plesk arranca este archivo y busca una variable `application` WSGI.
Flask expone su WSGI app directamente en `app.py`.
"""
import sys
import os

# Asegura que el directorio del proyecto este en el path
BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from app import app as application  # noqa: E402,F401
