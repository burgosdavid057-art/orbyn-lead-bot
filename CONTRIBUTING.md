# Cómo contribuir

## Correr los tests

La suite de tests unitarios **no necesita** claves de Groq, Telegram ni Google:
mockea la llamada al LLM y usa variables de entorno ficticias (ver
`conftest.py`). Corre en segundos y sin red.

```bash
pip install -r requirements-dev.txt
pytest
```

> `test_local.py` es distinto: ese sí llama a las APIs reales y sirve para
> probar la integración de punta a punta con tu `.env` configurado.

## Antes de abrir un PR

- Que `pytest` pase en verde.
- Si tocas la lógica de `qualifier.py` (parseo, coherencia de criterios,
  formateo), acompáñala de un test.
- Mantené el estilo existente y el principio de **fail-soft**: el bot nunca debe
  lanzar una excepción sin controlar hacia el usuario.

El mismo `pytest` corre en CI (GitHub Actions) contra Python 3.11, 3.12 y 3.13.
