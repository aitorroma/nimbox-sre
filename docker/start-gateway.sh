#!/bin/sh
# Runs after s6 restores container environment and drops to the hermes user.
# The route deliberately has no `secret` field: WebhookAdapter resolves it from
# WEBHOOK_SECRET, keeping credentials out of all repository-managed files.
set -eu

: "${WEBHOOK_SECRET:?WEBHOOK_SECRET is required}"
: "${TELEGRAM_ALERT_CHAT_ID:?TELEGRAM_ALERT_CHAT_ID is required}"

mkdir -p /opt/data
umask 077
cat > /opt/data/webhook_subscriptions.json <<EOF
{
  "modern-collector-alerts": {
    "description": "Analiza alertas firmadas de Modern Collector",
    "events": ["modern_collector.alert"],
    "prompt": "Incidencia desde Modern Collector: id={id}; estado={status}; severidad={severity}; host={host}; tipo={kind}; servicio={service}; mensaje={message}. Aplica remediation-loop: consulta primero maintenance y monit_alerts para el host; si ya hay mantenimiento, informa sin corregir. Si la alerta está firing, no hay ventana y vas a investigarla, activa maintenance(enable) durante 30 minutos con reason='Diagnóstico automático de alerta {id}: {service}' y requested_by=nimbox-sre; no la renueves ni la desactives. Después reúne evidencia de solo lectura con nightingale(get_monit_host_status) y OpenSRE. Si OpenSRE falla o falta evidencia, crea un ticket Warpgate efímero para agente y ejecuta diagnósticos de solo lectura del host y del servicio afectado (para Docker: docker ps -a, docker compose ps, docker logs --tail y systemctl/journalctl acotados). Esto está autorizado sin confirmación. No uses provision_agent_ssh_key, run_agent_ssh_command, get_ssh_client_keys, no instales claves públicas y no apliques cambios, reinicios o correcciones sin confirmación explícita. Revoca el ticket al terminar y envía un resumen con evidencia y siguiente acción concreta.",
    "skills": ["incident-response", "remediation-loop", "maintenance-windows", "sre-monitor"],
    "deliver": "telegram",
    "deliver_extra": {"chat_id": "${TELEGRAM_ALERT_CHAT_ID}"},
    "deliver_only": false
  }
}
EOF
chmod 600 /opt/data/webhook_subscriptions.json
exec hermes gateway
