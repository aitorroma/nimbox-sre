# Ventanas de mantenimiento

Antes de abrir, escalar o corregir una alerta de un host, consulta
`maintenance(action="get", hostname="...")`. Una ventana activa debe quedar
reflejada en el informe para evitar falsos positivos y cambios durante un
mantenimiento planificado.

- `list` y `get` son operaciones de solo lectura.
- `enable` y `disable` modifican el estado operativo: exige confirmación
  explícita del usuario y muestra host y payload antes de ejecutar.
- Al activar, requiere motivo y una única expiración: `duration_minutes`,
  `duration_seconds` o `until` ISO-8601. No crees mantenimientos indefinidos.
- Modern Collector registra `reason` y `requested_by`; usa `nimbox-sre` como
  solicitante salvo que el usuario indique otro valor.
