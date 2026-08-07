# Orbyn Lead Qualifier Bot

[![CI](https://github.com/burgosdavid057-art/orbyn-lead-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/burgosdavid057-art/orbyn-lead-bot/actions/workflows/ci.yml)

Bot de Telegram que recibe leads en texto libre, los cualifica contra el ICP
de Orbyn usando un LLM (Llama 3.3 70B vía Groq, gratis) y registra cada
decisión en una Google Sheet.

> Prueba técnica para Orbyn — David Burgos.

## ¿Cómo funciona?

```
Usuario en Telegram
        │
        │ texto libre con datos del lead
        ▼
┌────────────────────────┐
│  Flask webhook (/webhook)
│  - valida secret_token
│  - lanza worker en thread
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐        ┌─────────────────────────┐
│  qualifier.py          │───────▶│  Groq API (Llama 3.3)   │
│  - sanea entrada       │        │  response_format=json   │
│  - prompt anti-inject  │◀───────│  JSON estructurado      │
│  - valida coherencia   │        └─────────────────────────┘
└────────┬───────────────┘
         │
         ├─────────────▶ Telegram sendMessage (Markdown)
         │
         └─────────────▶ Google Sheets (gspread + service account)
```

## ICP que evalúa

Un lead se considera **cualificado** si cumple los 4 criterios a la vez:

1. **Sector**: empresa de servicios o consultoría (no SaaS, no ecommerce, no producto puro).
2. **Tamaño**: mínimo 5 empleados.
3. **Geografía**: España o Latinoamérica.
4. **Interés**: muestra interés explícito o implícito en automatización o IA.

El LLM extrae cada señal por separado, evalúa cada criterio y devuelve un JSON
con la decisión y el razonamiento. Si los 4 checks no son `true`, el
qualifier fuerza `qualified=false` aunque el LLM lo haya dicho — defensa
contra alucinación.

## Estructura

```
orbyn-lead-bot/
├── app.py                  # Flask webhook
├── qualifier.py            # Lógica LLM + prompt ICP
├── telegram_client.py      # Cliente Telegram Bot API
├── sheets_logger.py        # Logging a Google Sheets
├── config.py               # Carga .env
├── passenger_wsgi.py       # Entry point Plesk
├── set_webhook.py          # Configurar webhook
├── test_local.py           # Probar sin Telegram
├── requirements.txt
├── .env.example
├── SETUP_GOOGLE_SHEETS.md  # Guía paso a paso Service Account
├── DEPLOY_PLESK.md         # Guía deploy en Plesk
└── PRODUCTION_NOTES.md     # Las 3 frases de mejoras para producción
```

## Setup local (5 minutos)

### 1. Clonar e instalar

```bash
git clone <repo>
cd orbyn-lead-bot
python -m venv venv
# Windows: venv\Scripts\activate    Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Crear el bot de Telegram

1. Abre Telegram y habla con [@BotFather](https://t.me/BotFather).
2. `/newbot` → dale un nombre (ej: `Orbyn Lead Qualifier`) y un username terminado en `bot` (ej: `orbyn_lead_qualifier_bot`).
3. Copia el **token** que te da (formato `123456:ABC-xyz...`) en `.env` como `TELEGRAM_BOT_TOKEN`.
4. Inventa una cadena aleatoria larga (32+ caracteres) y ponla en `TELEGRAM_WEBHOOK_SECRET`. Telegram la enviará en cada webhook para que valides origen.

### 3. Conseguir la API key de Groq (gratis, sin tarjeta)

1. Ve a [console.groq.com/keys](https://console.groq.com/keys).
2. Login con Google.
3. Crea una API key → cópiala en `.env` como `GROQ_API_KEY`.

Groq da rate limits muy generosos en el tier gratuito (30 req/min, 14.400 req/día con `llama-3.3-70b-versatile`).

### 4. Configurar Google Sheets

Sigue [SETUP_GOOGLE_SHEETS.md](SETUP_GOOGLE_SHEETS.md) paso a paso. Resumen:

1. Crea un proyecto en Google Cloud.
2. Activa la Google Sheets API y Google Drive API.
3. Crea un Service Account, descarga el JSON, renómbralo a `google-credentials.json` y déjalo en la raíz del proyecto.
4. Crea una Google Sheet, comparte la hoja con el email del service account (permiso Editor).
5. Copia el ID de la hoja en `.env` como `GOOGLE_SHEET_ID`.

### 5. Probar sin Telegram

```bash
# Verifica conexión con Sheets
python test_local.py sheets-health

# Prueba un lead concreto
python test_local.py qualify "Consultora de marketing en Madrid, 20 empleados, quieren un chatbot con IA"

# Batería de leads (cualifica/no cualifica/sospechosos)
python test_local.py demo
```

### 6. Arrancar el webhook

**Opción A — Plesk** (lo que vamos a usar en producción): ver [DEPLOY_PLESK.md](DEPLOY_PLESK.md).

**Opción B — Local con ngrok** (para grabar el video rápido):

```bash
# Terminal 1
python app.py

# Terminal 2
ngrok http 5000
# Copia la URL https://xxxx.ngrok-free.app

# Terminal 3 — configura webhook en Telegram
python set_webhook.py set https://xxxx.ngrok-free.app/webhook
python set_webhook.py info   # verifica
```

Ahora escribe al bot por Telegram. Debería responder con el análisis.

## Probar el bot

Abre Telegram, busca el username del bot y manda:

```
Consultora estratégica en Madrid, 18 empleados, buscan automatizar 
el reporting interno con IA
```

Respuesta esperada:

```
[CUALIFICADO]
Confianza: alta

La empresa es una consultoría estratégica (servicios), con 18 empleados, 
ubicada en Madrid (España), e indica interés explícito en automatización 
con IA. Cumple los 4 criterios del ICP.

Criterios:
  OK - Servicios/consultoría
  OK - Mínimo 5 empleados
  OK - España o LatAm
  OK - Interés en automatización/IA
```

Y aparece una fila nueva en la Google Sheet con timestamp, datos extraídos, decisión y razonamiento.

## Tests automáticos

Además del `test_local.py` (que llama a Groq/Sheets de verdad), hay una suite de
tests unitarios que corre **sin red ni credenciales**: mockea la llamada a Groq
y cubre la lógica que sostiene la calidad del bot — la defensa anti-alucinación
(forzar `qualified=false` si algún criterio falla), el parseo defensivo de la
respuesta del LLM, el truncado de entradas largas y el formateo del mensaje.

```bash
pip install -r requirements-dev.txt
pytest
```

Corre en CI (GitHub Actions) contra Python 3.11, 3.12 y 3.13. Ver
[CONTRIBUTING.md](CONTRIBUTING.md).

## Decisiones técnicas notables

- **Prompt anti-inyección**: el lead va dentro de `<<<LEAD>>> ... <<<END_LEAD>>>` y el system prompt instruye explícitamente a tratar el contenido como dato, no como instrucción. Si detecta patrones sospechosos lo marca en `suspicious_input`.
- **Validación cruzada**: si el LLM dice `qualified=true` pero algún check individual es `false`, forzamos `qualified=false`. Defensa contra alucinación o jailbreaks.
- **Idempotencia parcial**: respondemos 200 a Telegram inmediatamente y procesamos en background. Telegram no reintenta y no duplicamos en la hoja.
- **Retry exponencial**: tanto Groq como Telegram tienen `tenacity` con backoff para errores 429/5xx.
- **Fail-soft en Sheets**: si Sheets cae, el usuario igual recibe respuesta. El error queda en logs del servidor.
- **Truncado de entrada**: máximo 2000 chars (configurable). Evita abuso de tokens.

Para más detalle sobre limitaciones y qué cambiaría en producción, ver [PRODUCTION_NOTES.md](PRODUCTION_NOTES.md).

## Entregables Orbyn

- Bot: ver username en la respuesta del email.
- Código: este repositorio.
- Video: enlace en el email.
- 3 frases sobre producción: [PRODUCTION_NOTES.md](PRODUCTION_NOTES.md).
