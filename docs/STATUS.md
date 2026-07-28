# Estado del proyecto

## Entorno

- Placa: ESP32-2432S028R CYD, conectada por COM57.
- ESPHome 2026.7.3 con ESP-IDF.
- Herramientas ESP-IDF en `C:\ESPHomeCache\idf`.
- Proyecto Arduino de validación conservado sin modificaciones.

## Hardware y conectividad verificados

- Pantalla ILI9341 y táctil XPT2046.
- Orientación horizontal y calibración táctil (`mirror_x: true`).
- Los seis botones coinciden con sus zonas táctiles.
- Wi-Fi y DHCP correctos; dirección observada: `192.168.31.213`.
- Broker MQTT de laboratorio accesible en `192.168.31.240:1883`.

## UI Engine implementado

- Componente externo `ui_engine`.
- `PageTemplate`, `TemplateRegistry` y `ButtonGrid`.
- Configuración JSON con pipeline `Parse -> Validate -> Apply` atómico.
- Proveedores HTTP, caché flash persistente y configuración embebida.
- Orden de recuperación: HTTP -> caché flash -> configuración embebida.
- Recarga remota sin recompilar mediante MQTT.
- Evento saliente genérico `control_id + action` por MQTT.
- Evento entrante `control_changed` con `active` y `reliability`.
- Estados visuales verificados: desconocido, encendido, apagado y no disponible.
- Una pulsación no modifica el estado visual hasta recibir confirmación del backend.
- Al conectar con MQTT, el panel publica automáticamente `sync_request` después de que el cliente está listo.
- Al perder MQTT, todos los controles pasan a `STALE_OR_DISCONNECTED`; al reconectar quedan `UNKNOWN` hasta sincronizarse.

## Contrato MQTT actual

- HA/backend -> panel: `esphome_ui/cyd-ui/event`.
- Panel -> HA/backend: `esphome_ui/cyd-ui/cmd`.
- Acción comprobada: `{"type":"action","id":"living","action":"toggle"}`.
- Estado comprobado: `{"type":"control_changed","id":"living","active":true,"reliability":"valid"}`.
- Recarga comprobada: `{"type":"reload"}`.
- Sincronización de arranque comprobada: `{"type":"sync_request"}`.

## Última compilación

- Resultado: correcto.
- DRAM: 49.940 bytes (27,6%).
- Flash: 1.089.923 bytes (59,4%).

## Próximo hito

## Integración real con Home Assistant

- `living` está mapeado externamente a `switch.sonoff_1001327309_2` mediante `config/backend-map.json`.
- Ciclo panel -> MQTT -> Home Assistant -> estado real -> panel verificado físicamente.
- Cambios hechos desde Home Assistant se reflejan automáticamente en el panel mediante seguimiento periódico.
- El token de Home Assistant permanece fuera del repositorio y no está incorporado al firmware.
- `tools/ha_bridge.py` funciona como backend de laboratorio; el firmware continúa ciego a Home Assistant.

## Navegación y variantes

- Navegación circular mediante flechas superiores.
- Estado de controles conservado al cambiar de página.
- Variantes `two_buttons`, `four_buttons` y `six_buttons` verificadas físicamente.
- Tres páginas cargadas desde JSON externo.
- La tercera página fue agregada sin recompilar ni grabar firmware.

## Próximo hito

Implementar el segundo tipo de template: una página de climatización reutilizable.
