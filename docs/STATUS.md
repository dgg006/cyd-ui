# Estado del proyecto

Actualizado: 2026-07-29

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
- Catálogo reducido de 50 iconos MDI con estados activo/inactivo; compilación
  verificada y pendiente de validación física en la próxima carga.

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

- DRAM estática: 51.516 bytes (28,5 %).
- Firmware con catálogo MDI y telemetría LDR: 1.352.751 bytes (73,7 % de la partición de aplicación).

## Próximo hito

Validar en uso real el configurador visual v0.1, completar los campos avanzados por dominio y agregar restauración desde el historial.

## Configurador visual v0.1

- Lista, alta, duplicación, eliminación y reordenamiento de páginas.
- Formularios definidos por template y variante.
- Edición de controles y selección de entidades desde Home Assistant.
- Búsqueda nativa de entidades y filtrado por dominios compatibles con cada template.
- Adaptación automática de `binary_sensor` mediante `device_class` y textos claros para estados `on/off`.
- Textos o símbolos `on/off` editables por control binario, sin campos numéricos irrelevantes.
- Búsqueda de iconos MDI y selección independiente para estados `on/off`.
- Vista previa de iconos usando la misma fuente incluida en el firmware.
- Vista previa local de 320 × 240.
- Vista previa del protector alineada con las posiciones y jerarquía visual usadas por LVGL en la CYD.
- Protector sin título obligatorio y tiempo de activación configurable entre nunca y 1 hora desde la interfaz.
- Atributos y acciones presentados como opciones legibles obtenidas de la entidad, sin exigir conocer nombres internos de Home Assistant.
- Validación del contrato antes de guardar.
- Copia recuperable, escritura atómica y recarga MQTT.
- El iniciador sirve `config/ui.json` como `/ui.json`, que es la ruta fija consumida por el firmware.

La arquitectura completa y las decisiones actualizadas están en `docs/ARCHITECTURE.md`.
# Actualización 2026-07-29 — configuración del dispositivo

- Brillo de la retroiluminación migrado a PWM sin interferir con el canal del parlante.
- LDR frontal incorporado como entrada de brillo automático, desactivado por defecto hasta calibrarlo en el lugar de uso.
- Modos de inactividad: reloj y clima, pantalla apagada, brillo tenue o desactivado.
- Horario nocturno con brillo y comportamiento de reposo propios.
- Volumen de 0 a 10 y activación independiente de toques, navegación y notificaciones.
- Editor visual con apartado fijo `Configuración` y prueba sonora.
- Lectura LDR actualizada cada segundo y calibración asistida de los extremos de oscuridad y mucha luz desde el editor.
- microSD deliberadamente postergada: exige una capa FATFS externa y compite por los buses SPI disponibles; no aporta valor inmediato al runtime actual.
