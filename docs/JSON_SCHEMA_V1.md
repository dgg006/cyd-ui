# Contrato JSON v1

## Documento

- `schema_version`: obligatorio; actualmente `1`.
- `pages`: entre 1 y 8 páginas.
- Los identificadores de controles deben ser únicos en todo el documento.

## Página

- `template`: actualmente `button_grid`.
- `variant`: `two_buttons`, `four_buttons` o `six_buttons`.
- `title`: texto obligatorio y no vacío.
- `controls`: entre 1 y la capacidad máxima de la variante.

## Control

- `type`: actualmente `button`.
- `id`: identificador opaco y globalmente único.
- `caption`: texto visible.
- `color`: formato `#RRGGBB`.
- `meta`: objeto opcional reservado para evolución futura.

## Navegación

- Las flechas superiores recorren las páginas circularmente.
- Cambiar de página reutiliza los widgets del template activo.
- Los estados recibidos se conservan al navegar.
- Agregar, quitar, ordenar o cambiar variantes de páginas no requiere recompilar firmware.

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
{"type":"control_changed","id":"living","active":true,"reliability":"valid"}
```

```json
{"type":"reload"}
```

`reliability` admite `valid`, `unknown`, `stale`, `disconnected` y `unavailable`.

## Aplicación segura y persistencia

1. La configuración se descarga por HTTP cuando está disponible.
2. Se parsea y valida completamente antes de modificar la UI.
3. Si es válida, se aplica y se guarda en la caché flash.
4. Si falla, se conserva la interfaz activa.
5. El orden de recuperación es HTTP -> caché flash -> configuración embebida.
