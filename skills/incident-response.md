# Incident Response Skill

## Descripción
Responde a incidentes de producción automáticamente.

## Triggers
- Alerta crítica de Nightingale
- Solicitud manual por Telegram

## Playbook obligatorio para alertas de Modern Collector

Ejecuta estos pasos en orden. No termines el informe tras el paso de
recopilación: continúa al diagnóstico remoto cuando haya una alerta *firing*
sin mantenimiento previo.

1. **Abrir el incidente.** Consulta `monit_alerts(get, incident_id)` y
   `maintenance(get, hostname)`. Si ya hay una ventana activa, informa de la
   alerta planificada y no diagnostiques ni modifiques su estado.
2. **Marcar la investigación.** Para una alerta *firing* sin mantenimiento,
   reclama el incidente con `monit_alerts(claim)` y activa
   `maintenance(enable, duration_minutes=30)` con el motivo
   `Diagnóstico automático de alerta <id>: <service>`. Añade un comentario de
   inicio con `monit_alerts(comment)`. No renueves esta ventana ni la elimines
   automáticamente.
3. **Recoger la línea base.** Consulta
   `nightingale(get_monit_host_status, host)` y `nightingale(list_alerts)`.
   Usa las métricas Prometheus de Monit aunque el host no esté en
   `nightingale(list_targets)`.
4. **Formar hipótesis.** Solicita RCA a OpenSRE con la alerta y las métricas.
   Si devuelve un error, anótalo y continúa: no es un bloqueo.
5. **Diagnosticar remotamente.** Crea un ticket Warpgate efímero para
   `agente`, ejecuta `run_ssh_command` de solo lectura y revoca el ticket. Para
   Docker consulta, como mínimo, `docker ps -a`, `docker compose ps` y
   `docker logs --tail`; complementa con `df -h`, `free -m`, `uptime` y logs de
   systemd acotados. No generes ni instales claves públicas, y no uses
   `run_agent_ssh_command`.
6. **Concluir sin cambiar.** Repite la métrica/estado del servicio. Si está
   recuperado o la investigación ha terminado, ciérralo con
   `monit_alerts(close)` incluyendo evidencia final; el cierre conserva el
   incidente para auditoría y retención. Si aún requiere trabajo humano,
   publica un comentario con la evidencia, hipótesis y siguiente corrección
   propuesta, y libéralo sólo si no queda trabajo automático pendiente.
7. **Pedir confirmación para corregir.** Busca primero un candidato con
   `runbooks(list_approved)` y obtén su detalle con `runbooks(get_approved)`.
   Sólo vale si host, servicio y tipo de alerta coinciden y el comando exacto
   está en `allowed_actions`. Si no existe, puedes crear un borrador mediante
   `runbooks(create_draft)`. Conserva el ID devuelto: si hay que mejorar ese
   procedimiento usa `runbooks(update_draft, runbook_id=...)` para crear una
   nueva versión del mismo, nunca una copia duplicada. Hermes nunca puede
   aprobarlo ni ejecutarlo como aprobado.
   Reiniciar servicios, ejecutar `docker compose up`, cambiar configuración,
   instalar paquetes, borrar datos o modificar red/SSH requiere confirmación
   explícita cuando sea una acción sensible.

## Respuesta esperada

Indica: mantenimiento creado o existente y su expiración; ticket revocado;
comandos de solo lectura ejecutados; evidencia; hipótesis; y la acción concreta
que requiere confirmación, si aplica. Nunca expongas secretos de tickets.
