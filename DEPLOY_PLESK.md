# Deploy en Plesk (aahost.co)

Guía para correr el bot como aplicación Python en Plesk usando Phusion
Passenger. Telegram requiere un endpoint HTTPS público, y Plesk ya nos da
SSL gratis vía Let's Encrypt — así que no necesitamos ngrok ni Railway.

## Arquitectura sobre Plesk

```
Telegram → HTTPS → davidburgos.dev/orbyn-bot/webhook
                       │
                       ▼
              Nginx (Plesk frontend)
                       │
                       ▼
              Phusion Passenger
                       │
                       ▼
              passenger_wsgi.py → Flask app
```

## 0. Antes de empezar

Confirma que el plan de Plesk de aahost.co soporta:

- **Python ≥ 3.10** (Plesk → tu dominio → Python).
- **Phusion Passenger** habilitado en el dominio (debería estar por defecto).
- SSH activo (`ssh davidburgos` ya configurado según tu memoria).

Si Python no aparece en el panel del dominio, contacta soporte de aahost.co. La mayoría de planes Plesk modernos lo incluyen.

## 1. Decidir dónde montar el bot

Tienes dos opciones razonables:

| Opción | URL | Comentario |
|---|---|---|
| Subdominio | `bot.davidburgos.dev` | Más limpio, requiere DNS y SSL para el subdominio (Plesk lo hace en 1 clic). |
| Subdirectorio | `davidburgos.dev/orbyn-bot/` | Más rápido, pero hay que cuidar que no choque con tu portafolio. |

**Recomendado: subdominio.** Lo explico para subdominio; el subdirectorio es similar pero con un `Location /orbyn-bot/` en Nginx.

## 2. Crear el subdominio

1. Plesk → **Sitios web y dominios** → **Agregar subdominio**.
2. Nombre: `bot`. Dominio padre: `davidburgos.dev`.
3. Document root: déjalo como sugiere (`/bot.davidburgos.dev/httpdocs` o similar).
4. Una vez creado, entra al subdominio → **Certificado SSL/TLS** → instala el de Let's Encrypt (gratis).

## 3. Subir el código

Por SSH:

```bash
ssh davidburgos
cd ~/bot.davidburgos.dev      # ajusta a la ruta real que te dio Plesk
git clone https://github.com/TU_USUARIO/orbyn-lead-bot.git .
# o si no quieres usar git: sube los archivos por SFTP
```

Luego:

```bash
# Copia y completa el .env con tus tokens reales
cp .env.example .env
nano .env

# Sube google-credentials.json por SFTP (NO por git)
chmod 600 .env google-credentials.json
```

## 4. Configurar la aplicación Python en Plesk

1. Plesk → tu subdominio `bot.davidburgos.dev` → **Python** (icono en el panel).
2. Si no hay app, **Habilitar Python**.
3. Configura:
   - **Versión Python**: 3.10 o superior.
   - **Application Root**: la ruta donde subiste el código (ej: `/var/www/vhosts/davidburgos.dev/bot.davidburgos.dev`).
   - **Application URL**: `https://bot.davidburgos.dev/`.
   - **Application Startup File**: `passenger_wsgi.py`.
   - **Application Entry point**: `application` (lo expone nuestro `passenger_wsgi.py`).
4. **Crear**.
5. Plesk crea un virtualenv automáticamente. Botón **Pip install**:
   - Si el panel lo permite, pega `requirements.txt` o pulsa "Install" si detecta el archivo.
   - Alternativa por SSH: `source ~/bot.davidburgos.dev/.venv/bin/activate && pip install -r requirements.txt` (la ruta del venv te la indica Plesk).

## 5. Reiniciar la app

En el panel Python de Plesk hay un botón **Restart App**. Pulsa después de:

- Cualquier cambio en el código
- Cualquier cambio en `.env`
- Cualquier cambio en dependencias

## 6. Verificar que el servidor responde

```bash
curl https://bot.davidburgos.dev/
# Debería responder: {"service":"orbyn-lead-bot","status":"ok"}

curl https://bot.davidburgos.dev/health
# {"status":"ok"}
```

Si ves un error 500 de Plesk: revisa los logs en `Plesk → Logs` o por SSH en `~/logs/`.

## 7. Configurar el webhook de Telegram

Desde tu máquina local (donde tienes el `.env` igual de configurado) o por SSH dentro del servidor:

```bash
python set_webhook.py set https://bot.davidburgos.dev/webhook
python set_webhook.py info
```

Salida esperada del `info`:

```
Bot:
  username: @orbyn_lead_qualifier_bot
  ...
Webhook actual:
  url: https://bot.davidburgos.dev/webhook
  has_custom_certificate: False
  pending_update_count: 0
  ...
```

## 8. Probar end-to-end

Abre Telegram → busca tu bot → mándale `/start` → te responde con el texto de bienvenida.

Manda un lead real:

```
Consultora estratégica en Madrid, 18 empleados, buscan automatizar 
el reporting interno con IA
```

Verifica:
- El bot responde con el análisis del LLM.
- En la Google Sheet aparece una fila nueva.

## Troubleshooting

### El bot no responde

```bash
# Ver logs de Passenger
tail -f ~/logs/error_log
# o
tail -f ~/logs/passenger.log
```

Causas comunes:
- `.env` mal configurado → revisa `python set_webhook.py info`.
- `requirements.txt` no instalado → reentra al panel Python y pulsa Install.
- Forgot to restart app después de cambios.

### `invalid_secret` en logs

El `TELEGRAM_WEBHOOK_SECRET` en `.env` no coincide con el que registraste al hacer `set_webhook`. Vuelve a ejecutar `python set_webhook.py set ...` desde el servidor (o asegúrate de usar el mismo .env local).

### `403 Forbidden` al consultar la Sheet

El service account no tiene permiso. Vuelve al paso 5 de `SETUP_GOOGLE_SHEETS.md` y comparte la hoja con el email del service account.

### Webhook dice `last_error_message: SSL error`

Plesk no terminó de instalar el certificado Let's Encrypt. Renueva manualmente desde el panel.

### Passenger no encuentra Flask

```bash
source <venv_path>/bin/activate
pip install -r requirements.txt
# Luego en Plesk: Restart App
```
