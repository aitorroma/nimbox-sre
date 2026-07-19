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
    "prompt": "Incidencia desde Modern Collector: id={id}; estado={status}; severidad={severity}; host={host}; tipo={kind}; servicio={service}; mensaje={message}. Aplica remediation-loop: consulta primero maintenance y monit_alerts para el host y, si está en mantenimiento, informa sin corregir. Después reúne evidencia de solo lectura mediante Nightingale/OpenSRE. No abras tickets, no ejecutes SSH ni apliques cambios o correcciones sin confirmación explícita. Envía un resumen breve con evidencia y próximo paso.",
    "skills": ["remediation-loop", "maintenance-windows", "sre-monitor"],
    "deliver": "telegram",
    "deliver_extra": {"chat_id": "${TELEGRAM_ALERT_CHAT_ID}"},
    "deliver_only": false
  }
}
EOF
chmod 600 /opt/data/webhook_subscriptions.json
exec hermes gateway
