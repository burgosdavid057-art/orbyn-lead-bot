# Cómo entregar a Orbyn

Lista de comprobación antes de mandar el email a `sales@orbyn.ai`.

## Antes del envío

- [ ] Bot creado en @BotFather y `username` anotado.
- [ ] `.env` completo en el servidor con tokens reales.
- [ ] `google-credentials.json` subido al servidor.
- [ ] Hoja de Google Sheets compartida con el service account.
- [ ] App desplegada en `https://bot.davidburgos.dev/` (o donde la pongas).
- [ ] `curl https://bot.davidburgos.dev/` devuelve `{"service":"orbyn-lead-bot","status":"ok"}`.
- [ ] `python set_webhook.py info` muestra el webhook configurado y `pending_update_count: 0`.
- [ ] Probado con al menos 3 leads diferentes (1 cualificado, 1 no, 1 borderline).
- [ ] Verificado que las filas aparecen en la Google Sheet.
- [ ] Hoja de Google Sheets compartida en modo "Cualquiera con el enlace puede ver" para que Orbyn pueda revisarla (¡NO Editor!).
- [ ] Repo en GitHub subido y público (o privado pero con acceso al evaluador).
- [ ] Video de 1 minuto grabado y subido a Loom/YouTube unlisted/Drive.

## Plantilla de email

> Asunto: Prueba técnica — Bot de cualificación de leads — David Burgos

Hola equipo de Orbyn,

Adjunto la entrega de la prueba técnica del agente de cualificación de leads:

- **Bot de Telegram**: `@orbyn_lead_qualifier_bot` (sustituir por el username real)
- **Repositorio**: https://github.com/TU_USUARIO/orbyn-lead-bot
- **Video de 1 minuto**: https://loom.com/share/XXXX (sustituir)
- **Google Sheet de prueba** (modo lectura): https://docs.google.com/spreadsheets/d/SHEET_ID

Para probarlo basta con escribirle un texto libre con datos de un lead. Algunos ejemplos:

- _"Consultora de marketing en Madrid, 20 personas, quieren automatizar el reporting"_ → debería responder CUALIFICADO.
- _"Tienda de ropa online en Bogotá, 8 empleados"_ → NO CUALIFICADO (ecommerce, no muestra interés en IA).
- _"Consultora boutique en Berlín, 12 personas, quieren un chatbot"_ → NO CUALIFICADO (fuera de España/LatAm).

**3 cosas que cambiaría en producción**:

1. **Robustez y observabilidad end-to-end.** Hoy el bot reintenta con backoff en Groq/Telegram, responde 200 inmediato para evitar duplicados, y deja logs en stdout; en producción metería idempotencia explícita por `update_id` de Telegram en Redis, una cola (SQS/RabbitMQ) entre webhook y worker para sobrevivir picos, y tracing con Sentry + métricas de latencia, tokens y tasa de cualificación en Grafana — porque sin esto operas a ciegas y un lead perdido no se entera nadie.

2. **Defensa en profundidad contra prompt injection y abuso.** El prompt ya delimita la entrada con `<<<LEAD>>>` y fuerza coherencia entre los checks individuales y la decisión final (si algún criterio es false, anulo el qualified=true aunque el LLM se lo invente); en producción añadiría rate-limiting por chat_id, validación estricta del JSON de salida con Pydantic, un clasificador previo barato para descartar inputs no-lead antes de pagar tokens del modelo grande, y secretos en vault con rotación automática.

3. **Control de costes y SLAs del LLM.** Groq gratuito es perfecto para la demo, pero en producción no puedes depender de un único proveedor: pondría caché por hash del texto del lead (muchos llegan duplicados), fallback a un segundo modelo si Groq da 429 sostenido, presupuesto mensual con alertas y kill-switch automático, y A/B periódico entre Llama 3.3, Gemini Flash y GPT-4o-mini midiendo precisión contra leads etiquetados — porque el modelo más barato hoy no es el mejor mañana.

Cualquier duda quedo atento. Gracias por la oportunidad.

Un saludo,

David Burgos
[teléfono / linkedin]
