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

Validar en uso real el configurador visual v0.1, completar los campos avanzados por dominio y agregar restauración desde el historial.

## Configurador visual v0.1

- Lista, alta, duplicación, eliminación y reordenamiento de páginas.
- Formularios definidos por template y variante.
- Edición de controles y selección de entidades desde Home Assistant.
- Búsqueda nativa de entidades y filtrado por dominios compatibles con cada template.
- Adaptación automática de `binary_sensor` mediante `device_class` y textos claros para estados `on/off`.
- Textos o símbolos `on/off` editables por control binario, sin campos numéricos irrelevantes.
- Vista previa local de 320 × 240.
- Validación del contrato antes de guardar.
- Copia recuperable, escritura atómica y recarga MQTT.
- El iniciador sirve `config/ui.json` como `/ui.json`, que es la ruta fija consumida por el firmware.

La arquitectura completa y las decisiones actualizadas están en `docs/ARCHITECTURE.md`.
