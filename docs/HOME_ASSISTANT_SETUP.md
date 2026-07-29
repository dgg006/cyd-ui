# Instalación en Home Assistant y traslado entre redes

Actualizado: 2026-07-29

## Qué funciona directamente con Home Assistant

El firmware expone por la API nativa cifrada de ESPHome:

- `Backlight`: encendido y nivel de brillo de la pantalla.
- `Luz ambiental`: lectura porcentual del LDR frontal.
- Cinco botones de sonido: atención, notificación, éxito, advertencia y error.
- Acción `esphome.cyd_ui_play_sound` con el argumento `sound`.
- Acción `esphome.cyd_ui_update_control` para actualizar un control genérico.
- Acción `esphome.cyd_ui_reload_ui` para solicitar una recarga de configuración.
- Evento `esphome.cyd_ui_action` con `control_id` y `action` cuando se toca un control.

Los nombres exactos de las entidades pueden recibir un prefijo de dispositivo al incorporarse a Home Assistant.

## Primera conexión en una red nueva

1. Encender la CYD y esperar aproximadamente 90 segundos.
2. Si no reconoce la red guardada, buscar desde el teléfono la red Wi-Fi `CYD UI Setup`.
3. Conectarse usando la contraseña privada guardada en `secrets.yaml` como `fallback_ap_password`.
4. Si el portal no se abre solo, visitar `http://192.168.4.1`.
5. Elegir la red Wi-Fi de la casa y escribir su contraseña.
6. Esperar a que la red temporal desaparezca y la CYD se conecte a la red elegida.

La interfaz anterior se conserva en flash. La ausencia del servidor HTTP o del broker MQTT no deja la pantalla en blanco ni provoca reinicios.

Este comportamiento fue comprobado en laboratorio deteniendo simultáneamente el servidor JSON, el puente y el broker accesible por LAN: la API del dispositivo permaneció operativa y los servicios se reconectaron al restaurarlos.

## Incorporación a Home Assistant

El servidor de destino ya fue verificado: Home Assistant 2026.7.4 tiene cargados ESPHome y el complemento Mosquitto broker.

1. Abrir **Ajustes → Dispositivos y servicios**.
2. Esperar el descubrimiento de `CYD UI Lab` y pulsar **Configurar**.
3. Si no aparece, usar **Añadir integración → ESPHome** e introducir `cyd-ui.local`.
4. Cuando lo solicite, copiar la clave `api_encryption_key` del archivo privado `secrets.yaml`.
5. Habilitar la opción que permite al dispositivo ejecutar acciones de Home Assistant si se desea recibir `esphome.cyd_ui_action`.

## Ejemplos de automatización

Reproducir una notificación:

```yaml
action:
  - action: esphome.cyd_ui_play_sound
    data:
      sound: notification
```

Sonidos admitidos:

- `attention`
- `notification`
- `success`
- `warning`
- `error`

También es posible usar los botones del dispositivo con una acción `button.press`; esto resulta cómodo desde la interfaz gráfica de automatizaciones.

Escuchar pulsaciones genéricas del panel:

```yaml
triggers:
  - trigger: event
    event_type: esphome.cyd_ui_action
    event_data:
      control_id: living
actions:
  - action: light.toggle
    target:
      entity_id: light.living
```

El ejemplo es ilustrativo: el firmware solo emite un identificador opaco y no conoce la entidad real.

## Qué requiere todavía el backend dinámico

La API nativa cubre el hardware fijo del panel y ofrece acciones genéricas. Las páginas configurables, el mapa hacia entidades arbitrarias y la sincronización automática de todos sus estados continúan usando:

- `configurator/server.py` para editar `ui.json` y `backend-map.json`;
- el servidor HTTP local para entregar `ui.json`;
- MQTT y `tools/ha_bridge.py` para traducir estados y comandos dinámicos.

Por eso, en una prueba doméstica sin esos servicios, la CYD mostrará la última interfaz guardada y Home Assistant podrá usar LDR, brillo y sonidos, pero los botones dinámicos no controlarán entidades hasta trasladar o reemplazar el backend.

## Camino previsto para la integración completa

1. Validar primero la API nativa y las entidades fijas en la red doméstica.
2. Empaquetar configurador, servidor JSON y puente como un servicio instalable junto a Home Assistant.
3. Mantener `ui.json` y `backend-map.json` como contratos independientes del editor.
4. Evaluar una integración personalizada de Home Assistant cuando el contrato sea estable; no introducirla prematuramente en el firmware.

## Recuperación

- Si cambia el Wi-Fi: usar `CYD UI Setup` y el portal `192.168.4.1`.
- Si Home Assistant no descubre la placa: comprobar que el teléfono, Home Assistant y la CYD estén en la misma red y probar con la IP asignada por el router.
- Si falta el backend: la interfaz cacheada sigue visible; las entidades nativas continúan disponibles.
- Si una actualización falla: la partición OTA anterior queda como respaldo del mecanismo de ESPHome.
