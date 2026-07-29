# CYD UI Engine

Runtime declarativo para interfaces LVGL, desarrollado inicialmente para la ESP32-2432S028R CYD y ESPHome.

## Principios

1. La interfaz habitual se reconfigura sin recompilar el motor.
2. El firmware no conoce entidades ni decisiones de Home Assistant.
3. Los templates crean una cantidad fija de widgets y actualizan sus propiedades.
4. Una configuración nueva reemplaza la UI activa solo después de validarse por completo.
5. Una acción táctil requiere confirmación del backend antes de cambiar el estado mostrado.

## Estado actual

- Pantalla, touch, Wi-Fi y MQTT verificados en hardware.
- `button_grid` con seis botones configurable mediante JSON.
- Configuración remota por HTTP con caché flash y respaldo embebido.
- Acciones y estados en tiempo real mediante MQTT.
- Integración bidireccional real con Home Assistant validada mediante un mapa externo de controles.
- Proyecto Arduino de validación conservado intacto.
- Configurador visual local v0.1 para páginas, controles y asociaciones con Home Assistant.

## Configurador visual

```powershell
py -3.13 configurator\server.py
```

Abrir `http://127.0.0.1:8125`. Antes de guardar valida el contrato, conserva una copia recuperable y, al finalizar, ordena la recarga de la CYD.

Para iniciar en conjunto el broker, servidor de configuración, puente de Home Assistant y configurador:

```powershell
powershell -ExecutionPolicy Bypass -File tools\start_development.ps1
```

## Comandos locales

```powershell
$env:ESPHOME_ESP_IDF_PREFIX='C:\ESPHomeCache\idf'
py -3.13 -m esphome config cyd-ui.yaml
py -3.13 -m esphome compile cyd-ui.yaml
py -3.13 -m esphome upload cyd-ui.yaml --device COM57
```
