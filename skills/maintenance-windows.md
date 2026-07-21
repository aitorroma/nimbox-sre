# Ventanas de mantenimiento

Antes de abrir, escalar o corregir una alerta de un host, consulta
`maintenance(action="get", hostname="...")`. Una ventana activa debe quedar
reflejada en el informe para evitar falsos positivos y cambios durante un
mantenimiento planificado.

- `list` y `get` son operaciones de solo lectura.
- Para una alerta firing que el agente vaya a diagnosticar, si no hay ventana
  activa, activa sin confirmación una ventana de **30 minutos** con motivo
  `Diagnóstico automático de alerta <id>: <service>` y `requested_by=nimbox-sre`.
  No la renueves automáticamente y deja que expire. Esto es una excepción
  exclusiva para acotar alertas duplicadas durante el diagnóstico de lectura.
- Fuera de ese flujo, `enable` y `disable` modifican el estado operativo:
  exige confirmación explícita del usuario y muestra host y payload antes de
  ejecutar.
- Al activar, requiere motivo y una única expiración: `duration_minutes`,
  `duration_seconds` o `until` ISO-8601. Para un mantenimiento indefinido usa
  exclusivamente `indefinite=true`, sin ningún campo de expiración, y sólo tras
  confirmación explícita del usuario. Indica en el resumen que deberá
  finalizarse manualmente.
- Modern Collector registra `reason` y `requested_by`; usa `nimbox-sre` como
  solicitante salvo que el usuario indique otro valor.
