# NimBox SRE

Agente **Hermes** para operaciones SRE de NimBox. Atiende conversaciones y
alertas, consulta la observabilidad, investiga incidencias y puede realizar
intervenciones controladas mediante Warpgate.

## Capacidades

- **Nightingale**: targets, alertas y métricas.
- **OpenSRE**: investigación y diagnóstico de incidencias.
- **Warpgate**: tickets, targets y acceso SSH controlado con clave persistente
  del agente.
- **Modern Collector**: consulta y gestión confirmada de ventanas de
  mantenimiento.
- **Webhook HMAC**: despierta Hermes de inmediato cuando Modern Collector abre
  una incidencia.
- **Telegram**: canal de interacción, avisos y ejecución del heartbeat.

## Seguridad operativa

El agente trabaja con el flujo `skills/remediation-loop.md`:

1. Comprueba primero si el host está en mantenimiento.
2. Reúne evidencia de solo lectura con Nightingale y OpenSRE.
3. Propone una hipótesis y el siguiente paso.
4. Solo aplica una corrección mínima y reversible con runbook aprobado o
   confirmación explícita.

Nunca debe revelar claves, secretos de tickets ni claves privadas. Cambios de
configuración, reinicios, red, firewall, usuarios, SSH y mantenimiento exigen
confirmación explícita.

## Requisitos

- Docker y Docker Compose para desarrollo local, o Docker Swarm para
  producción.
- Credenciales y endpoints de Telegram, modelo LLM, Nightingale, Warpgate,
  OpenSRE y Modern Collector.
- Para producción, la red overlay externa `Nimbox360`.

## Configuración

Las credenciales **no se incluyen** en este repositorio. Use
`.env.swarm.example` como lista de variables y guarde los valores en el gestor
de secretos o entorno de despliegue:

```sh
cp .env.swarm.example .env
cp .env.swarm.example docker/.env
```

Variables principales:

| Grupo | Variables |
| --- | --- |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_ALERT_CHAT_ID` |
| Modelo | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| Observabilidad | `NIGHTINGALE_API_URL`, `NIGHTINGALE_TOKEN`, `OPENSRE_URL` |
| Acceso | `WARPGATE_API_URL`, `WARPGATE_TOKEN` |
| Mantenimiento | `MONIT_API_URL`, `MONIT_API_TOKEN` |
| Webhook | `ALERT_WEBHOOK_SECRET` |

`ALERT_WEBHOOK_SECRET` es el secreto HMAC compartido con Modern Collector. En
local Compose se usa también como `WEBHOOK_SECRET`; en Swarm el stack realiza
ese mapeo automáticamente.

## Desarrollo local

```sh
docker compose up -d --build
docker compose logs -f hermes
```

El listener webhook queda publicado en `http://localhost:8644`. La ruta de
Modern Collector es:

```text
POST /webhooks/modern-collector-alerts
```

## Despliegue en Docker Swarm

Construya y publique una imagen versionada:

```sh
docker build -t tuxed/nimbox-sre-hermes:latest .
docker push tuxed/nimbox-sre-hermes:latest
```

Exporte las variables requeridas y despliegue el stack:

```sh
docker stack deploy -c docker-stack.yml nimbox-sre
```

El servicio `hermes` queda únicamente en la overlay `Nimbox360`; no necesita
un puerto público para recibir eventos del servicio `monit` de la misma red.

## Modern Collector → Hermes

El emisor de alertas y API de mantenimiento está en
[Modern Collector](https://github.com/aitorroma/modern-collector).

En los servicios `monit` y `telegram-polling` de Modern Collector configure:

```yaml
ALERT_WEBHOOK_URL: http://hermes:8644/webhooks/modern-collector-alerts
ALERT_WEBHOOK_SECRET: ${ALERT_WEBHOOK_SECRET}
```

Modern Collector firma el payload con HMAC SHA-256 y Hermes valida timestamp,
firma e idempotencia antes de iniciar el análisis. Véase
[`docs/modern-collector-webhook.md`](docs/modern-collector-webhook.md).

## Estructura relevante

```text
plugins/nimbox_sre/  Integración de Nightingale, Warpgate, OpenSRE y mantenimiento
skills/              Procedimientos de respuesta y remediación
docker/              Política del agente y scripts de arranque
docker-compose.yml   Ejecución local
docker-stack.yml     Despliegue Docker Swarm
```

## Licencia

Pendiente de definir.
