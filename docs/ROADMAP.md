# Estado y hoja de ruta

Actualizado: 2026-07-29

## Validado en hardware

- ESP32-2432S028R CYD sin PSRAM.
- ESPHome 2026.7 y LVGL 9.5.
- Pantalla ILI9341 y táctil XPT2046 en buses SPI separados.
- Wi-Fi, HTTP, MQTT, API cifrada, OTA, caché flash, LDR y parlante.
- Templates `button_grid`, `climate`, `sensor_grid`, `cover` y
  `clock_weather`.
- Navegación, protector, brillo automático, horario nocturno y calibración.

## Integración Home Assistant 0.1.0

- Flujo de configuración gráfico.
- Editor visual en un panel lateral.
- Almacenamiento administrado con historial de diez revisiones.
- Consulta de entidades sin tokens externos.
- Puente nativo de comandos y estados.
- Migración reversible desde automatizaciones temporales.

## Antes de declarar la versión estable

- Probar instalación, actualización y eliminación mediante HACS.
- Validar físicamente la migración y la reversión del puente nativo.
- Completar la entrega directa de configuración hacia la CYD.
- Añadir caracteres españoles a la fuente LVGL, incluida la `ñ`.
- Mejorar la fidelidad visual entre la vista previa y la pantalla real.
- Añadir pruebas dentro de una instancia de Home Assistant aislada.
- Preparar marca e iconos para `home-assistant/brands`.

## Fuera del alcance inmediato

- Diseñador libre de widgets en tiempo de ejecución.
- Vídeo o cámaras en la CYD clásica.
- Uso de microSD sin un caso de uso que justifique memoria y complejidad.
- Encendido automático de equipos peligrosos sin confirmaciones explícitas.

