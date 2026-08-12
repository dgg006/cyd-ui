# Estado del proyecto

## Actualización 2026-08-12 — carátula multimedia compacta

- CYD UI v0.7.0 implementa la opción visual B: carátula compacta de 72 × 72,
  metadatos a la derecha y cinco controles compactos en la fila inferior.
- La CYD descarga JPEG bajo demanda, lo decodifica a RGB565 y conserva el
  marcador neutro cuando la imagen falta o falla.
- Los proyectos multimedia guardados con diez controles se migran a once de
  forma automática y atómica, sin sobrescribir el resto de la configuración.
- El puente de laboratorio puede retransmitir la imagen desde Home Assistant a
  la red local de la pantalla para probarla fuera de casa.
- Firmware compilado y cargado por OTA. Validación: 51 pruebas automáticas,
  DRAM estática 54.068 bytes (29,9 %) y firmware 1.566.419 bytes (85,4 % de la
  partición de aplicación).

## Actualización 2026-08-12 — agenda visual de recordatorios

- CYD UI v0.6.0 permite elegir fecha y hora en el mismo centro de recordatorios,
  consultar los avisos pendientes y cancelarlos sin escribir YAML.
- La agenda se conserva en el almacenamiento administrado por Home Assistant y
  reconstruye sus temporizadores después de cada reinicio.
- Si la pantalla está desconectada al vencer el horario, la integración conserva
  el aviso y reintenta la entrega cada minuto.
- El puente de laboratorio incorpora un canal Home Assistant → CYD para probar
  recordatorios programados desde el taller sin modificar el firmware.
- Interfaz comprobada en escritorio y a 375 px de ancho. Validación: 49 pruebas
  automáticas superadas.

## Actualización 2026-08-11 — alarmas, LED y multimedia confiable

- CYD UI v0.5.0 incorpora la acción visual `cyd_ui.show_reminder`, con un
  formulario apto para usuarios comunes y automatizaciones de Home Assistant.
- Los recordatorios admiten sonido único, modo silencioso o alarma repetitiva
  durante 10 a 120 segundos. La alarma se detiene al aceptar y puede ofrecer
  **APLAZAR** por 5, 10 o 15 minutos.
- El LED de notificaciones conserva durante dos segundos el color solicitado y
  después recupera automáticamente el estado de conexión; el supervisor ya no
  pisa inmediatamente una notificación.
- La pantalla Multimedia limpia título, artista, emisora y carátula cuando el
  reproductor queda detenido o inactivo. Los textos auxiliares antiguos ya no
  se reutilizan si son anteriores al último cambio del reproductor.
- Firmware compilado y cargado por USB en COM57. Verificación: 48 pruebas
  automáticas, DRAM estática 53.812 bytes (29,8 %) y firmware 1.526.995 bytes
  (83,2 % de la partición de aplicación).

## Actualización 2026-08-10 — recordatorios y controles multimedia

- La integración CYD UI v0.4.0 incorpora un centro de recordatorios en su panel:
  permite escribir título y mensaje, elegir prioridad y sonido, enviar el aviso
  persistente a la pantalla y retirarlo manualmente.
- El formulario fue validado tanto en escritorio como en un ancho de celular de
  375 px, sin desplazamiento horizontal ni controles inaccesibles.
- La pantalla Multimedia reemplaza los textos de transporte por iconos MDI para
  pista anterior/siguiente, play/pausa y volumen. Los metadatos conservan la
  fuente de texto con caracteres españoles.
- Firmware compilado y cargado por USB en COM57. Validación: 46 pruebas
  automáticas, DRAM estática 53.612 bytes (29,7 %) y firmware 1.525.071 bytes
  (83,1 % de la partición de aplicación).

## Multimedia (en desarrollo)

- Template `media/full_controls` implementado y compilado para la CYD.
- Incluye selector de hasta tres reproductores, metadatos estándar, pista anterior/siguiente, play/pausa y volumen.
- Admite una fuente alternativa para título, artista y emisora cuando un reproductor no publica atributos estándar.
- Carátula compacta implementada con descarga JPEG bajo demanda,
  redimensionado a 72 × 72 y marcador neutro ante errores.

Actualizado: 2026-08-08

## Actualización 2026-08-08 — pasada visual y LED de notificaciones

- Firmware compilado y cargado por USB en COM57; el arranque de ESPHome y del
  `ui_engine` fue verificado por el registro serie.
- El modo claro ahora usa una superficie ligeramente gris y contraste calculado
  para valores, iconos y textos. Los colores blancos o muy claros ya no quedan
  invisibles sobre tarjetas claras.
- Los botones activos eligen automáticamente texto claro u oscuro según el color
  de fondo configurado.
- El indicador de conexión en pantalla se redujo de 8 × 8 a 4 × 4 píxeles.
- El protector de pantalla usa una hora de 60 px y una fecha de 18 px. El icono y
  el texto meteorológico se miden y centran como un único grupo.
- El LED RGB trasero se expone como la entidad **LED de notificaciones**, con
  color, brillo y efectos de pulso controlables desde Home Assistant. Mientras la
  conexión es saludable, el control manual ya no es anulado por la supervisión
  periódica; una falla de Wi-Fi o Home Assistant conserva prioridad visual.
- Validación: configuración ESPHome correcta, 42 pruebas automáticas superadas,
  DRAM estática 53.420 bytes (29,6 %) y firmware 1.513.575 bytes (82,5 %).

## Actualización 2026-08-05 — laboratorio remoto por API nativa

- Implementado `CYD Lab Gateway`: conecta la pantalla presente en la red del
  taller con el Home Assistant doméstico a través de WireGuard.
- Ambos enlaces salen desde la PC, por lo que Home Assistant no necesita una
  ruta inversa hacia la red `192.168.31.0/24`.
- El gateway usa la API cifrada de ESPHome, la misma configuración almacenada
  por la integración HACS y el mismo modelo de traducción de acciones/estados
  que el puente nativo de producción. No restaura MQTT ni modifica el firmware.
- Validados en vivo: Home Assistant `192.168.68.77:8123`, CYD
  `192.168.31.150:6053`, revisión 47, 8 páginas y 34 controles.
- La configuración se revisa automáticamente cada cinco segundos y los cambios
  de estado llegan mediante WebSocket en tiempo real.
- Por seguridad, el laboratorio bloquea el encendido/apagado del calefactor;
  los ajustes de temperatura y los demás controles conservan su contrato.
- Se agregó el iniciador `Iniciar puente CYD.cmd` y protección contra dos
  instancias simultáneas.

## Actualización 2026-08-03 — sincronización, móvil e idioma

- El firmware recibió una fuente Roboto con los caracteres españoles necesarios; `Baño` y la letra `ñ` quedaron validados físicamente en la CYD.
- Se separaron los sonidos de interfaz de las notificaciones de Home Assistant. Desactivar los toques locales ya no bloquea una notificación externa, y cada grupo conserva su volumen propio.
- El editor recibió una adaptación para teléfono: paneles de una columna, controles más grandes y selección buscable de entidades e iconos sin depender de listas desplegables nativas.
- Se implementó la señal `esphome.cyd_ui_ready`: cuando la CYD termina de reconectarse a Home Assistant, el puente nativo vuelve a enviar la última configuración guardada y los estados actuales. Esto elimina la necesidad prevista de pulsar **Guardar y aplicar** tras un reinicio.
- Firmware compilado y cargado por USB en COM57. La validación completa de la resincronización queda pendiente para la próxima conexión de la CYD a la red doméstica y a Home Assistant.
- La vista previa del editor fue alineada con las medidas LVGL del reloj y ahora dispone de representaciones específicas para las carátulas de climatización y cortina. La siguiente pasada visual debe cubrir sensores y cuadrículas, siempre contrastándolas con la CYD real.

## Pausa de desarrollo — prueba doméstica

El desarrollo queda pausado hasta la renovación de la cuota semanal. Durante esta pausa no se modificará ni cargará firmware y tampoco se harán cambios en Home Assistant.

### Resultado general de la prueba en casa

- La pantalla se conectó correctamente a la red Wi-Fi doméstica.
- Home Assistant detectó el dispositivo rápidamente.
- Los botones pudieron controlar sus entidades.

### Pendientes detectados

1. **Sincronización inicial incompleta (prioridad alta).**
   Al iniciar el panel en la red doméstica, algunos botones funcionaban, pero la sincronización no quedaba completamente correcta hasta entrar al editor y pulsar **Guardar y aplicar**. El comportamiento esperado es que, al arrancar o reconectarse, el panel reciba automáticamente la última configuración guardada y una instantánea completa de los estados, sin intervención manual. Debe revisarse el orden de conexión, registro de servicios y envío inicial de configuración/estados.

2. **Editor poco amigable en teléfonos (prioridad alta).**
   La interfaz necesita una adaptación específica para pantallas pequeñas. Desde el celular, algunos selectores —especialmente los de entidades e iconos— no despliegan sus opciones correctamente. Deben funcionar mediante toque, permitir búsqueda y mantener un diseño cómodo en una pantalla angosta.

3. **Sonidos de interfaz y notificaciones no son independientes (prioridad media).**
   Al desactivar el sonido desde Configuración también quedan silenciadas las notificaciones sonoras solicitadas desde Home Assistant. Deben separarse, como mínimo, el sonido de interacción local y el sonido de notificaciones externas, con controles independientes y una política nocturna explícita.

Estos puntos quedan registrados para la próxima etapa. No invalidan la prueba: la conexión Wi-Fi, el descubrimiento por Home Assistant y el control básico quedaron confirmados.

## LED RGB y conectividad

- Implementado como indicador de conectividad: rojo sin Wi-Fi, amarillo con
  Wi-Fi pero sin Home Assistant, azul durante el portal de configuración y
  apagado durante el funcionamiento normal.
- Expuesto también como luz RGB de Home Assistant para notificaciones manuales,
  con efectos de pulso. Los estados de falla tienen prioridad sobre el uso
  decorativo o de notificación.
- La interfaz LVGL mantiene un indicador equivalente de 4 × 4 píxeles y muestra
  texto únicamente cuando existe un problema de conexión.

## Pendiente de diseño: temas visuales

- Ofrecer modo claro u oscuro y una selección acotada de hasta cinco colores de acento.
- El acento afecta navegación, bordes, selección y detalles decorativos; no cambia colores semánticos de estado ni permite elegir colores libres por control.

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
- Catálogo reducido de 54 iconos MDI con estados activo/inactivo; compilación
  verificada y pendiente de validación física en la próxima carga.

## Templates verificados físicamente

- `button_grid`: 2, 4 y 6 botones.
- `climate`: temperatura actual, objetivo y ajuste incremental.
- `clock_weather`: reloj y clima como protector de pantalla.
- `sensor_grid`: cuatro valores con unidad y precisión.
- `cover`: posición, apertura/cierre total y pasos de 10 %.
- `media`: selector de reproductor, metadatos, reproducción y volumen.
- Overlay de recordatorios: título, mensaje, prioridad, sonido opcional y confirmación obligatoria.

## Integración de laboratorio

- Backend bidireccional con Home Assistant mediante HTTPS/WebSocket y MQTT.
- Cambios externos reflejados en tiempo real.
- Sonidos `attention`, `notification`, `success`, `warning` y `error`.
- Evento de Home Assistant `cyd_ui_sound` validado de extremo a extremo.
- API nativa validada desde un cliente real: descubrimiento de entidades, lectura del LDR y ejecución de sonidos.
- Entidades nativas para Home Assistant: retroiluminación, luz ambiental y cinco botones de sonido.
- Acciones nativas de sonido, actualización, recarga y recordatorios disponibles para automatizaciones.
- Las pulsaciones del panel emiten también el evento `esphome.cyd_ui_action` cuando Home Assistant está conectado.
- El encendido del calefactor permanece bloqueado; solo se permite leer y cambiar su objetivo.

## Memoria de referencia

- DRAM estática: 53.612 bytes (29,7 %).
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
- El puente nativo de eventos y estados está codificado y probado, pero no se registra todavía: primero debe desactivarse de forma transaccional el puente de automatizaciones para evitar órdenes duplicadas.
- Preparada una migración reversible desde el panel administrativo: registra el estado previo de las automatizaciones, transfiere primero la propiedad de comandos y permite volver atrás. No fue ejecutada en el Home Assistant real.
- La integración todavía no se instala en el Home Assistant doméstico: primero debe recibir el editor real, almacenamiento administrado y pruebas de carga/descarga.
- Antes de publicarla se deben definir la URL y el propietario definitivos del repositorio, reemplazando los marcadores `OWNER` del manifiesto.
