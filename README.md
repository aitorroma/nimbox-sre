# NimElectric Telegram Agent

Bot para **Telegram + PDFs de factura + API NimElectric + informe PDF**, listo para **Coolify**.

## Qué hace

1. Recibe una factura PDF por webhook de Telegram.
2. Extrae texto del PDF.
3. Intenta sacar datos con parser local.
4. Si faltan campos, usa **Agno + MiniMax** para completar extracción estructurada.
5. Consulta la API de NimElectric:
   - `GET /enrich/cups/{cups}`
   - `GET /tariffs/compare/cups/{cups}`
6. Ejecuta un simulador local inspirado en el CRM de NimElectric.
7. Responde en Telegram con resumen, ahorro estimado y propuesta.
8. Permite:
   - ver referencias **TD2.0**
   - generar un **informe PDF NimElectric**
   - descargar el **JSON** del informe

## Stack

- FastAPI
- Agno
- MiniMax (OpenAI-compatible)
- requests
- pypdf
- pytesseract
- reportlab
- sqlite3

## Variables de entorno

Ver `.env.example`.

Claves principales:

- `TELEGRAM_BOT_TOKEN`
- `NIMELECTRIC_API_KEY`
- `APP_BASE_URL`
- `MINIMAX_API_KEY`
- `MINIMAX_BASE_URL=https://api.minimax.io/v1`
- `MINIMAX_MODEL=MiniMax-M2.7`

## Endpoints

- `GET /health`
- `GET /debug/auth`
- `GET /debug/minimax`
- `POST /telegram/webhook`
- `POST /telegram/set-webhook`

## MiniMax + Agno

La extracción IA usa:
- `agno.models.openai.like.OpenAILike`
- endpoint OpenAI-compatible de MiniMax
- output estructurado con Pydantic

Si MiniMax no está configurado, el bot sigue funcionando solo con parser local.

## Deploy en Coolify

Usa el `Dockerfile` del repo.

### Variables recomendadas en Coolify

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `NIMELECTRIC_API_KEY`
- `APP_BASE_URL`
- `MINIMAX_API_KEY`
- `MINIMAX_BASE_URL=https://api.minimax.io/v1`
- `MINIMAX_MODEL=MiniMax-M2.7`

### Pasos

1. Crear app en Coolify desde este repo.
2. Configurar variables de entorno.
3. Desplegar.
4. Registrar webhook:

```bash
curl -X POST https://tu-dominio/telegram/set-webhook
```

### Verificación

```bash
curl https://tu-dominio/health
curl https://tu-dominio/debug/minimax
curl https://tu-dominio/debug/auth
```

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8080
```

## Notas

- El estado por chat se guarda en `STATE_DB_PATH`.
- Los informes y JSON se guardan en `OUTPUT_DIR`.
- El generador de informe reutiliza la plantilla NimElectric en `app/report/scripts/nimelectric_report.py`.
