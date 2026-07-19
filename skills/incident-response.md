# Incident Response Skill

## Descripción
Responde a incidentes de producción automáticamente.

## Triggers
- Alerta crítica de Nightingale
- Solicitud manual por Telegram

## Workflow
Sigue `remediation-loop.md`:
1. **Acknowledge y línea base**: confirmar la alerta y consultar Nightingale.
2. **Investigar**: usar OpenSRE y SSH de solo lectura por Warpgate.
3. **Evaluar**: elegir una causa verificable y una corrección mínima.
4. **Actuar**: usar `run_agent_ssh_command` sólo con un runbook aprobado o tras confirmación para cambios.
5. **Validar**: repetir la métrica/health check original; máximo dos iteraciones.
6. **Documentar y notificar**: registrar el incidente y comunicar evidencia, acción y estado.
