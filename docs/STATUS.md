# Estado del proyecto

Actualizado: 2026-07-28

## Plataforma validada

- ESP32-2432S028R CYD por COM57.
- ESPHome 2026.7.3 sobre ESP-IDF 5.5.5.
- Pantalla ILI9341 y táctil XPT2046 en buses SPI separados.
- Wi-Fi, HTTP, MQTT, caché flash, reloj SNTP y parlante verificados.

## Runtime implementado

- Componente externo `ui_engine` en C++.
- Configuración JSON con aplicación atómica.
- Descarga HTTP, respaldo flash y configuración embebida segura.
- Recarga sin recompilar mediante MQTT.
- Acciones genéricas y confirmación del backend.
- Navegación circular, conservación de estado y protector de pantalla.
- Estados `UNKNOWN`, `VALID` y `STALE_OR_DISCONNECTED`.

## Templates verificados físicamente

- `button_grid`: 2, 4 y 6 botones.
- `climate`: temperatura actual, objetivo y ajuste incremental.
- `clock_weather`: reloj y clima como protector de pantalla.
- `sensor_grid`: cuatro valores con unidad y precisión.
- `cover`: posición, apertura/cierre total y pasos de 10 %.

## Integración de laboratorio

- Backend bidireccional con Home Assistant mediante HTTPS/WebSocket y MQTT.
- Cambios externos reflejados en tiempo real.
- Sonidos `attention`, `notification`, `success`, `warning` y `error`.
- Evento de Home Assistant `cyd_ui_sound` validado de extremo a extremo.
- El encendido del calefactor permanece bloqueado; solo se permite leer y cambiar su objetivo.

## Memoria de referencia

- DRAM estática: 50.788 bytes (28,1 %).
- Firmware: aproximadamente 1.274 kB (69,4 % de la partición de aplicación).

## Próximo hito

Construir el configurador visual para agregar, quitar, ordenar y editar páginas, elegir entidades de Home Assistant, guardar con validación y recargar la CYD sin flashear.

La arquitectura completa y las decisiones actualizadas están en `docs/ARCHITECTURE.md`.
