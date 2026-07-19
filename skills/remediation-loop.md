# Bucle de análisis y corrección SRE

## Objetivo
Resolver incidencias de forma trazable con el ciclo **detectar → analizar → corregir → verificar → documentar**, sin repetir intentos ciegos ni ejecutar cambios destructivos.

## Activación
- Alerta activa de Nightingale.
- Petición del usuario de investigar, corregir o validar un host.
- Resultado de una corrección que no ha restaurado el servicio.

## Ciclo obligatorio

### 1. Detectar y acotar
1. Consulta Nightingale: alertas activas y el target afectado.
2. Recoge una línea base: hora UTC, host, síntoma, severidad y métricas.
3. Si hace falta, usa `warpgate(action="run_agent_ssh_command")` para comandos de solo lectura (`hostname`, `df -h`, `free -m`, `uptime`, `systemctl --failed`, logs acotados).

### 2. Analizar
1. Pide RCA a OpenSRE con el contexto y las observaciones reales.
2. Formula una hipótesis verificable y su evidencia. No confundas una hipótesis con una causa raíz.
3. Elige una corrección mínima y reversible. Si no hay evidencia suficiente, escala en lugar de probar comandos al azar.

### 3. Corregir de forma segura
- **Sin confirmación adicional:** observación, diagnóstico y validación.
- **Con runbook aprobado o confirmación del usuario:** una corrección acotada que no borre datos ni cambie credenciales, firewall, red o despliegues.
- **Siempre requiere confirmación explícita:** borrado de datos/logs, `docker system prune`, cambios de paquetes/configuración, reinicios de servicios de negocio, cambios de red/SSH/usuarios y comandos irreversibles.
- Ejecuta una única corrección por iteración. Indica el comando y el efecto esperado antes de ejecutarlo.

### 4. Verificar
1. Repite la métrica o comprobación que originó la alerta.
2. Verifica salud del servicio y ausencia de efectos colaterales.
3. Si la alerta sigue activa, vuelve a analizar con la evidencia nueva; máximo una segunda corrección. Después escala con diagnóstico, comandos ejecutados y una propuesta concreta.
4. Si SSH falla antes de llegar al target, no repitas SSH: informa del error de acceso y resuelve primero Warpgate/target.

### 5. Documentar y comunicar
Registra en `wiki/incidents/` el síntoma, línea base, hipótesis, evidencia, cambio, validación, rollback, estado final y prevención. En Telegram comunica estado, evidencia, acción aplicada (o motivo de escalado) y resultado de validación. Nunca reveles secretos, claves privadas o credenciales.
