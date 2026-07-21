# Bucle de análisis y corrección SRE

## Objetivo
Resolver incidencias de forma trazable con el ciclo **detectar → analizar → corregir → verificar → documentar**, sin repetir intentos ciegos ni ejecutar cambios destructivos.

## Activación
- Alerta activa de Nightingale.
- Petición del usuario de investigar, corregir o validar un host.
- Resultado de una corrección que no ha restaurado el servicio.

## Ciclo obligatorio

### 1. Detectar y acotar
1. Consulta Nightingale: alertas activas y `list_monit_hosts` / `get_monit_host_status` para el host afectado. No concluyas que no hay métricas porque el host no aparezca en `/targets`.
2. Recoge una línea base: hora UTC, host, síntoma, severidad, mantenimiento/archivado y métricas. Si la alerta está firing, no hay mantenimiento y vas a iniciar diagnóstico automático, activa `maintenance(enable)` durante 30 minutos con motivo `Diagnóstico automático de alerta <id>: <service>`. No la renueves ni la desactives automáticamente.
3. Si hace falta, está autorizado sin confirmación a crear un ticket Warpgate efímero para `agente` y usar `run_ssh_command` con comandos de solo lectura (`hostname`, `df -h`, `free -m`, `uptime`, `systemctl --failed`, `docker ps -a`, `docker compose ps`, `docker logs --tail`, `journalctl -n`, `systemctl status --no-pager`). Revoca el ticket al finalizar.
4. No uses `provision_agent_ssh_key`, `run_agent_ssh_command`, `get_ssh_client_keys` ni solicites instalar una clave pública en el host durante el diagnóstico automático.

### 2. Analizar
1. Pide RCA a OpenSRE con el contexto y las observaciones reales.
2. Formula una hipótesis verificable y su evidencia. No confundas una hipótesis con una causa raíz.
3. Elige una corrección mínima y reversible. Si no hay evidencia suficiente, escala en lugar de probar comandos al azar.

### 3. Corregir de forma segura
- **Sin confirmación adicional:** observación, diagnóstico, creación/revocación de ticket Warpgate efímero y validación.
- **Runbooks:** consulta `runbooks(list_approved)` y lee el candidato con `runbooks(get_approved)` antes de proponer una corrección. Sólo puede usarse si su ámbito (`host`, `service`, `kind`) coincide con la incidencia y el comando exacto aparece en `allowed_actions`. Un borrador no autoriza ningún cambio. Si el procedimiento es repetible, puedes crear `runbooks(create_draft)` con evidencia, pasos, comandos permitidos y rollback; Hermes nunca puede aprobarlo ni revocarlo.
- **Con runbook aprobado válido o confirmación del usuario:** una corrección acotada que no borre datos ni cambie credenciales, firewall, red o despliegues.
- **Siempre requiere confirmación explícita:** borrado de datos/logs, `docker system prune`, cambios de paquetes/configuración, reinicios de servicios de negocio, cambios de red/SSH/usuarios y comandos irreversibles.
- Ejecuta una única corrección por iteración. Indica el comando y el efecto esperado antes de ejecutarlo.

### 4. Verificar
1. Repite la métrica o comprobación que originó la alerta.
2. Verifica salud del servicio y ausencia de efectos colaterales.
3. Si la alerta sigue activa, vuelve a analizar con la evidencia nueva; máximo una segunda corrección. Después escala con diagnóstico, comandos ejecutados y una propuesta concreta.
4. Si SSH falla antes de llegar al target, no repitas SSH, no intentes instalar claves y no abras un bucle de tickets: informa del error de acceso y escala.

### 5. Documentar y comunicar
Registra en `wiki/incidents/` el síntoma, línea base, hipótesis, evidencia, cambio, validación, rollback, estado final y prevención. En Telegram comunica estado, evidencia, acción aplicada (o motivo de escalado) y resultado de validación. Nunca reveles secretos, claves privadas o credenciales.
