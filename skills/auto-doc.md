# Auto-Documentation Skill

## Descripción
Documenta automáticamente cada solución en el wiki siguiendo el patrón de Karpathy.

## Triggers
- Después de resolver un incidente
- Después de ejecutar un fix
- Después de aprender algo nuevo

## Workflow

### 1. Documentar Incidente
Crear `wiki/incidents/YYYY-MM-DD-host-cause.md` con timeline, causa raíz, fix y prevención.

### 2. Actualizar Host
Actualizar `wiki/hosts/hostname.md` con incidentes pasados.

### 3. Crear Runbook (si es nuevo)
Crear `wiki/runbooks/action-description.md` con pasos detallados.

### 4. Actualizar Índice
Actualizar `wiki/index.md` con la nueva página.

### 5. Log
Agregar entrada a `wiki/log.md`.
