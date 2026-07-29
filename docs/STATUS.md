# Estado del proyecto

Actualizado: 2026-07-29

## Plataforma validada

- ESP32-2432S028R CYD por COM57.
- ESPHome 2026.7.3 sobre ESP-IDF 5.5.5.
- Pantalla ILI9341 y táctil XPT2046 en buses SPI separados.
- Wi-Fi, HTTP, MQTT, API nativa cifrada, caché flash, reloj SNTP y parlante verificados.

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
- API nativa validada desde un cliente real: descubrimiento de entidades, lectura del LDR y ejecución de sonidos.
- Entidades nativas para Home Assistant: retroiluminación, luz ambiental y cinco botones de sonido.
- Acciones nativas `play_sound`, `update_control` y `reload_ui` disponibles para automatizaciones.
- Las pulsaciones del panel emiten también el evento `esphome.cyd_ui_action` cuando Home Assistant está conectado.
- El encendido del calefactor permanece bloqueado; solo se permite leer y cambiar su objetivo.

## Memoria de referencia

- DRAM estática: 53.412 bytes (29,6 %).
- Firmware con API cifrada, portal cautivo, OTA, MDI, telemetría, selector de dos redes y confirmación del calefactor: 1.552.419 bytes (84,6 % de la partición de aplicación).
- Margen de firmware restante: 16 %. Antes de sumar dependencias grandes debe revisarse nuevamente el tamaño.

## Próximo hito

Validar en uso real el configurador visual v0.1, completar los campos avanzados por dominio y agregar restauración desde el historial.

Pendiente para la próxima carga de firmware: ampliar la fuente de texto LVGL con caracteres españoles, como mínimo `áéíóúüñ¿¡` y sus mayúsculas. Actualmente el editor y el JSON conservan `Baño`, pero la `ñ` se muestra como un cuadro en la CYD.

En paralelo: validar la incorporación del dispositivo a Home Assistant en su red definitiva y decidir cómo alojar allí el configurador y el backend dinámico.

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
- Activación independiente de sonidos de toque, navegación y notificaciones.
- Escala perceptual de volumen y prueba inmediata del valor seleccionado sin guardar previamente.
- Volúmenes independientes para toques, navegación y notificaciones, con silencio general opcional durante el horario nocturno.
- Editor visual con apartado fijo `Configuración` y prueba sonora.
- Lectura LDR actualizada cada segundo y calibración asistida de los extremos de oscuridad y mucha luz desde el editor.
- Telemetría visible del porcentaje de brillo realmente aplicado y del modo activo (`normal`, noche, protector, apagado o tenue).
- Calibración táctil guiada de cuatro puntos, aplicada en ejecución y persistida en la configuración JSON.
- El primer toque tras apagar o atenuar la pantalla se consume exclusivamente para despertarla y no activa el control situado debajo.
- Los cambios de horario nocturno reevalúan inmediatamente el modo de reposo activo, incluso si el panel ya estaba mostrando el protector.
- microSD deliberadamente postergada: exige una capa FATFS externa y compite por los buses SPI disponibles; no aporta valor inmediato al runtime actual.

# Actualización 2026-07-29 — traslado e integración nativa

- La red `CYD UI Setup` aparece automáticamente si el Wi-Fi guardado no está disponible; permite cargar nuevas credenciales sin recompilar.
- `api.reboot_timeout` y `mqtt.reboot_timeout` están desactivados para que la interfaz cacheada siga operativa aunque Home Assistant o el broker no estén presentes.
- El parlante está expuesto mediante cinco botones simples y una acción parametrizada para automatizaciones.
- El LDR se publica como `Luz ambiental` en porcentaje, usando los extremos de calibración guardados en la configuración del dispositivo.
- La retroiluminación aparece como una entidad `light` controlable desde Home Assistant.
- La configuración dinámica de páginas continúa dependiendo, por ahora, del servidor HTTP y del backend MQTT; el firmware conserva en flash la última interfaz válida cuando esos servicios no están disponibles.
- El Home Assistant de destino fue comprobado en modo lectura: versión 2026.7.4, integración ESPHome cargada y Mosquitto broker cargado. No es necesario instalar esas dos piezas para la prueba doméstica.
- Prueba de aislamiento realizada: con servidor JSON, puente y broker LAN detenidos, la API del dispositivo continuó accesible; al restaurar los servicios, todos los canales volvieron a estar disponibles.
- Firmware final de traslado cargado: selecciona automáticamente `ServiCell` o `Red_IOT` desde secretos privados.
- Portal de recuperación simplificado a `CYD UI Setup` / `12345678`; sus datos aparecen en la pantalla cuando se activa.
- Dos automatizaciones nativas instaladas en Home Assistant para comandos y sincronización de estados sin depender de la PC del taller.
- Ruta nativa de comando validada con `switch.sonoff_1001327309_2`; no se accionó el calefactor.
- El límite compartido de descarga HTTP y caché flash se amplió de 8 a 16 KiB después de detectar correctamente el crecimiento de la configuración a 8.407 bytes.
- `Guardar y aplicar` actualiza ahora la pantalla y regenera las automatizaciones nativas de Home Assistant en una sola operación; los fallos se informan por separado.
- La activación del calefactor requiere dos toques dentro de tres segundos; apagarlo requiere uno. La generación solo alterna entre `off` y `heat` y no se probó la activación fuera de casa.

# Actualización 2026-07-29 — distribución mediante HACS

- Creado el bootstrap de una integración personalizada `cyd_ui` compatible con la estructura exigida por HACS.
- La integración dispone de flujo de alta gráfico, traducciones en español e inglés y un panel administrativo inicial en la barra lateral.
- El recurso web y el comando WebSocket de diagnóstico quedan encapsulados dentro de `custom_components/cyd_ui`.
- Implementado almacenamiento administrado y atómico para la configuración, con historial acotado a diez revisiones.
- Implementadas operaciones WebSocket administrativas para leer/guardar el proyecto y consultar entidades sin token externo.
- El editor visual ya puede ejecutarse dentro del panel de Home Assistant, importar el proyecto actual y guardar revisiones; la aplicación directa a la CYD continúa deshabilitada hasta implementar el puente nativo definitivo.
- La integración todavía no se instala en el Home Assistant doméstico: primero debe recibir el editor real, almacenamiento administrado y pruebas de carga/descarga.
- Antes de publicarla se deben definir la URL y el propietario definitivos del repositorio, reemplazando los marcadores `OWNER` del manifiesto.
