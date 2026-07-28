# Contrato JSON v1

## Documento

- `schema_version`: obligatorio; actualmente `1`.
- `pages`: entre 1 y 8 páginas.
- Los IDs de controles deben ser únicos en todo el documento.
- Puede existir como máximo una página con `screensaver: true`.

## Campos de página

- `template`: nombre registrado del template.
- `variant`: variante semántica admitida por el template.
- `title`: texto obligatorio y no vacío.
- `screensaver`: booleano opcional; solo válido para `clock_weather`.
- `controls`: controles requeridos por el contrato del template.

## Campos de control

- `type`: `button` o `value` según el template.
- `id`: identificador opaco y globalmente único.
- `role`: función semántica dentro de templates especializados.
- `caption`: texto visible.
- `color`: formato `#RRGGBB`.
- `unit`: unidad opcional para valores.
- `action`: acción genérica emitida al tocar.
- `meta`: objeto opcional reservado para evolución futura.

## Templates y variantes actuales

### `button_grid`

- Variantes: `two_buttons`, `four_buttons`, `six_buttons`.
- Controles: exclusivamente `type: button`.
- Capacidad: 2, 4 o 6 según la variante.

### `climate`

- Variante: `thermostat`.
- Roles obligatorios: `current_temperature`, `target_temperature`, `decrease`, `power`, `increase`.
- Los dos valores de temperatura usan `type: value`; las acciones usan `type: button`.

### `clock_weather`

- Variante: `screensaver`.
- Roles obligatorios: `condition`, `outside_temperature`, `humidity`.
- Todos los controles son `type: value`.

### `sensor_grid`

- Variante: `four_values`.
- Entre uno y cuatro controles `type: value`.
- Admite `unit` y precisión definida en el backend.

### `cover`

- Variante: `position_controls`.
- Roles obligatorios actuales: `position`, `state`, `open`, `close`, `close_step`, `open_step`.
- `position` y `state` son valores; los demás son botones.
- El runtime acepta temporalmente el formato anterior con `stop` para migrar cachés existentes.

## Navegación

- Las flechas recorren las páginas circularmente.
- La página `screensaver` queda fuera de la navegación manual.
- Los estados recibidos se conservan al navegar.
- Agregar, quitar, ordenar o cambiar páginas no requiere recompilar mientras los templates ya existan en firmware.

## MQTT

### Panel hacia backend

Tópico: `esphome_ui/cyd-ui/cmd`.

```json
{"type":"action","id":"living","action":"toggle"}
```

```json
{"type":"sync_request"}
```

### Backend hacia panel

Tópico: `esphome_ui/cyd-ui/event`.

```json
{"type":"control_changed","id":"living","active":true,"value":"","reliability":"valid"}
```

```json
{"type":"reload"}
```

```json
{"type":"sound","sound":"attention"}
```

`reliability` admite `valid`, `unknown`, `stale`, `disconnected` y `unavailable`; el runtime los representa mediante sus tres estados internos de confiabilidad.

## Aplicación segura y persistencia

1. En el arranque se lee la caché flash.
2. La caché debe completar parseo y validación antes de aplicarse.
3. Si la caché es inválida, se usa la configuración embebida.
4. Al conectar, la configuración remota se descarga por HTTP.
5. Una candidata remota solo sustituye la UI después de validarse por completo.
6. La configuración remota aceptada se guarda en flash.
7. Si una recarga falla, se conserva la interfaz activa.
