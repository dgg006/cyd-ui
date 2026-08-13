# CYD UI Engine

Runtime declarativo para interfaces LVGL, desarrollado inicialmente para la ESP32-2432S028R CYD y ESPHome.

## Desarrollo remoto desde el trabajo

`tools/start_lab_gateway.ps1` conecta una CYD presente en la red local con el
Home Assistant de casa a través de WireGuard. Usa la API nativa de ESPHome: no
requiere MQTT, no cambia el firmware y no interviene cuando la pantalla vuelve
a casa.

Con WireGuard activo y la pantalla encendida, ejecutar:

```powershell
powershell -ExecutionPolicy Bypass -File tools/start_lab_gateway.ps1
```

El puente carga automáticamente el proyecto guardado por la integración CYD UI,
sincroniza estados en tiempo real y traduce las pulsaciones a servicios de Home
Assistant. Por seguridad, el encendido y apagado remoto de climatización queda
bloqueado en modo laboratorio.

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

### Novedades de v0.5.0

- Recordatorios persistentes con sonido único, alarma repetitiva y aplazado opcional.
- Acción visual `cyd_ui.show_reminder` para automatizaciones sin llamadas ESPHome de bajo nivel.
- LED RGB protegido contra la restauración inmediata del indicador de conexión.
- Metadatos multimedia limpiados al detener el reproductor para no mostrar información antigua.

### Novedades de v0.6.0

- Agenda visual para programar recordatorios con fecha y hora desde el panel.
- Los pendientes sobreviven a reinicios de Home Assistant y pueden cancelarse.
- Si la CYD no está disponible a la hora indicada, la entrega se reintenta automáticamente.
- El puente de laboratorio admite recordatorios enviados desde Home Assistant hacia la CYD local.

### Novedades de v0.7.0

- Multimedia incorpora una carátula compacta de 72 × 72 píxeles descargada bajo demanda.
- La imagen se redimensiona y decodifica en RGB565 sin reservar un framebuffer completo.
- Los proyectos multimedia anteriores se migran automáticamente sin perder páginas ni asociaciones.
- El puente de laboratorio retransmite la carátula cuando Home Assistant y la CYD están en redes distintas.

### Novedades de v0.7.1

- El configurador permite consultar y restaurar las diez versiones anteriores.
- Restaurar nunca destruye la configuración actual: la conserva como una revisión nueva.
- Guardar páginas ya no puede borrar recordatorios ni otros datos auxiliares de la integración.

### Novedades de v0.7.2

- Las carátulas se recortan al centro y se presentan como círculos suavizados.
- Las esquinas usan exactamente el fondo general del tema oscuro o claro para simular
  transparencia sin exigir máscaras ni memoria adicional a la CYD.
- El procesamiento se realiza en Home Assistant o en el puente de laboratorio;
  el firmware continúa descargando un JPEG compacto de 72 × 72.

### Novedades de v0.7.3

- La copia de la configuración en flash se guarda en bloques pequeños y en dos bancos alternados.
- Cambiar entre los temas claro y oscuro ya no exige reservar un bloque contiguo grande de RAM.
- Una interrupción durante el guardado conserva la última copia completa y válida.
- El puente de laboratorio evita aplicar repetidamente una misma revisión.

### Novedades de v0.7.4

- La página multimedia usa un selector compacto de reproductor y una única fila inferior de controles.
- El volumen y su indicador visual quedan debajo de la carátula.
- Canción, artista, emisora y reproductor se limitan a una línea con puntos suspensivos.
- Las fuentes incluyen puntuación y caracteres latinos habituales en metadatos musicales.
- La vista previa del editor reproduce la nueva distribución.

### Novedades de v0.7.5

- El control central usa pausa en reproductores compatibles y stop en radios que no admiten pausa.
- Una acción multimedia rechazada ya no reinicia el puente ni devuelve la pantalla a la primera página.
- La sincronización inicial conserva los metadatos válidos recibidos antes de finalizar la conexión.
- Los metadatos antiguos no reaparecen al iniciar una reproducción nueva sin información propia.

### Novedades de v0.7.6

- Jarvis vuelve a mostrar canción y artista aunque esos textos no hayan cambiado entre dos reproducciones.
- Emisora y carátula validan el conjunto multimedia actual sin provocar recargas masivas.
- El puente de laboratorio obtiene carátulas internas mediante el acceso remoto disponible.

### Novedades de v0.7.7

- El selector multimedia abre una lista real con hasta tres reproductores configurados.
- Al elegir un reproductor, todos los metadatos y controles cambian juntos a esa entidad.
- La barra y el porcentaje de volumen responden inmediatamente al tacto mientras Home Assistant confirma el cambio.

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

Para actualizar los recursos del panel de Home Assistant desde el configurador local:

```powershell
py -3.13 tools\build_ha_frontend.py
```

El puente nativo temporal se genera desde el mapa actual con:

```powershell
py -3.13 tools\install_ha_native_bridge.py --install
```
