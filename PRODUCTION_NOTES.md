# 3 cosas que cambiaría si esto fuera a producción

Las 3 frases pedidas por Orbyn — versión corta. Debajo está el detalle de
qué del MVP actual ya mitiga cada riesgo y qué falta para producción real.

---

**1. Robustez y observabilidad end-to-end.** Hoy el bot reintenta con backoff
en Groq y Telegram, responde 200 inmediato para evitar duplicados, y deja
logs en stdout; en producción metería idempotencia explícita por `update_id`
de Telegram en Redis, una cola (SQS/RabbitMQ) entre webhook y worker para
sobrevivir picos, y tracing distribuido con Sentry + métricas de latencia,
tokens y tasa de cualificación en Grafana — porque sin esto operas a ciegas
y un lead perdido nunca se entera nadie.

**2. Defensa en profundidad contra prompt injection y abuso.** El prompt ya
delimita la entrada con `<<<LEAD>>>` y fuerza coherencia entre los checks y
la decisión final (si algún criterio individual es `false`, anulo el
`qualified=true` aunque el LLM se lo invente); en producción añadiría
rate-limiting por `chat_id`, un guardrail de salida que valide el JSON
contra un schema estricto (Pydantic) y rechace si trae campos extra, un
clasificador previo barato para descartar inputs ofensivos o no-leads
antes de pagar tokens del modelo grande, y rotación de la API key y del
`webhook_secret` automatizada vía vault — en lugar de un `.env` en disco
del servidor.

**3. Control de costes y SLAs del LLM.** Groq gratuito es perfecto para la
demo, pero en producción no puedes depender de un único proveedor: pondría
caché por hash del texto del lead (muchos leads llegan duplicados),
fallback a un segundo modelo si Groq da 429/5xx sostenido, presupuesto
mensual con alertas y kill-switch automático, y un experimento A/B
periódico entre Llama 3.3 70B, Gemini Flash y GPT-4o-mini midiendo
precisión real contra leads etiquetados por humanos — porque el modelo más
barato hoy no es el mejor mañana y la deriva en calidad solo se ve si la
mides.

---

## Apéndice — Qué del MVP ya mitiga cada riesgo

| Riesgo | Mitigación en este MVP | Lo que falta para prod |
|---|---|---|
| Caída transitoria de Groq | `tenacity` con backoff exponencial, 3 reintentos | Circuit breaker, fallback model, cola persistente |
| Caída de Telegram al responder | Reintento, fallback a texto plano si Markdown rompe | Cola con dead-letter para fallos definitivos |
| Caída de Sheets | Fail-soft: si Sheets cae el usuario igual recibe respuesta, queda en logs | Buffer local + reintento diferido, idealmente DB primaria y Sheets como vista |
| Webhook duplicado por reintento de Telegram | Respondemos 200 antes de procesar | Idempotencia por `update_id` en Redis |
| Prompt injection en el texto del lead | Delimitadores explícitos + instrucción al LLM + flag `suspicious_input` + validación cruzada de checks | Guardrail de salida con schema validation, clasificador previo |
| LLM alucinando `qualified=true` sin criterios | Forzado a `false` si algún check individual es `false` | Tests automáticos contra dataset etiquetado |
| Abuso por mensaje gigante | `MAX_LEAD_LENGTH=2000` con truncado | Rate limiting por `chat_id`, costo máximo por usuario |
| Suplantación de webhook | `X-Telegram-Bot-Api-Secret-Token` validado en cada request | Adicionalmente filtro por IP range de Telegram |
| Secretos en disco | `.gitignore` excluye `.env` y `google-credentials.json`, chmod 600 | Vault/Secret Manager, rotación automática |
| Costes API desbocados | Modelo gratuito + temperature baja + max_tokens limitado | Caché por hash, presupuesto + alertas, multi-provider |

## Apéndice — Cosas que NO hice por scope de la demo

- Tests unitarios del qualifier (haría `pytest` con fixtures de leads etiquetados).
- CI/CD (GitHub Actions: lint + tests + deploy automático a Plesk vía SSH).
- Dashboard de métricas (un Grafana con tasa de cualificación por día, modelo, sector).
- Soporte de audio (Telegram permite voice notes — un Whisper barato antes del clasificador abriría ese canal).
- Multi-tenancy: hoy una sola hoja para todos los chats; en producción cada cliente tendría su propia Sheet o tabla.
- Internacionalización: prompt está en español, pero algunos términos podrían dar falsos negativos con leads escritos en inglés sobre LatAm.
