# SRE Agent Wiki Schema

## Estructura

```
wiki/
├── index.md          # Catálogo de todo el wiki
├── log.md           # Registro cronológico
├── hosts/           # Info por servidor
├── incidents/       # Incidentes resueltos
├── runbooks/        # Procedimientos
├── decisions/       # Decisiones técnicas
└── sources/         # Fuentes de datos
```

## Convenciones

### Páginas de Host (`hosts/`)
- Nombre: `hostname.md`
- Contenido: specs, servicios, métricas típicas, incidentes pasados

### Páginas de Incidente (`incidents/`)
- Nombre: `YYYY-MM-DD-host-cause.md`
- Contenido: timeline, causa raíz, evidencia, fix aplicado, prevención

### Runbooks (`runbooks/`)
- Nombre: `action-description.md`
- Contenido: paso a paso, comandos, validaciones

### Decisiones (`decisions/`)
- Nombre: `YYYY-MM-DD-decision.md`
- Contenido: contexto, opciones evaluadas, decisión tomada, por qué

## Workflow

1. **Investigar**: Al recibir alerta, revisar hosts/ e incidents/
2. **Resolver**: Aplicar fix, documentar en incidents/
3. **Aprender**: Si es nuevo, crear runbook/
4. **Actualizar**: Actualizar index.md y hosts/ relevantes
