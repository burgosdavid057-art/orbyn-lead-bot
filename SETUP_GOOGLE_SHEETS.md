# Setup Google Sheets — paso a paso

Esto se hace una sola vez. Tiempo estimado: 10 minutos.

## 1. Crear un proyecto en Google Cloud

1. Ve a [console.cloud.google.com](https://console.cloud.google.com/).
2. Arriba a la izquierda, en el selector de proyectos → **Nuevo proyecto**.
3. Nombre: `orbyn-lead-bot` (o lo que quieras).
4. Crear y esperar a que aparezca seleccionado.

## 2. Activar las APIs necesarias

1. Menú lateral → **APIs y servicios** → **Biblioteca**.
2. Busca `Google Sheets API` → entra → **Habilitar**.
3. Vuelve a la biblioteca, busca `Google Drive API` → entra → **Habilitar**.

> La Drive API es necesaria porque `gspread` la usa para localizar la hoja por ID.

## 3. Crear el Service Account

1. Menú lateral → **APIs y servicios** → **Credenciales**.
2. Arriba: **+ Crear credenciales** → **Cuenta de servicio**.
3. Nombre: `orbyn-bot-sa`. ID: se autocompleta. **Crear y continuar**.
4. En el paso de roles, **omitir** (no le damos roles a nivel de proyecto, le daremos acceso solo a la hoja específica). Continuar → Listo.

## 4. Generar la clave JSON

1. En la lista de Cuentas de servicio, haz clic en la que acabas de crear.
2. Pestaña **Claves** → **Agregar clave** → **Crear clave nueva** → **JSON** → Crear.
3. Se descarga un archivo `.json`. **Renómbralo a `google-credentials.json`** y muévelo a la raíz del proyecto (`orbyn-lead-bot/google-credentials.json`).
4. Abre el JSON y copia el campo `client_email` (algo como `orbyn-bot-sa@orbyn-lead-bot.iam.gserviceaccount.com`). Lo vas a necesitar en el siguiente paso.

> Trata este archivo como una contraseña. Está en `.gitignore`.

## 5. Crear la Google Sheet y compartirla

1. Ve a [sheets.google.com](https://sheets.google.com/) y crea una hoja nueva.
2. Nómbrala `Orbyn Leads` (o lo que quieras).
3. **Renombra la primera pestaña** abajo a `Leads` (doble clic en `Hoja1` → renombrar).
4. Arriba a la derecha → **Compartir** → pega el `client_email` del paso 4 → permiso **Editor** → desmarca "Notificar a las personas" → **Compartir**.
5. Copia el ID de la hoja desde la URL: `https://docs.google.com/spreadsheets/d/AQUI_ESTA_EL_ID/edit`.

## 6. Configurar `.env`

En tu `.env`:

```dotenv
GOOGLE_SHEET_ID=AQUI_ESTA_EL_ID
GOOGLE_SHEET_TAB=Leads
GOOGLE_CREDENTIALS_PATH=./google-credentials.json
```

## 7. Verificar conexión

```bash
python test_local.py sheets-health
```

Salida esperada:

```json
{
  "ok": true,
  "sheet_title": "Orbyn Leads",
  "tab": "Leads",
  "rows": 1000
}
```

La primera vez que se escriba una fila, el código añade el encabezado automáticamente. No necesitas crear las columnas a mano.

## Troubleshooting

- **`The caller does not have permission`**: no compartiste la hoja con el `client_email` del service account. Repite el paso 5.
- **`Requested entity was not found`**: ID de la hoja mal copiado, o la hoja fue eliminada.
- **`API has not been used in project ... or it is disabled`**: faltó activar la Sheets API o la Drive API. Vuelve al paso 2.
- **`invalid_grant: Token has been expired or revoked`**: el JSON del service account es viejo o fue revocado. Genera una clave nueva (paso 4).
