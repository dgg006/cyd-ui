# CYD UI Engine

Runtime declarativo para interfaces LVGL, desarrollado inicialmente para la ESP32-2432S028R CYD y ESPHome.

## Principios

1. La interfaz habitual se reconfigura sin recompilar el motor.
2. El firmware no conoce entidades ni decisiones de Home Assistant.
3. Los templates crean una cantidad fija de widgets y actualizan sus propiedades.
4. Una configuración nueva reemplaza la UI activa solo después de validarse por completo.
5. Una acción táctil requiere confirmación del backend antes de cambiar el estado mostrado.

## Estado actual

- Pantalla, touch, Wi-Fi, MQTT y API nativa cifrada verificados en hardware.
- `button_grid` con seis botones configurable mediante JSON.
- Configuración remota por HTTP con caché flash y respaldo embebido.
- Acciones y estados en tiempo real mediante MQTT.
- Integración bidireccional real con Home Assistant validada mediante un mapa externo de controles.
- Proyecto Arduino de validación conservado intacto.
- Configurador visual local v0.1 para páginas, controles y asociaciones con Home Assistant.
- Catálogo compacto de iconos MDI configurable sin recompilar mientras el icono ya esté incluido.
- Configuración general desde el editor: brillo PWM, LDR, reposo, horario nocturno y volumen/sonidos.
- Integración directa con Home Assistant para brillo, LDR y sonidos, sin depender del puente MQTT.
- Portal Wi-Fi de emergencia y OTA preparados para trasladar el panel entre redes.
- Puente nativo temporal instalado en Home Assistant para que los controles y estados actuales funcionen sin la PC de desarrollo.
- Selección automática entre las redes autorizadas y datos del portal de emergencia visibles en la propia CYD.

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
esphome config cyd-ui.yaml
esphome compile cyd-ui.yaml
esphome upload cyd-ui.yaml --device COM57
```

La instalación en Home Assistant y el traslado entre redes están explicados en
[`docs/HOME_ASSISTANT_SETUP.md`](docs/HOME_ASSISTANT_SETUP.md).

La futura integración instalable mediante HACS comenzó en
[`custom_components/cyd_ui`](custom_components/cyd_ui); su alcance y estado están
documentados en [`docs/HACS_INTEGRATION.md`](docs/HACS_INTEGRATION.md).

El puente nativo temporal se genera desde el mapa actual con:

```powershell
py -3.13 tools\install_ha_native_bridge.py --install
```
