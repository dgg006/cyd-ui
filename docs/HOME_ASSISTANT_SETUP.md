# Instalación en Home Assistant y traslado entre redes

Actualizado: 2026-07-29

## Estado actual

El firmware ya contiene las dos redes de desarrollo autorizadas:

- `ServiCell`, para las pruebas en el taller.
- `Red_IOT`, para la prueba doméstica.

Las contraseñas se leen desde `secrets.yaml`; no están escritas en el YAML público ni se incorporan a la documentación. Al encender, ESPHome elige automáticamente la red disponible.

Si ninguna red funciona, la pantalla muestra los datos del portal de emergencia:

```text
Red: CYD UI Setup
Clave: 12345678
Dirección: 192.168.4.1
```

El portal es solo un mecanismo de recuperación. Para la primera prueba en casa no debería ser necesario.

## Primera prueba real en casa

1. Conectar la CYD a la alimentación y esperar entre 30 y 90 segundos.
2. Abrir Home Assistant en el teléfono.
3. Ir a **Ajustes → Dispositivos y servicios**.
4. Si aparece el dispositivo descubierto `CYD UI Lab`, pulsar **Configurar**.
5. Si no aparece, pulsar **Añadir integración → ESPHome** e introducir `cyd-ui.local`.
6. Cuando Home Assistant solicite la clave de cifrado, usar `api_encryption_key` de `secrets.yaml`.
7. Activar **Permitir que el dispositivo realice acciones de Home Assistant**. Esta autorización es necesaria para que las pulsaciones de la pantalla lleguen a las automatizaciones.
8. Esperar hasta un minuto después de completar la integración.

Resultado esperado:

- La entidad `Backlight` controla encendido y brillo.
- `Luz ambiental` muestra el LDR frontal.
- Los cinco botones de sonido reproducen sus avisos.
- El botón Living controla `switch.sonoff_1001327309_2`.
- Los estados configurados se actualizan en la pantalla.
- Los botones `-` y `+` del calefactor pueden modificar su temperatura objetivo.
- Ninguna automatización instalada puede encender el calefactor.

## Puente nativo instalado

Se instalaron en Home Assistant dos automatizaciones temporales:

- `CYD UI - Ejecutar controles`: recibe `esphome.cyd_ui_action` y ejecuta solamente las acciones autorizadas en el mapa actual.
- `CYD UI - Sincronizar estados`: envía a la pantalla los estados actuales al iniciar Home Assistant, cuando cambia una entidad y cada minuto como recuperación.

Este puente permite la prueba doméstica completa sin ejecutar en la PC del taller el broker, el servidor JSON ni `ha_bridge.py`. Se generó desde `config/backend-map.json` con:

```powershell
py -3.13 tools\install_ha_native_bridge.py --install
```

El encendido del calefactor no forma parte de las acciones generadas. Solo se leen sus valores y se permite cambiar la temperatura objetivo.

## Configurador visual

El editor de `http://127.0.0.1:8125` todavía es una herramienta local de desarrollo. No está alojado dentro de Home Assistant. Esta limitación no impide la prueba de esta noche: la CYD conserva en flash la última interfaz válida y las automatizaciones nativas conectan esa interfaz con Home Assistant.

Convertir el editor en un panel o complemento instalable de Home Assistant es un hito posterior. La configuración actual no se perderá por apagar o trasladar la placa.

## Entidades y acciones nativas

El firmware expone mediante la API cifrada de ESPHome:

- `Backlight`.
- `Luz ambiental`.
- Cinco botones de sonido: atención, notificación, éxito, advertencia y error.
- Acción `esphome.cyd_ui_play_sound` con el argumento `sound`.
- Acción `esphome.cyd_ui_update_control` para actualizar un control genérico.
- Acción `esphome.cyd_ui_reload_ui` para solicitar una recarga.
- Acción `esphome.cyd_ui_show_reminder` para mostrar un aviso persistente con
  `reminder_id`, `title`, `message`, `level` y `sound`.
- Acción `esphome.cyd_ui_dismiss_reminder` para retirar un aviso por su identificador.
- Evento `esphome.cyd_ui_action` con `control_id` y `action` al tocar un control.

Los nombres de servicios pueden incluir el nombre del dispositivo cuando Home Assistant los registra.

Ejemplo de una automatización o script:

```yaml
action: cyd_ui.show_reminder
data:
  reminder_id: medicacion_noche
  title: Recordatorio
  message: Tomar la medicación de la noche
  level: reminder
  sound_mode: alarm
  alarm_duration: 120
  snooze_minutes: 10
```

El aviso enciende la pantalla, queda por encima de cualquier página y no se
retira hasta pulsar **ACEPTAR**. La confirmación emite `esphome.cyd_ui_action`
con el identificador del recordatorio y `action: acknowledge`.

El panel lateral **CYD UI → Recordatorios** permite realizar lo mismo sin YAML.
Además de enviar un aviso inmediatamente, puede programarlo una vez, todos los
días, de lunes a viernes, semanalmente o en días específicos. La agenda queda
guardada en Home Assistant y cada entrada puede cancelarse desde el mismo panel.

## Recuperación

- Si la CYD muestra `CONFIGURAR WI-FI`, conectarse a `CYD UI Setup` con `12345678` y abrir `http://192.168.4.1`.
- Si Home Assistant no descubre la placa, confirmar que Home Assistant y la CYD alcanzan la misma red y probar con la IP que le asignó el router.
- Si `cyd-ui.local` no resuelve entre VLAN o redes separadas, usar esa IP directamente.
- Si los controles aparecen naranjas al principio, esperar un minuto: indica que todavía no llegó la primera sincronización.
- Si los botones físicos no ejecutan acciones, revisar que se haya autorizado al dispositivo a realizar acciones de Home Assistant.
- La falta del backend de desarrollo no borra la interfaz: se usa la copia validada de la caché flash.

## Verificación realizada antes del traslado

- Firmware compilado y cargado por USB.
- Conexión a la red del taller recuperada después de reiniciar.
- API cifrada accesible en el puerto 6053.
- Siete entidades y tres acciones nativas enumeradas correctamente.
- Automatizaciones instaladas y activas en Home Assistant.
- Ruta completa de comando probada con el control Living: encendido, confirmación de estado y restauración a apagado.
- No se accionó el calefactor.
