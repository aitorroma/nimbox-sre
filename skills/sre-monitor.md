# SRE Monitor Skill

## Descripción
Monitorea la salud de los hosts periodicamente y registra cambios.

## Triggers
- Heartbeat SRE cada 30 minutos
- Alerta de Nightingale

## Acciones
1. Consultar targets en Nightingale
2. Verificar métricas (CPU, RAM, disco)
3. Comparar con umbrales
4. Si hay problema → resumir evidencia y activar `incident-response` / `remediation-loop`
5. El heartbeat no ejecuta SSH ni correcciones: espera aprobación o un runbook para la fase de remediación.
6. Actualizar wiki/hosts/ tras una investigación o corrección confirmada.

## Umbrales
- CPU > 80%: Warning
- CPU > 95%: Critical
- RAM > 85%: Warning
- RAM > 95%: Critical
- Disco > 85%: Warning
- Disco > 95%: Critical

## Comandos
```bash
# Verificar un host
curl -H "X-Warpgate-Token: $TOKEN" "$API/targets/{id}"

# Verificar alertas activas
curl -H "X-Warpgate-Token: $TOKEN" "$API/alert-cur-events"
```
