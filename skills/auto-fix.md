# Auto-fix Skill

## Descripción
Ejecuta arreglos automáticos en servidores.

## Prerequisitos
- Host y síntoma verificados en Nightingale.
- Hipótesis y efecto esperado documentados en el incidente.
- Acceso con un ticket Warpgate efímero y `warpgate(action="run_ssh_command")`; no generes ni instales claves SSH.
- Runbook aprobado o confirmación explícita para ejecutar un cambio.

## Fixes disponibles

### Disco lleno (requiere confirmación)
```bash
# Rotar logs
journalctl --vacuum-size=100M

# Limpiar /tmp
find /tmp -type f -atime +7 -delete

# No ejecutar `docker system prune -f` automáticamente: puede borrar recursos
# necesarios. Propón primero una limpieza concreta y reversible.
```
