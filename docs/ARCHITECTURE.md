# UI Engine

### Runtime declarativo para interfaces embebidas

**Documentación oficial del proyecto**

---

```
██╗   ██╗██╗    ███████╗███╗   ██╗ ██████╗ ██╗███╗   ██╗███████╗
██║   ██║██║    ██╔════╝████╗  ██║██╔════╝ ██║████╗  ██║██╔════╝
██║   ██║██║    █████╗  ██╔██╗ ██║██║  ███╗██║██╔██╗ ██║█████╗
██║   ██║██║    ██╔══╝  ██║╚██╗██║██║   ██║██║██║╚██╗██║██╔══╝
╚██████╔╝██║    ███████╗██║ ╚████║╚██████╔╝██║██║ ╚████║███████╗
 ╚═════╝ ╚═╝    ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚══════╝
```

**Versión de la documentación:** 1.0
**Versión del protocolo/schema descripto:** schema_version 1
**Estado del proyecto:** Implementación funcional validada en hardware — configurador visual pendiente
**Plataforma de referencia inicial:** ESP32-2432S028R ("Cheap Yellow Display", CYD) + ESPHome + LVGL v9
**Licencia propuesta:** A definir (candidatos: MIT, Apache 2.0 — ver §27)
**Autores del diseño:** Delmo (autor y mantenedor del proyecto), con arquitectura co-diseñada mediante discusión técnica entre dos asistentes de IA (Claude, de Anthropic, y un asistente de OpenAI/ChatGPT) actuando como pares de revisión de arquitectura.
**Fecha de este documento:** 28 de julio de 2026
**Idioma:** Español (términos técnicos y nombres de símbolos en inglés, como es convención en la industria del firmware/embedded)

---

## Nota sobre el origen de este documento

Este documento no nace de una sola mente. Nace de un proceso de diseño en el que dos sistemas de IA distintos — cada uno con su propio "estilo" de razonamiento — revisaron, cuestionaron y refinaron iterativamente la misma propuesta arquitectónica, mientras un humano (el autor del proyecto) actuaba como puente, copiando mensajes entre ambos sin intervenir en el contenido técnico. El resultado es una arquitectura que sobrevivió varias rondas de objeciones cruzadas antes de considerarse estable.

Esto se menciona explícitamente porque es relevante para cualquiera que lea este documento en el futuro: las decisiones aquí no son la primera idea que surgió, sino la que quedó en pie después de que ambas partes intentaran activamente encontrarle fallas a la otra. Donde hubo desacuerdo, este documento lo registra — incluyendo las posiciones que perdieron la discusión y por qué.

---

## Historial de versiones de este documento

| Versión | Fecha       | Cambios                                                                 | Autor(es) |
|---------|-------------|--------------------------------------------------------------------------|-----------|
| 0.1     | 2026-07-24  | Primera versión oficial. Consolida toda la discusión de diseño previa al Sprint 1. Ningún código fue escrito todavía; este documento describe una arquitectura *aprobada pero no implementada*. | Delmo, Claude, ChatGPT (co-diseño) |
| 1.0     | 2026-07-28  | Actualización posterior a la validación en hardware. Documenta el runtime real, cinco familias de templates, configuración dinámica, integración con Home Assistant, caché flash, pantalla de reposo, sonido, pruebas y lecciones de implementación. | Delmo y OpenAI/Codex |

**Convención de versionado de este documento:** se usará versionado semántico informal, distinto del `schema_version` del protocolo JSON (que es un entero simple, ver §17). `0.x` indica que el proyecto todavía no tiene una primera implementación funcional (vertical slice). Se pasará a `1.0` cuando el Sprint 1 esté completo, funcionando en hardware real, y este documento haya sido actualizado para reflejar la implementación real (no solo el diseño).

**Nota importante para mantenedores futuros:** cuando el código diverja de este documento — y va a divergir, porque ningún diseño sobrevive intacto el contacto con el hardware real — este documento debe actualizarse en el mismo commit o pull request que el código, no "después". Un documento de arquitectura desactualizado es peor que no tener documento, porque miente con autoridad.

---

## Estado del proyecto

**Fase actual: runtime funcional validado en una CYD real.**

Existe una implementación C++ operativa como `external_component` de ESPHome. La placa de referencia inicializa pantalla, táctil, LVGL, Wi-Fi, MQTT, HTTP, caché flash y sonido. La configuración de páginas se descarga como JSON y puede recargarse sin compilar ni grabar firmware. Las acciones salen como eventos genéricos y un backend externo las traduce a Home Assistant.

Capacidades verificadas físicamente:

- `button_grid` con variantes de 2, 4 y 6 botones.
- Navegación circular entre páginas y conservación del estado al navegar.
- Página de climatización con temperatura actual, objetivo y ajustes incrementales.
- Protector de pantalla con reloj y clima tras un tiempo de inactividad.
- Página de cuatro sensores con unidades, colores y precisión configurables.
- Página de cortina con apertura/cierre total y ajustes relativos de 10 %.
- Notificaciones sonoras cortas, tanto desde herramientas locales como desde eventos de Home Assistant.
- Configuración remota HTTP, recarga por MQTT y respaldo persistente en flash.
- Estados `UNKNOWN`, `VALID` y `STALE_OR_DISCONNECTED`.
- Flujo real panel → MQTT → backend → Home Assistant → confirmación → panel.

Pendientes principales:

- Configurador visual para crear, ordenar y editar páginas sin tocar JSON.
- Empaquetado definitivo del backend de laboratorio.
- Sistema `Theme` centralizado; hoy varios estilos siguen definidos por template.
- Pruebas automatizadas del parser y de migraciones de schema.
- Definición del despliegue final fuera del PC de desarrollo.

---

## Objetivos del proyecto

### Objetivo general

Construir un **runtime declarativo para interfaces gráficas embebidas**, cuya primera implementación corre sobre ESPHome + LVGL en una ESP32-2432S028R, pero cuyo diseño no depende conceptualmente de ninguno de esos dos frameworks ni de Home Assistant como backend.

### Objetivos específicos

1. **Eliminar la necesidad de recompilar firmware para cambiar la interfaz de usuario.** Cambiar qué entidades controla un botón, qué color tiene, qué ícono muestra, o qué páginas existen, debe ser posible editando un archivo de configuración externo (JSON), no el código fuente del dispositivo.

2. **Separar completamente la lógica de presentación de la lógica de negocio.** El firmware no debe saber qué es una `light`, un `climate` o una `scene` de Home Assistant. Solo debe saber que existe un `Control` con un `id`, un `caption`, un `icon`, un `color` y un `state`. La traducción entre "conceptos de Home Assistant" y "controles genéricos" vive fuera del firmware.

3. **Que agregar un nuevo tipo de página (template) sea una tarea aislada.** Escribir un nuevo `PageTemplate` no debería requerir tocar el motor (`ApplicationController`, `ConfigProvider`, `TemplateRegistry`, el parser). Debería ser, idealmente, tan simple como escribir una clase nueva y registrarla.

4. **Que el sistema sea robusto ante fallos de red, configuraciones corruptas, y datos desactualizados**, sin dejar nunca al usuario frente a una pantalla en un estado visual inconsistente o indefinido.

5. **Que el diseño no asuma una única placa ni un único backend.** Aunque la primera implementación es CYD + ESPHome + Home Assistant, ninguna decisión de arquitectura debería impedir, en principio, una segunda implementación sobre otro hardware o backend, reusando el mismo formato de configuración.

### Objetivo explícitamente descartado

**No es un objetivo de este proyecto crear un motor de UI completamente libre o "de propósito general" al estilo de un motor de renderizado web.** Este punto se desarrolla en profundidad en §7 (Filosofía), pero se adelanta aquí porque es una decisión que afecta a todo el resto del documento: el proyecto elige deliberadamente un modelo de **templates predefinidos y configurables**, no de **composición libre de widgets**. Esa restricción es una elección de diseño, no una limitación no considerada.

---

## Alcance

### Dentro del alcance (v1, Sprint 1 y evoluciones directas planificadas)

- Firmware ESPHome con un `external_component` que implementa el UI Engine.
- Un template inicial: `button_grid`, con variantes `two_buttons`, `four_buttons`, `six_buttons`.
- Configuración vía JSON servido por HTTP, con cache local en flash.
- Comunicación bidireccional de eventos vía MQTT (estado hacia el dispositivo, acciones desde el dispositivo).
- Validación estricta de configuración antes de aplicarla a la interfaz visual.
- Manejo de estados de confiabilidad de datos (`UNKNOWN`, `VALID`, `STALE_OR_DISCONNECTED`).
- Documentación del JSON Schema v1 como contrato estable.
- Templates adicionales (`climate`, `media`, `sensors`, `settings`) como evolución directa, no como parte de Sprint 1.

### Fuera de alcance (para v1, y en algunos casos indefinidamente)

- **Editor visual de configuración dentro de Home Assistant.** Se reconoce como el "verdadero desafío de UX" del proyecto (ver §26), pero se considera una capa separada que se construye sobre un motor ya validado, no al mismo tiempo.
- **Composición libre de widgets arbitraria (tipo drag-and-drop sin restricciones).** Explícitamente rechazado como modelo, ver §7.
- **Multi-página con navegación (swipe, tabs) en Sprint 1.** Se documenta como evolución esperada, pero el Sprint 1 se limita a una sola página activa para validar la cadena completa sin superficie de bugs adicional.
- **Soporte oficial para placas sin comunidad de referencia clara.** El proyecto empieza acotado a la CYD; portar a otro hardware es un objetivo de diseño (no depender de esa placa específicamente en la arquitectura core) pero no un compromiso de soporte activo.
- **Autenticación/seguridad de la comunicación HTTP/MQTT más allá de lo que ya provee ESPHome/Home Assistant de forma nativa.** Se asume una red doméstica de confianza razonable; no se diseña un modelo de amenazas contra atacantes en la misma LAN.
- **Internacionalización (i18n) de la interfaz.** Los `caption` viajan como texto plano en el idioma que el usuario configure en HA; no hay sistema de traducciones en el firmware.
- **Un "protocolo formal versionado" con spec independiente del código (ESPHome UI Protocol v1 como documento RFC-like).** Se discutió como visión de largo plazo (ver §14 y §26) pero se decidió explícitamente no invertir en ese formalismo hasta que exista una segunda implementación real que lo necesite.

---

## Filosofía del proyecto

### El problema con "interfaz completamente libre"

La primera pregunta que cualquier arquitectura de UI configurable debe responder es: **¿cuánta libertad le damos a la configuración?** Hay dos extremos posibles.

En un extremo, un motor "de composición libre": el JSON describe una jerarquía arbitraria de widgets (contenedores, botones, sliders, texto, posiciones absolutas o relativas, estilos por widget), similar a cómo funcionaría un motor de renderizado de HTML/CSS reducido. Esto es máximamente flexible, pero tiene costos serios en un dispositivo embebido sin PSRAM:

- El parser tiene que ser un intérprete de layout genérico, no un simple validador de campos.
- La memoria necesaria para representar un árbol arbitrario de widgets no es predecible en tiempo de compilación.
- Cada combinación posible de configuración es, en los hechos, una superficie de bugs distinta — no hay forma de probar exhaustivamente "todas las UIs posibles que un usuario podría configurar".
- El costo de implementación es mucho más alto, y para un proyecto de una sola persona en tiempo libre, ese costo compite directamente con la probabilidad de que el proyecto llegue a un estado usable.

En el otro extremo, el modelo elegido por este proyecto: **templates predefinidos, parametrizables, pero no componibles libremente**. El firmware conoce de antemano un catálogo cerrado de "formas de página" (`ButtonGrid`, `ClimatePage`, etc.), cada una con una cantidad máxima de widgets fija, definida en tiempo de compilación. La configuración JSON no describe *qué* widgets existen — eso ya está decidido por el template — sino *cómo se ven y a qué responden* los widgets que ese template ya trae.

Esta es la analogía correcta con Home Assistant Lovelace, pero con una diferencia importante que vale la pena remarcar: Lovelace en su modo YAML/UI *sí* permite composición relativamente libre de cards. Este proyecto conscientemente **no** persigue ese nivel de libertad. Es más parecido, en espíritu, a elegir un layout de una plantilla de PowerPoint y rellenar los campos, que a diseñar una diapositiva desde cero.

### Por qué esa restricción es una virtud, no una limitación

1. **Memoria predecible.** Si `ButtonGrid` siempre reserva como máximo 6 botones, el firmware sabe exactamente cuánta RAM necesita para esa página, en tiempo de compilación, sin importar qué diga el JSON.
2. **Superficie de bugs acotada.** Hay un número finito de templates, y cada uno se puede probar exhaustivamente con todas sus variantes. No hay una explosión combinatoria de layouts posibles.
3. **El "editor visual" futuro (fuera de alcance en v1, ver §26) se vuelve un problema mucho más simple.** Si las páginas son instancias de templates con parámetros conocidos, un editor de configuración puede generarse casi automáticamente a partir de la introspección de cada template (`accepted_types()`, `min_controls()`, `max_controls()`, `supported_variants()`). Un editor para composición libre de widgets, en cambio, es un problema de UI de por sí complejo (básicamente, reconstruir algo como Figma).
4. **El usuario objetivo no necesita composición libre.** El caso de uso real (paneles de control domótico) tiene un catálogo relativamente chico de "formas de pantalla" que se repiten: grillas de botones, control de clima, reproductor de medios, lista de sensores. No hay evidencia de que un usuario doméstico quiera diseñar layouts arbitrarios; quiere elegir "una pantalla de 4 botones" y decidir qué hace cada botón.

### Filosofía de la frontera con Home Assistant

Un principio que emergió durante el diseño — no como plan inicial, sino como consecuencia de aplicar consistentemente otras decisiones — es que **el firmware no debe saber nada sobre Home Assistant**. No sabe qué es una `light`, no sabe qué es un `entity_id`, no sabe qué es un dominio de HA. Solo entiende:

```
Control { id, type, caption, icon, color, state, meta }
```

Esto tiene una consecuencia importante que se documenta explícitamente porque no es obvia a primera vista: **la traducción entre el mundo de Home Assistant y el mundo del `Control` genérico ocurre enteramente del lado de Home Assistant**, típicamente en una automation o script que arma el JSON de configuración y que traduce eventos de estado de HA hacia el Event Bus MQTT del dispositivo (ver §19).

La consecuencia práctica de este principio es que, si en el futuro se quisiera reemplazar Home Assistant por Node-RED, openHAB, o cualquier otro backend, el firmware **no necesitaría cambiar en absoluto**. Solo cambiaría el componente externo que genera el JSON y publica/consume los tópicos MQTT.

### Filosofía respecto al versionado y la evolución

El proyecto adopta una postura pragmática frente al ideal de "diseñar el protocolo perfecto desde el día uno": se reconoce que pensar en esto como un protocolo reusable por otras implementaciones es valioso como *marco mental* para tomar mejores decisiones de diseño hoy, pero se descarta explícitamente invertir tiempo en formalizar ese protocolo como documento independiente antes de que exista una necesidad real (una segunda implementación) que lo justifique. Ver la discusión completa en §14 y la Idea Descartada correspondiente en §29.

---

## Principios fundamentales

Estos son los principios que deberían guiar cualquier decisión de diseño futura sobre este proyecto. A diferencia de las "reglas arquitectónicas" (§9), que son técnicamente verificables, estos principios son más una guía de criterio.

**P1 — El firmware es ciego al backend.**
Ninguna clase del firmware debe importar, referenciar o asumir conceptos de Home Assistant (`entity_id`, dominios, servicios). Todo lo que el firmware conoce es `Control`, `Page`, `Event`.

**P2 — La configuración describe, no programa.**
El JSON de configuración es un documento declarativo. No contiene lógica, condicionales, ni scripts. Si en algún momento aparece la tentación de meter lógica condicional dentro del JSON ("si la temperatura es mayor a X, mostrar rojo"), esa lógica pertenece al lado que genera el JSON (Home Assistant), no al formato de configuración.

**P3 — Nunca dejar la interfaz en un estado a medio construir.**
Cualquier cambio de configuración se aplica de forma atómica: o se aplica completo y validado, o no se aplica y se mantiene el estado anterior. Nunca hay un estado intermedio visible al usuario.

**P4 — Preferir simple-y-correcto sobre elegante-y-especulativo.**
Cada capa de abstracción que se agrega al diseño debe justificar su costo (en RAM, en flash, en tiempo de desarrollo) contra un beneficio concreto, no contra un beneficio hipotético de "por si en el futuro...". Este principio fue explícitamente el criterio usado para decidir qué entraba en Sprint 1 y qué quedaba documentado-pero-no-implementado (ver §9, regla R7, y la discusión en §13).

**P5 — La confiabilidad del dato es first-class, no un detalle visual.**
Un control que muestra un estado desactualizado como si fuera actual es peor que un control que muestra explícitamente "no sé". El sistema de `ControlState` (§22) existe para que ningún template pueda, por descuido, mostrar un dato viejo como si fuera fresco.

**P6 — Un template no conoce a otro template, ni al motor.**
Cada `PageTemplate` es una unidad aislada. No debe haber comunicación directa entre templates, ni un template debe necesitar saber cómo funciona `ApplicationController` o `ConfigProvider` internamente. Toda la comunicación pasa por las interfaces definidas (`Control`, `ControlUpdate`, `Theme`).

**P7 — Nada se cachea de forma ambigua.**
Cualquier dato que se persiste (en flash) debe llevar consigo la información necesaria para saber si sigue siendo válido (`schema_version`, `checksum`, `timestamp`). Nunca se asume que un dato cacheado es válido sin verificarlo.

---

## Reglas arquitectónicas

Estas son reglas técnicas concretas, verificables en una revisión de código. Cualquier pull request que las viole debería ser rechazado o, como mínimo, discutido explícitamente antes de aceptarse.

**R1. El motor no conoce clases de template concretas.**
`TemplateRegistry` solo conoce nombres de string (`"button_grid"`) mapeados a factories (`std::function` o puntero a función que devuelve `std::unique_ptr<PageTemplate>`). Está prohibido que `ApplicationController`, el parser, o cualquier clase del motor tengan un `if (template_name == "button_grid")` o un `switch` sobre nombres de template. Agregar un template nuevo debe ser posible sin tocar ninguna línea fuera de la clase del template nuevo y su registro.

**R2. Los widgets se crean una sola vez, nunca se destruyen en runtime.**
`PageTemplate::create()` se llama exactamente una vez por instancia de template activa, y crea el número máximo de widgets que ese template soporta (`max_controls()`). Cambios de configuración posteriores solo modifican propiedades de esos widgets ya existentes (a través de `apply()` y `update_control()`), nunca crean o destruyen widgets de LVGL. Esta regla existe por dos razones: evitar fragmentación de memoria en un dispositivo sin PSRAM, y evitar una clase entera de bugs de ciclo de vida de LVGL (use-after-free de widgets, referencias colgantes).

**R3. Solo se instancian los templates que la configuración activa usa.**
El firmware no pre-crea todos los templates del registry al boot — eso agotaría la RAM disponible en una placa sin PSRAM apenas se agreguen dos o tres templates. Solo se instancia (vía la factory) el/los template(s) que la `UIConfig` validada efectivamente referencia.

**R4. Ninguna clase de template, ni el parser, ni el motor, importan símbolos o tipos de Home Assistant.**
Es la traducción a nivel de código del Principio P1. Ni siquiera como comentario debería aparecer `entity_id` en el código del firmware — el campo se llama `id`, es un string opaco.

**R5. Toda configuración nueva se valida completa antes de tocar cualquier widget existente.**
El pipeline es `Parse → Validate → Resolve → Ready`. Ninguna de las tres primeras etapas debe tener efectos secundarios sobre el estado visual actual. Solo cuando el objeto `UIConfig` completo llega a `Ready` (validado y con recursos resueltos), `ApplicationController` autoriza el swap hacia el runtime activo. Si cualquier etapa falla, el estado visual anterior permanece sin cambios y el error se loguea.

**R6. Los objetos de configuración son inmutables después de `Resolve()`.**
Un `PageConfig` o `Control` resuelto no cambia sus campos de definición (`id`, `type`, `caption` original, recursos resueltos) durante su ciclo de vida. El único canal de mutación posterior es `ControlUpdate`, aplicado vía `update_control()`, que actualiza exclusivamente propiedades visuales dinámicas (estado, valor, visibilidad, habilitado), nunca la definición del control.

**R7. Ninguna abstracción se implementa antes de tener un caso de uso concreto que la necesite.**
Ejemplos explícitos de esta regla aplicada en este proyecto: `MqttConfigProvider` está diseñado (la interfaz `ConfigProvider` lo permite) pero no se implementa en Sprint 1 porque no hay un caso de uso real todavía. El sistema de `Theme` está previsto en la firma de `create()` pero no implementado. La máquina de estados completa de 5 valores para `ControlState` se documenta como evolución (§22) pero Sprint 1 usa una versión de 3 valores. Esta regla es la aplicación directa del Principio P4.

**R8. La semántica visual de los estados de confiabilidad vive en `Theme`, nunca en un template individual.**
Ningún `PageTemplate::update_control()` debe decidir por sí mismo "si el estado es `STALE_OR_DISCONNECTED`, pintar de gris". Esa decisión es responsabilidad de `Theme::apply_state()` (aunque `Theme` en Sprint 1 tenga una implementación mínima hardcodeada). Esto garantiza que todos los templates se vean consistentes entre sí sin coordinación manual.

**R9. El cache en flash no toma decisiones, solo persiste y recupera.**
`FlashStorage` es una clase "tonta": guarda bytes y los devuelve. La decisión de si un dato cacheado es válido, está vencido, o debe descartarse por incompatibilidad de `schema_version`, vive en la capa de `Cache` (que envuelve a `FlashStorage`), no en `FlashStorage` mismo. Esta separación de responsabilidades se discute en detalle en el ADR correspondiente (§13, decisión D9).

**R10. El namespace de tópicos MQTT siempre incluye `device_id`, incluso con un solo dispositivo desplegado.**
`esphome_ui/<device_id>/event` y `esphome_ui/<device_id>/cmd`, nunca tópicos planos sin el identificador del dispositivo. El costo de incluirlo es nulo; el costo de no incluirlo y necesitarlo después (cuando exista un segundo panel) es un refactor de mensajería completo, incluyendo del lado de Home Assistant.

---

## Reglas que nunca deberían romperse

Esta sección es intencionalmente más corta y más categórica que la anterior. Son las reglas que, si se rompen, indican que el proyecto se está desviando de su propósito fundamental, no simplemente tomando un atajo táctico.

1. **El firmware nunca debe requerir recompilación para que un usuario cambie qué hace un botón, qué ícono tiene, o a qué entidad apunta.** Si en algún punto de la evolución del proyecto esto deja de ser cierto para algún caso, ese caso está, por definición, fuera del modelo de este proyecto y no debería forzarse a entrar.

2. **El firmware nunca debe importar conocimiento de un backend específico (Home Assistant, Node-RED, o cualquier otro).** Esta es la regla individual más importante de todo el documento. Es la que separa "un firmware para controlar mi casa" de "una plataforma".

3. **Nunca se le muestra al usuario un dato desactualizado disfrazado de dato actual.** Un valor `STALE_OR_DISCONNECTED` debe ser visualmente distinguible de un valor `VALID`, siempre, en todos los templates, sin excepción.

4. **Nunca se aplica una configuración parcialmente validada.** No existe, ni debería existir nunca, un camino de código donde una parte de una `PageConfig` se aplique al runtime mientras otra parte todavía se está validando.

5. **Nunca se agrega una dependencia, biblioteca, o capa de abstracción sin que exista primero un caso de uso concreto que la necesite en el código real.** (Regla R7 elevada a categoría de "nunca romper" porque es, históricamente, la forma más común en que proyectos de hobby de una sola persona mueren: por sobre-ingeniería antes de tener algo funcionando.)

---

## Casos de uso

### Caso de uso primario: panel de control doméstico fijo

El caso que motivó el proyecto. Una ESP32-2432S028R (CYD) montada en una pared o superficie de una habitación, mostrando una o más páginas de control: luces, clima, escenas, sensores. El usuario final (quien vive en la casa, no necesariamente quien programa) interactúa tocando botones. El mantenedor del sistema domótico (Delmo, en este caso) es quien edita la configuración cuando quiere cambiar qué controla el panel.

Flujo típico: el mantenedor edita el JSON servido por Home Assistant (a mano, en Sprint 1; eventualmente vía un editor visual), el panel detecta el cambio (por trigger MQTT o por reinicio), descarga la nueva configuración, valida, y actualiza la interfaz sin que nadie toque el dispositivo físicamente ni lo reprograme.

### Caso de uso secundario: múltiples paneles con configuraciones distintas

Aunque no es el foco de Sprint 1, el diseño contempla desde el principio (regla R10) que puedan existir varios paneles CYD en distintas habitaciones, cada uno con su propio `device_id`, sirviendo configuraciones distintas (por ejemplo, un panel en la cocina con controles de cocina, uno en el living con controles de living) desde el mismo servidor HTTP de Home Assistant, simplemente sirviendo un archivo JSON distinto por dispositivo.

### Caso de uso terciario (especulativo, no implementado): panel de emergencia/alarma

Durante el diseño se mencionó, como ejemplo de por qué el Event Bus MQTT usa un discriminador `type` en el payload en lugar de tópicos separados por tipo de evento, la posibilidad de eventos como `alarm`, `notification`, `toast`. Esto no es un caso de uso implementado ni planificado para Sprint 1, pero se documenta porque **influyó una decisión de diseño real** (el formato del Event Bus, ver §19): el sistema debe poder crecer hacia notificaciones push sin necesitar un rediseño del canal de comunicación.

### Caso de uso futuro (fuera de alcance v1): auto-configuración vía editor visual

El mantenedor entra a una tarjeta de Home Assistant, arrastra o selecciona "agregar página", elige un template de una lista, el sistema le muestra solo los campos que ese template necesita (usando la introspección de `accepted_types()`, `min_controls()`, `max_controls()`, `supported_variants()`), completa entidades desde desplegables poblados por la API de HA, guarda, y el panel se actualiza solo. Este caso de uso es la motivación de fondo detrás de varias decisiones de diseño (particularmente la introspección de templates, R en §9), aunque su implementación esté fuera de alcance.

---

## Problemas que este proyecto intenta resolver

1. **El ciclo de "cambiar un botón = recompilar y flashear" es lento y frágil.** En un setup ESPHome tradicional con `lvgl:` declarado directamente en YAML, cualquier cambio de configuración de la interfaz (agregar un botón, cambiar qué entidad controla) requiere editar el YAML del dispositivo, recompilar, y hacer OTA (o peor, flasheo por USB). Esto es lento incluso con OTA, y elimina cualquier posibilidad de que alguien que no sea el propio desarrollador ajuste la interfaz.

2. **El acoplamiento entre firmware y backend hace que cambiar de sistema domótico sea reescribir todo.** Si la lógica de "qué es una luz" y "cómo se prende" vive dentro del firmware (como sucede en casi todos los proyectos ESPHome+LVGL existentes, ver comparación abajo), migrar de Home Assistant a otro sistema implica reescribir el firmware entero, no solo la integración.

3. **Los paneles táctiles DIY suelen mostrar datos desactualizados sin indicarlo.** Es un problema común y subestimado: un panel que pierde conexión con el broker MQTT sigue mostrando el último estado que recibió, indistinguible visualmente de un estado actual. Esto genera confusión real (alguien cree que una luz está apagada porque el panel lo muestra así, cuando en realidad está prendida y el panel simplemente perdió conexión).

4. **La falta de un modelo de templates reutilizables obliga a rehacer diseño de UI por cada proyecto.** Proyectos existentes en la comunidad ESPHome+LVGL (ver comparación) suelen ser configuraciones YAML extensas y específicas de un usuario, difíciles de adaptar o reusar por otra persona sin reescribir gran parte del archivo.

---

## Limitaciones actuales de ESPHome + LVGL relevantes para este proyecto

Estas limitaciones fueron identificadas durante el diseño y determinan decisiones de arquitectura concretas documentadas en otras secciones.

**L1 — El bloque `lvgl:` de ESPHome es fundamentalmente un DSL declarativo de compile-time.**
ESPHome traduce YAML a C++ en tiempo de compilación. El bloque `lvgl:` genera código que crea un árbol de widgets fijo. No existe, dentro del DSL, un mecanismo para decir "creá widgets según una estructura que se conoce solo en runtime". *Consecuencia de diseño:* el motor de templates debe implementarse como un `external_component` en C++ que use la librería LVGL directamente (llamadas a `lv_obj_create`, `lv_label_set_text`, etc.), no a través del DSL YAML. Esto se estableció como la primera decisión arquitectónica cerrada del proyecto (ver §13, ADR-001).

**L2 — El componente `api:` (integración nativa con Home Assistant) requiere que cada entidad esté declarada en YAML en tiempo de compilación.**
No existe forma de suscribirse, vía `api:`, al estado de una entidad cuyo `entity_id` se conoce solo en runtime (por ejemplo, porque viene de un JSON de configuración). *Consecuencia de diseño:* la comunicación de estado/comando con Home Assistant no puede usar `api:` nativo para entidades dinámicas; debe usar MQTT, donde los tópicos y payloads sí pueden ser genéricos y el mapeo a entidades específicas de HA ocurre del lado de HA (en automations), no en el firmware. Ver ADR-002 en §13.

**L3 — Las placas CYD (ESP32-2432S028R) típicamente no traen PSRAM.**
La variante más común de esta placa usa un ESP32 WROOM-32 sin PSRAM externa, con aproximadamente 320KB de SRAM interna disponible, compartida entre el framebuffer de LVGL, buffers de red (HTTP/MQTT/TLS si aplica), el heap de la aplicación, y el propio stack de ESPHome/WiFi. *Consecuencia de diseño:* regla R2 y R3 (widgets creados una sola vez, solo se instancian los templates efectivamente usados), y la recomendación explícita de no cachear el JSON completo de configuración en RAM más tiempo del necesario para parsearlo.

**L4 — LVGL v9 (la versión soportada por ESPHome en las versiones recientes) maneja el ciclo de vida de widgets de forma manual.**
No hay garbage collection ni recuento de referencias automático para widgets LVGL. Crear y destruir widgets dinámicamente en runtime es una fuente común de bugs (fugas de memoria, use-after-free, fragmentación de heap) en proyectos LVGL embebidos. *Consecuencia de diseño:* regla R2, que prohíbe crear/destruir widgets fuera del método `create()` inicial de cada template.

**L5 — El bloque `http_request:` de ESPHome soporta GET/POST simples, pero el manejo de respuestas grandes (JSON extenso) tiene límites de buffer configurables que hay que dimensionar con cuidado.**
No es una limitación bloqueante, pero es un punto de atención para el Sprint 1: el tamaño esperado del JSON de configuración debe mantenerse acotado (páginas y controles limitados) para no forzar buffers grandes en una placa sin PSRAM.

**L6 — ESPHome no expone, dentro del DSL, primitivas para lógica de "reintentos con backoff" o "cache con invalidación por checksum" de forma nativa para `http_request:`.**
Esto debe implementarse a mano dentro del `external_component`, no se obtiene gratis del framework. Es una de las razones por las que `ApplicationController` existe como clase explícita orquestando ese ciclo de vida (ver §16 y ADR-006 en §13).

---

## Comparación con otras soluciones existentes

Es relevante ubicar este proyecto respecto al ecosistema existente de ESPHome+LVGL para paneles domóticos, porque ayuda a entender qué problema específico resuelve que otras soluciones no resuelven, y para evitar reinventar sin necesidad partes que ya están bien resueltas en otros lados.

**Configuraciones YAML monolíticas declaradas directamente con `lvgl:`** (el patrón más común en proyectos personales de la comunidad ESPHome): son la forma "estándar" de usar LVGL con ESPHome. Tienen la ventaja de ser simples de entender para quien ya conoce YAML de ESPHome, y no requieren escribir C++. La desventaja central, que es exactamente el problema que este proyecto busca resolver, es que cualquier cambio de interfaz requiere editar YAML y recompilar/reflashear. No hay separación entre "definición de layout" y "configuración de contenido".

**Proyectos comunitarios de "paneles modulares" basados en `!include` de fragmentos YAML** (por ejemplo, repositorios que exponen archivos YAML reutilizables por tipo de tile — luz, sensor, clima — con placeholders vía sustituciones de ESPHome): resuelven parcialmente el problema de reutilización de diseño (uno no reescribe el layout de cada tile desde cero) pero siguen requiriendo recompilación para cualquier cambio de contenido, porque las sustituciones de ESPHome se resuelven en tiempo de compilación, no en runtime. Es un paso intermedio interesante entre "todo hardcodeado" y "todo configurable en runtime", pero no llega al objetivo de este proyecto.

**Editores visuales de diseño LVGL para ESPHome (herramientas tipo canvas que exportan YAML)**: resuelven el problema de *diseñar* la interfaz más rápido, con una experiencia visual de arrastrar y soltar, pero el resultado final sigue siendo YAML estático que se compila. No resuelven el problema de reconfiguración sin recompilar; son una herramienta de autoría, no un runtime dinámico.

**Paneles comerciales cerrados** (tablets con apps dedicadas de fabricantes de domótica, sistemas propietarios): resuelven bien la reconfiguración en runtime (típicamente con una app o editor propio), pero a costa de acoplamiento total al ecosistema del fabricante, sin transparencia del protocolo, y generalmente sin soporte para hardware DIY económico como la CYD.

**Posicionamiento de este proyecto respecto a estas alternativas:** UI Engine ocupa un espacio que no está bien cubierto — reconfiguración en runtime sin recompilar, sobre hardware DIY económico, con desacople real del backend — a costa de requerir escribir el motor en C++ (más esfuerzo inicial que un YAML declarativo) y de sacrificar la libertad total de layout que ofrecería, por ejemplo, un editor visual que exporta YAML estático.

---

## Justificación de decisiones (Architecture Decision Records)

Esta sección documenta cada decisión arquitectónica significativa en formato ADR (Architecture Decision Record), incluyendo el contexto, las alternativas consideradas, la decisión tomada, y las consecuencias. A diferencia de un resumen, aquí se preserva el razonamiento de las alternativas rechazadas — incluyendo argumentos que en su momento parecían razonables pero que no sobrevivieron la discusión.

Notación: cada ADR indica si la decisión está **cerrada** (no se espera revisitarla sin una razón de peso) o **abierta a revisión** (se tomó por descarte de tiempo, pero podría reconsiderarse con más información).

---

### ADR-001: El motor vive en un `external_component` C++, no en el DSL YAML `lvgl:`

**Estado:** Cerrada.

**Contexto:** La primera pregunta de diseño fue dónde vive la lógica de construir páginas dinámicamente a partir de configuración externa.

**Alternativas consideradas:**
- *(A)* Usar el DSL `lvgl:` de ESPHome con sustituciones (`!include`, variables) para simular configurabilidad.
- *(B)* Escribir un `external_component` en C++ que use LVGL directamente, dejando `lvgl:` fuera del árbol de páginas dinámicas.

**Decisión:** (B).

**Razonamiento:** La limitación L1 (§8) es determinante: `lvgl:` es un DSL de compile-time. La alternativa (A) fue descartada casi inmediatamente en la discusión porque no resuelve el problema central del proyecto (reconfiguración sin recompilar) — solo lo pospone o lo disimula parcialmente con sustituciones, que igual requieren recompilación para cambiar valores.

**Consecuencias:** El proyecto requiere escribir C++ real, con conocimiento de la API de LVGL y de la estructura interna de un `external_component` de ESPHome. Esto eleva la barrera de entrada del proyecto comparado con un YAML declarativo, pero es el único camino consistente con el objetivo general.

---

### ADR-002: Comunicación de estado/comando vía MQTT, no vía `api:` nativo de ESPHome

**Estado:** Cerrada.

**Contexto:** Se necesita un canal para que el dispositivo reciba estados de entidades y envíe comandos, sin conocer de antemano (en compile-time) qué entidades va a controlar.

**Alternativas consideradas:**
- *(A)* Usar el componente `api:` nativo de ESPHome, declarando entidades "virtuales" que se mapean a HA.
- *(B)* Usar MQTT con un modelo de tópicos y payloads genéricos.

**Decisión:** (B).

**Razonamiento:** La limitación L2 (§8) descarta (A) de forma directa: `api:` requiere declaración de entidades en compile-time, lo cual viola el objetivo específico #1 (eliminar recompilación) para cualquier cambio que involucre una entidad nueva. MQTT no tiene esa restricción — los tópicos y el contenido del payload son completamente dinámicos en runtime.

**Consecuencias:** Se requiere un broker MQTT en la red (ya presente en el setup existente del autor). La traducción entre tópicos MQTT genéricos y entidades reales de HA debe implementarse del lado de HA (automations), lo cual es consistente con el Principio P1.

---

### ADR-003: Modelo de templates predefinidos, no composición libre de widgets

**Estado:** Cerrada.

**Contexto:** Definir cuánta libertad tiene el JSON de configuración sobre la estructura visual.

**Alternativas consideradas:**
- *(A)* Composición libre: el JSON describe un árbol arbitrario de widgets, posiciones, y estilos.
- *(B)* Templates predefinidos: el firmware conoce un catálogo cerrado de "formas de página", el JSON solo parametriza.

**Decisión:** (B).

**Razonamiento:** Desarrollado en profundidad en §7. En síntesis: (A) tiene costos de memoria impredecibles, superficie de bugs no acotada, y un costo de implementación mucho mayor, sin que exista evidencia de que el caso de uso real (paneles domóticos) necesite esa libertad. (B) es más simple de implementar, más fácil de validar exhaustivamente, y allana el camino para un futuro editor visual basado en introspección de templates.

**Consecuencias:** Agregar un nuevo tipo de "forma de página" (por ejemplo, un layout de tres columnas con proporciones distintas) requiere escribir una clase nueva y recompilar el firmware. Esto se acepta como trade-off consciente: es infrecuente (agregar un template nuevo) comparado con la operación frecuente que sí se resuelve sin recompilar (cambiar contenido de páginas existentes).

---

### ADR-004: `ConfigProvider` como interfaz abstracta, con una sola implementación en Sprint 1

**Estado:** Cerrada (la interfaz); Abierta a revisión (cuáles implementaciones adicionales vale la pena escribir y cuándo).

**Contexto:** Definir cómo el motor obtiene el JSON de configuración, y si el motor debe conocer el mecanismo de transporte (HTTP, MQTT, SD, etc.).

**Alternativas consideradas:**
- *(A)* El motor conoce directamente HTTP (llama a `http_request` sin capa de abstracción intermedia).
- *(B)* Una interfaz `ConfigProvider` con método `fetch()`, e implementaciones concretas intercambiables (`HttpConfigProvider`, y en el futuro potencialmente `MqttConfigProvider`, `SdConfigProvider`).

**Decisión:** (B), interfaz definida desde el inicio, pero **solo se implementa `HttpConfigProvider` en Sprint 1**.

**Razonamiento:** Este fue un punto de desacuerdo real entre las dos partes de la discusión de diseño. La posición inicial (desde el lado de ChatGPT en la conversación de diseño) defendía desacoplar completamente el origen de la configuración desde el día uno, argumentando que "no cuesta nada" y que el origen de configuración podría cambiar en el futuro (SD, SPIFFS, una integración nueva). La posición de Claude coincidió en el valor de la interfaz abstracta (el costo de una clase virtual con un método es efectivamter nulo), pero objetó implementar más de una fuente de configuración en Sprint 1 sin un caso de uso concreto que la necesitara — aplicando el Principio P4 y la regla R7. La convergencia final fue: interfaz sí, múltiples implementaciones no, hasta que haya necesidad real.

**Consecuencias:** El código de Sprint 1 tiene exactamente una implementación de `ConfigProvider` (`HttpConfigProvider`), más `FlashStorage`/`Cache` como mecanismo de persistencia (que es conceptualmente distinto de "obtener configuración nueva", ver ADR-005). Escribir `MqttConfigProvider` en el futuro no debería requerir tocar `ApplicationController`, gracias a la interfaz ya definida.

---

### ADR-005: Separación entre `ConfigProvider`, `Cache` y `FlashStorage`

**Estado:** Cerrada.

**Contexto:** Definir cómo se relacionan la obtención de configuración nueva y la persistencia de la última configuración conocida.

**Alternativas consideradas:**
- *(A)* Una sola clase `FlashConfigProvider` que decide internamente cuándo usar el cache y cuándo pedir uno nuevo por HTTP.
- *(B)* Tres responsabilidades separadas: `ConfigProvider` (obtiene desde la fuente remota), `Cache` (decide si un dato persistido sigue siendo válido), `FlashStorage` (persiste y recupera bytes, sin tomar decisiones).

**Decisión:** (B).

**Razonamiento:** La propuesta inicial (llamar a la clase de persistencia `FlashConfigProvider`, tratándola como una implementación más de `ConfigProvider`) fue señalada como conceptualmente incorrecta durante la discusión: "Flash no provee configuración, Flash persiste". Nombrar la clase como si proveyera configuración mezcla dos responsabilidades distintas (obtener un dato nuevo, vs. recordar el último dato bueno) bajo una misma interfaz, lo cual dificulta razonar sobre el sistema cuando aparecen bugs de sincronización entre ambas. Separar en tres clases con responsabilidades estrictas (regla R9) resulta en un diseño más fácil de auditar, aunque signifique una clase más.

**Consecuencias:** `FlashStorage` es deliberadamente "tonta" — no valida `schema_version` ni decide nada, solo guarda y devuelve bytes. Esa lógica de decisión vive en `Cache`. `ApplicationController` es quien orquesta la interacción entre las tres.

---

### ADR-006: `ApplicationController` como orquestador explícito del ciclo de vida

**Estado:** Cerrada.

**Contexto:** Decidir si la lógica de "cuándo recargar configuración, cuándo usar cache, cuándo reconstruir la UI" vive repartida entre varias clases o centralizada en una sola.

**Alternativas consideradas:**
- *(A)* Repartir la lógica de ciclo de vida entre `UIEngine`, `ConfigProvider` y `TemplateRegistry`, cada uno reaccionando a eventos de forma más o menos independiente.
- *(B)* Una clase única, `ApplicationController`, que orquesta explícitamente el flujo completo: boot → carga de cache → dibujo inicial → conexión MQTT/HTTP → detección de config nueva → validación → swap atómico → manejo de reconexión.

**Decisión:** (B).

**Razonamiento:** Se identificó, en un punto avanzado de la discusión, que el mayor riesgo técnico del proyecto no es LVGL, ni el parser JSON, ni MQTT individualmente, sino la **interacción temporal entre todos esos componentes** — qué pasa si la red se cae a mitad de una descarga, qué pasa si llega un evento MQTT mientras se está aplicando una config nueva, qué pasa al reconectar después de una pérdida de WiFi. Repartir esa lógica entre varias clases (alternativa A) hace que, con el tiempo, nadie tenga una vista completa de "quién decide qué en qué momento", lo cual es exactamente el tipo de deuda técnica que un proyecto de una sola persona no puede permitirse acumular.

**Consecuencias:** `ApplicationController` es la clase más importante del sistema desde el punto de vista de robustez, y su diseño merece más tiempo de revisión que cualquier template individual. Ver el diagrama de ciclo de vida completo en §16.

---

### ADR-007: `TemplateRegistry` con factories registradas por nombre, no un `if`/`switch` sobre tipos

**Estado:** Cerrada.

**Contexto:** Cómo el motor instancia la clase de template correcta a partir del string `template` del JSON.

**Alternativas consideradas:**
- *(A)* Un `if (name == "button_grid") return new ButtonGrid(); else if (...)` centralizado en el motor.
- *(B)* Un registry con `std::map<string, Factory>` donde cada template se auto-registra.

**Decisión:** (B).

**Razonamiento:** (A) viola la regla R1 y el objetivo específico #3 (agregar un template debe ser una tarea aislada). Cada `if` nuevo en el motor central es una modificación al código compartido cada vez que se agrega un template, lo cual aumenta el riesgo de romper algo que ya funcionaba. (B) permite que agregar un template sea, en el caso ideal, solo escribir la clase nueva y una línea de registro, sin tocar el motor.

**Consecuencias:** Costo de una entrada en un `std::map` por template registrado — insignificante en Sprint 1 con un solo template. Se discutió (ver ADR-011) si usar `std::function` para las factories tiene costo de flash relevante frente a punteros a función simples; se decidió no optimizar prematuramente.

---

### ADR-008: `controls[]` con campo `type` discriminador, en vez de un array de campos fijos por template

**Estado:** Cerrada.

**Contexto:** Cómo estructurar la lista de elementos dentro de una página en el JSON.

**Alternativas consideradas:**
- *(A)* Un array `items[]` donde la interpretación de cada elemento depende implícitamente del template contenedor (por ejemplo, `ButtonGrid` siempre espera botones, sin campo `type` explícito).
- *(B)* Un array `controls[]` donde cada elemento lleva un campo `type` explícito (`"button"`, y en el futuro `"slider"`, `"label"`), validado contra lo que el template acepta (`accepted_types()`).

**Decisión:** (B).

**Razonamiento:** La propuesta inicial (A, de Claude) era razonable para Sprint 1 pero fue mejorada durante la discusión: con `type` explícito, un mismo template puede evolucionar para aceptar más de un tipo de control sin romper el schema (por ejemplo, `ClimatePage` podría aceptar `button`, `slider` y `label` simultáneamente), y la validación de "qué tipos acepta este template" queda centralizada en el propio template (`accepted_types()`) en vez de ser un supuesto implícito no verificado en código.

**Consecuencias:** Cada `Control` en el JSON es un poco más verboso (un campo `type` extra), a cambio de un formato con más vida útil y una validación explícita en vez de implícita.

---

### ADR-009: `variant` en vez de `layout` con geometría explícita

**Estado:** Cerrada.

**Contexto:** Cómo el JSON indica la disposición visual dentro de un template (por ejemplo, cuántas columnas y filas tiene una grilla de botones).

**Alternativas consideradas:**
- *(A)* Un campo `layout` con geometría explícita, por ejemplo `"2x2"`.
- *(B)* Un campo `variant` con un nombre semántico, por ejemplo `"four_buttons"`.

**Decisión:** (B).

**Razonamiento:** Una geometría explícita (`"2x2"`) describe un detalle de implementación gráfica que el JSON no debería necesitar conocer. Si en el futuro el diseño visual de la variante "cuatro botones" cambia (por ejemplo, de una grilla 2x2 a una disposición en cruz, o a botones de tamaño desigual), un JSON que dice `variant: "four_buttons"` sigue siendo válido y semánticamente correcto, mientras que uno que dice `layout: "2x2"` quedaría describiendo una geometría que ya no es cierta. El nombre semántico desacopla la configuración de la implementación visual concreta.

**Consecuencias:** El firmware es responsable de mapear cada `variant` soportada a su disposición gráfica real. Cada template expone sus variantes soportadas vía `supported_variants()`.

---

### ADR-010: `id` opaco en vez de `entity_id`

**Estado:** Cerrada. Considerada la decisión de mayor impacto conceptual del proyecto.

**Contexto:** Cómo identificar, dentro del JSON de configuración y del `Control` en runtime, a qué "cosa" se refiere un widget.

**Alternativas consideradas:**
- *(A)* Usar `entity_id` directamente, tal como lo expone Home Assistant (`light.living`, `switch.garage`).
- *(B)* Usar un campo `id` genérico y opaco para el firmware (`"living"`), sin ninguna estructura ni significado predefinido, cuya traducción a una entidad real de HA ocurre enteramente del lado de HA.

**Decisión:** (B).

**Razonamiento:** Esta decisión surgió como consecuencia natural de aplicar consistentemente el Principio P1 (el firmware es ciego al backend) al campo de identificación de controles — no fue, en un primer momento, planteada como "la gran decisión del proyecto", sino que emergió del razonamiento sobre otros puntos. Fue notada explícitamente durante la revisión posterior como el momento en que el proyecto dejó de ser conceptualmente "un firmware ESPHome para Home Assistant" y pasó a ser, en la práctica, un sistema agnóstico de backend, aunque su primera implementación siga siendo para Home Assistant.

**Consecuencias:** Toda la lógica de "qué es `id: living`" (que resulte ser `light.living` en HA, con su dominio, sus servicios disponibles, sus atributos) vive en la automation o script de HA que genera el JSON y que traduce eventos MQTT. El firmware nunca necesita parsear ni entender la sintaxis `dominio.nombre` de las entity_ids de HA.

---

### ADR-011: `std::function` para factories del registry, en vez de punteros a función simples

**Estado:** Abierta a revisión.

**Contexto:** Costo de flash de `std::function` (que arrastra parte de la STL) frente a punteros a función C simples, en un registry con potencialmente varias entradas.

**Alternativas consideradas:**
- *(A)* `std::function<std::unique_ptr<PageTemplate>()>` como tipo de factory.
- *(B)* Punteros a función simples (`PageTemplate* (*)()`), sin capacidad de capturar contexto.

**Decisión:** (A) para Sprint 1, con revisión explícita pendiente si el binario empieza a acercarse a los límites de flash disponibles.

**Razonamiento:** Con una sola entrada de registro en Sprint 1, la diferencia de costo de flash entre ambas alternativas es insignificante, y `std::function` da mejor ergonomía (permite, en el futuro, factories parametrizadas que capturen contexto). Cambiar prematuramente a punteros simples sería optimizar sin tener todavía el problema que esa optimización resolvería (aplicación del Principio P4 en sentido inverso: no agregar restricciones sin necesidad concreta, de la misma forma que no se agregan abstracciones sin necesidad concreta).

**Consecuencias:** Se deja documentado como punto de revisión explícito para cuando existan más templates registrados y se pueda medir el impacto real en el tamaño del binario compilado.

---

### ADR-012: Modelo de estados de confiabilidad (`ControlState`) de 3 valores en Sprint 1, no 5

**Estado:** Abierta a revisión — se espera pasar a 5 valores en una iteración post-Sprint-1.

**Contexto:** Cuántos estados distintos de "confiabilidad del dato" debe distinguir el sistema.

**Alternativas consideradas:**
- *(A)* Modelo de 5 estados: `UNKNOWN → SYNCING → VALID → STALE → DISCONNECTED`.
- *(B)* Modelo de 3 estados: `UNKNOWN`, `VALID`, `STALE_OR_DISCONNECTED` (unificando los dos últimos estados de A).

**Decisión:** (B) para Sprint 1.

**Razonamiento:** El modelo de 5 estados es conceptualmente más correcto y fue la propuesta inicial de ChatGPT en la discusión, con buena justificación (distinguir "el broker está caído" de "el dato es viejo pero el broker sigue conectado" es información útil). Sin embargo, implementarlo bien requiere resolver primero una pregunta de producto que todavía no tiene respuesta: ¿cuál es el timeout que separa `VALID` de `STALE` para cada tipo de entidad? (una lectura de temperatura puede tolerar minutos sin actualizarse; el estado de una luz debería considerarse sospechoso mucho antes). Fijar esa lógica en código antes de tener datos de uso real del sistema corriendo se consideró prematuro, aplicando nuevamente el Principio P4.

**Consecuencias:** Sprint 1 no distingue "dato viejo con broker conectado" de "broker desconectado" — ambos casos se representan igual visualmente (`STALE_OR_DISCONNECTED`). Se documenta como mejora esperada de la primera iteración post-Sprint-1, una vez que haya experiencia real de uso que informe los timeouts correctos por tipo de entidad.

---

### ADR-013: Semántica visual de estados centralizada en `Theme`, aunque `Theme` no se implemente en Sprint 1

**Estado:** Cerrada (el principio); implementación diferida (ver ADR-004 y R7 para el criterio general de diferir implementación).

**Contexto:** Quién decide cómo se ve un control en estado `STALE_OR_DISCONNECTED` — cada template individualmente, o un componente centralizado.

**Alternativas consideradas:**
- *(A)* Cada `PageTemplate::update_control()` decide su propia representación visual de cada estado.
- *(B)* Una clase `Theme`, con un método como `Theme::apply_state()`, que centraliza esa semántica visual; los templates solo consumen estilos, no los definen.

**Decisión:** (B), con la firma de `create()` de `PageTemplate` ya preparada para recibir una referencia a `Theme` desde Sprint 1, aunque la implementación interna de `Theme` en Sprint 1 sea mínima/hardcodeada.

**Razonamiento:** Sin esta centralización, cada template nuevo que se agregue corre el riesgo de representar los mismos estados de forma visualmente inconsistente (un template pintando gris lo que otro pinta con opacidad reducida, por ejemplo), lo cual degrada la experiencia de usuario de forma sutil y difícil de detectar en revisión de código. Se decidió reservar el "hueco" arquitectónico (la firma del método) desde el día uno específicamente para no tener que romper la firma de todos los templates existentes el día que `Theme` se implemente de verdad — ese cambio de firma sería un refactor invasivo evitable con un costo de previsión casi nulo hoy.

**Consecuencias:** `PageTemplate::create(lv_obj_t* parent, const Theme& theme)` es la firma definitiva desde Sprint 1. La implementación real de `Theme` (con `ButtonStyle`, `LabelStyle`, `CardStyle`, `PopupStyle` como se discutió) queda fuera de Sprint 1.

---

### ADR-014: Pipeline `Parse → Validate → Resolve → Ready`, sin capas DTO/Runtime Model separadas físicamente en memoria

**Estado:** Cerrada.

**Contexto:** Cómo estructurar el proceso de convertir el JSON crudo en objetos utilizables por los templates, y si "DTO" y "Runtime Model" deben ser estructuras de datos físicamente distintas en memoria.

**Alternativas consideradas:**
- *(A)* Cuatro capas físicamente separadas: JSON → DTO (struct plano) → Validator → Runtime Model (struct distinto, con recursos ya resueltos) → Template.
- *(B)* Un pipeline de pasos (`Parse`, `Validate`, `Resolve`) que opera *in-place* sobre un mismo struct, donde `Resolve()` rellena campos derivados (como el ícono resuelto a partir del string crudo) dentro de la misma instancia, sin duplicar la estructura completa.

**Decisión:** (B).

**Razonamiento:** La propuesta inicial de tener un DTO y un Runtime Model como tipos completamente distintos (defendida por ChatGPT, con buena justificación conceptual: "el parser no debería resolver recursos, solo cargar texto") es correcta en el principio, pero implementarla como dos structs separados en memoria duplicaría, en la práctica, casi todos los campos que *no* requieren resolución (el `id`, el `caption`, que viajan sin cambios), para beneficiar solo a los pocos campos que sí la requieren (`icon`, `color`). En un dispositivo sin PSRAM, esa duplicación no se justifica. La solución de compromiso — mantener el principio de "el parser no resuelve recursos" pero implementarlo como una función `resolve()` que opera sobre el mismo struct, rellenando campos derivados una sola vez — preserva el beneficio conceptual (separación de responsabilidades entre parsear y resolver) sin el costo de memoria de una estructura duplicada.

**Consecuencias:** `Control` tiene campos "crudos" (`icon_raw`, `color_raw`) y campos "resueltos" (`resolved_icon`, `resolved_color`) en la misma instancia. `resolve()` se llama una sola vez, después de `Validate()`, y a partir de ahí el objeto se considera inmutable en su definición (regla R6).

---

### ADR-015: `meta: {}` reservado y vacío desde Sprint 1

**Estado:** Cerrada.

**Contexto:** Si el schema JSON debe anticipar campos futuros no utilizados todavía.

**Alternativas consideradas:**
- *(A)* No incluir ningún campo hasta que sea necesario, para mantener el schema mínimo.
- *(B)* Incluir un campo `meta: {}` opcional, vacío, reservado para futuras propiedades (confirmación antes de ejecutar acción, badge, prioridad, animación, sonido, vibración, tooltip, long-press, etc.) sin usarlo todavía.

**Decisión:** (B).

**Razonamiento:** El costo de reservar un objeto vacío en el schema es nulo (no ocupa espacio relevante, no requiere lógica adicional). El beneficio es evitar, en el futuro, tener que agregar campos nuevos directamente al nivel raíz de `Control` cada vez que aparezca una necesidad puntual (lo cual eventualmente satura el objeto raíz con propiedades de uso poco frecuente) o, peor, tener que versionar el schema por cada campo nuevo cuando en realidad se podría haber previsto un espacio de extensión.

**Consecuencias:** `meta` no se parsea activamente en Sprint 1 (puede incluso ignorarse en el parser), pero su presencia en el schema documenta la intención de extensibilidad desde el inicio.

---

# Parte II — Implementación real validada

Esta parte registra lo que efectivamente se construyó y probó entre el 24 y el 28 de julio de 2026. Cuando una descripción de esta parte contradiga una hipótesis previa, prevalece la implementación real y debe generarse un ADR de seguimiento si la diferencia afecta una regla arquitectónica.

## Plataforma y entorno de referencia

- Placa: ESP32-2432S028R CYD (Guition), ESP32-WROOM-32, flash de 4 MB y sin PSRAM.
- Pantalla: ILI9341, 320 × 240 en orientación horizontal.
- Táctil: XPT2046 resistivo en un segundo bus SPI.
- Audio: transductor integrado en GPIO26 mediante salida PWM y RTTTL.
- Framework: ESPHome 2026.7.3 sobre ESP-IDF 5.5.5.
- UI: LVGL 9.5 integrado por ESPHome.
- Entorno de desarrollo: ESPHome independiente en Windows, Visual Studio Code, Git y carga USB por COM57.

La prueba Arduino/TFT_eSPI original se conserva únicamente como validación de hardware. El producto no depende de ese sketch ni utiliza TFT_eSPI como capa gráfica. ESPHome administra los drivers físicos y el runtime crea objetos LVGL sobre la pantalla activa.

## Arquitectura implementada

```text
Home Assistant
      │  HTTPS / WebSocket
      ▼
Backend de laboratorio (ha_bridge.py)
      │  MQTT: estados, acciones, recarga y sonido
      ▼
UiEngineComponent (external_component ESPHome)
      ├── ConfigProvider HTTP
      ├── FlashStorage
      ├── ConfigParser
      ├── TemplateRegistry
      ├── PageTemplate activo
      └── Estado runtime de controles
              │
              ▼
          LVGL 9.5
              │
              ▼
     ESPHome display + touch
              │
              ▼
      ESP32-2432S028R CYD
```

La frontera conceptual original se mantuvo: el firmware conoce `Control.id`, `type`, `role`, `caption`, `color`, `unit`, `action` y estado, pero no conoce dominios ni servicios de Home Assistant. El mapa entre IDs opacos y entidades reales vive en `config/backend-map.json` y es interpretado por el backend externo.

## Ciclo de vida real

### Arranque

1. ESPHome inicializa pantalla, táctil, LVGL, Wi-Fi, MQTT, reloj y sonido.
2. `UiEngineComponent` registra las factories de templates.
3. Se abre el almacenamiento flash.
4. Se intenta leer la última configuración persistida.
5. La configuración se parsea y valida por completo antes de tocar la interfaz.
6. Si la caché es inválida, se usa la configuración embebida en el firmware.
7. Se crea una única página activa y sus widgets.
8. Al conectar MQTT, el motor solicita recarga HTTP y luego sincronización completa de estados.

### Recarga dinámica

1. El editor o una herramienta modifica `ui.json`.
2. Se publica `{"type":"reload"}` en el tópico de eventos.
3. La CYD descarga el JSON por HTTP.
4. El parser crea una configuración candidata.
5. Todos los templates y controles se validan antes del cambio.
6. Solo si todo es válido se reemplaza la configuración activa.
7. La copia aceptada se guarda en flash.

Una recarga inválida conserva la UI anterior. La configuración no se aplica parcialmente.

### Acción táctil

1. Un template detecta `LV_EVENT_CLICKED`.
2. Emite `control_id + action` sin conocer el backend.
3. ESPHome publica el comando por MQTT.
4. El backend verifica que ese control tenga `allow_control: true`.
5. El backend llama al servicio permitido de Home Assistant.
6. El cambio real vuelve como evento de estado.
7. El panel actualiza el widget con la confirmación del backend.

Este flujo evita que un botón aparente haber actuado cuando el sistema real rechazó o no recibió la orden.

## Templates implementados

| Template | Variantes verificadas | Uso actual | Estado |
|---|---|---|---|
| `button_grid` | `two_buttons`, `four_buttons`, `six_buttons` | Luces, escenas y acciones genéricas | Validado físicamente |
| `climate` | `thermostat` | Temperatura actual, objetivo y ajuste ±1 °C | Validado con calefactor real; encendido bloqueado por seguridad |
| `clock_weather` | `screensaver` | Reloj, condición, temperatura y humedad | Validado; activación por inactividad y salida con primer toque |
| `sensor_grid` | `four_values` | Cuatro valores con unidad y precisión | Validado con temperaturas y humedad reales |
| `cover` | `position_controls` | Posición, estado, apertura/cierre total y pasos de 10 % | Validado con cortina real |

El límite continúa siendo ocho páginas por documento de configuración. La página marcada como `screensaver` no participa de la navegación manual.

## Modelo de control actual

Campos utilizados por la implementación:

- `type`: clase genérica del control (`button` o `value` en la versión actual).
- `id`: identificador opaco y único en todo el documento.
- `role`: función del control dentro de un template especializado.
- `caption`: texto visible.
- `color`: color RGB hexadecimal.
- `unit`: unidad opcional para valores.
- `action`: acción genérica emitida al tocar.
- `meta`: objeto reservado para extensiones futuras.

`PageConfig` contiene `template`, `variant`, `title`, `screensaver` y `controls[]`. El parser convierte colores a valores de runtime, conserva los strings necesarios y rechaza documentos que excedan límites o contengan IDs duplicados.

## Estado y confiabilidad

El modelo de tres estados previsto en ADR-012 fue implementado:

- `UNKNOWN`: todavía no llegó una lectura confiable.
- `VALID`: dato confirmado por el backend.
- `STALE_OR_DISCONNECTED`: el backend dejó de estar disponible o el dato perdió confiabilidad.

Al desconectarse MQTT, los controles activos pasan a un aspecto atenuado o de advertencia. Al reconectar, el panel solicita una sincronización completa antes de volver a presentar los valores como válidos.

## Transporte implementado

### Configuración

- HTTP: descarga de `ui.json` desde una URL configurada en ESPHome.
- Flash: última configuración remota aceptada.
- Embebida: respaldo seguro compilado con el firmware.
- MQTT: solo dispara la recarga; el documento completo no viaja en el tópico.

### Eventos MQTT

- Backend → panel: `esphome_ui/<device_id>/event`.
- Panel → backend: `esphome_ui/<device_id>/cmd`.

Tipos verificados:

- `reload`: solicitar descarga de configuración.
- `control_changed`: actualizar estado y valor de un control.
- `sound`: reproducir un sonido permitido.
- `action`: acción táctil emitida por el panel.
- `sync_request`: solicitar todos los estados actuales.

Los mensajes usan QoS 1 y no se retienen cuando representan eventos transitorios.

## Integración con Home Assistant

`tools/ha_bridge.py` es una implementación de laboratorio, no parte del firmware. Sus responsabilidades actuales son:

- Autenticarse contra Home Assistant sin exponer el token al dispositivo.
- Seguir `state_changed` y llamadas relevantes por WebSocket.
- Traducir IDs opacos a entidades y atributos.
- Aplicar formato decimal y mapas de valores.
- Verificar `allow_control` antes de ejecutar servicios.
- Publicar confirmaciones y estados no disponibles.
- Mantener una consulta periódica de respaldo.

La temperatura objetivo del calefactor puede modificarse, pero el encendido permanece deliberadamente deshabilitado. Esta restricción es parte de la configuración del backend, no del template `climate`.

La cortina de prueba permite apertura/cierre total y `set_cover_position` relativo. Los ajustes de 10 % reemplazaron al botón Pausa porque una orden de detención enviada a través de la nube puede llegar cuando el movimiento ya terminó.

## Sonido y notificaciones

La CYD reproduce secuencias cortas RTTTL con ganancia moderada. Sonidos registrados:

- `attention`
- `notification`
- `success`
- `warning`
- `error`

El backend escucha el evento `cyd_ui_sound` de Home Assistant. Una automatización puede dispararlo con un campo `sound`, y el puente publica el evento MQTT correspondiente. Esto fue validado de extremo a extremo desde Home Assistant remoto hasta el parlante físico.

Los sonidos deben ser breves, sutiles y no bloquear el loop principal. No se pretende reproducir voz ni audio continuo en esta placa.

## Protector de pantalla

El template `clock_weather` puede marcarse con `screensaver: true`. Tras el tiempo de inactividad configurado:

- se recuerda la página anterior;
- se muestra reloj y clima;
- se ocultan las flechas de navegación;
- el primer toque despierta la interfaz y regresa a la página anterior;
- no se ejecuta la acción subyacente a ese primer toque.

El timeout actual de laboratorio es corto para facilitar pruebas. El valor final deberá ser configurable desde el editor visual.

## Incidentes y lecciones de hardware real

### Calibración táctil

La primera grilla mostró que las coordenadas horizontales estaban invertidas: tocar “Noche” activaba “Living”. La solución correcta fue configurar el driver táctil (`mirror_x`) y no compensar posiciones dentro de cada template.

### Configuración flash incompatible

Durante el rediseño de la cortina, el firmware nuevo encontró en flash una configuración anterior que todavía contenía el rol `stop`. El archivo era legible, pero no válido para el nuevo contrato, y el motor se marcó como fallido antes de conectarse: la pantalla quedó negra aunque MQTT y el parlante seguían funcionando.

La corrección definitiva separó “pude leer la caché” de “la caché es válida”. El arranque ahora valida flash antes de aplicarla y cae a la configuración embebida si no es compatible. Además, el template de cortina acepta temporalmente el formato anterior para facilitar la migración.

### Regla resultante

Ningún proveedor puede considerarse exitoso solo porque devolvió bytes. El dato obtenido debe completar `Parse → Validate` antes de ser candidato a configuración activa. Las migraciones incompatibles deberán aumentar `schema_version` o incluir compatibilidad explícita.

## Uso de memoria medido

Compilación de referencia posterior al template de cortina y la recuperación segura:

- DRAM estática: 50.788 bytes, 28,1 % del presupuesto informado.
- Firmware: aproximadamente 1.274 kB, 69,4 % de la partición de aplicación.
- Partición de aplicación libre: aproximadamente 31 %.

Estos valores dejan margen para el editor y nuevos templates del lado del backend, pero aconsejan mantener widgets limitados, buffers parciales y recursos gráficos controlados. La placa sigue sin PSRAM.

## Verificaciones realizadas

- Pantalla y táctil en buses SPI separados.
- Rotación horizontal y correspondencia táctil de todas las zonas.
- Creación de botones y actualización visual por confirmación del backend.
- Variantes de 2, 4 y 6 botones.
- Navegación circular y conservación de estados.
- Descarga HTTP y recarga en vivo sin flashear.
- Caché flash y arranque sin servidor HTTP.
- Reconexión MQTT y sincronización completa.
- Cambios externos de Home Assistant reflejados en tiempo real.
- Ajuste de temperatura objetivo sin encender el calefactor.
- Reloj/clima como pantalla de reposo.
- Sonidos locales y disparados desde Home Assistant.
- Sensores con precisión decimal consistente.
- Cortina completa y ajustes incrementales del 10 %.
- Recuperación ante caché flash incompatible.

## Estructura actual del repositorio

```text
cyd-ui/
├── cyd-ui.yaml
├── components/ui_engine/
│   ├── __init__.py
│   ├── ui_engine.*
│   ├── model.h
│   ├── config_parser.*
│   ├── config_provider.*
│   ├── flash_storage.*
│   ├── template_registry.h
│   ├── page_template.h
│   ├── button_grid.*
│   ├── climate_page.*
│   ├── clock_weather_page.*
│   ├── sensor_grid.*
│   └── cover_page.*
├── config/
│   ├── ui.json
│   └── backend-map.json
├── tools/
│   ├── ha_bridge.py
│   ├── reload_config.py
│   └── play_sound.py
└── docs/
```

Las credenciales viven fuera del repositorio. No deben incorporarse a firmware, documentación, commits ni ejemplos públicos.

## Decisiones nuevas posteriores al diseño

### ADR-016: ESPHome administra hardware; el runtime compone sobre LVGL

**Estado:** Cerrada e implementada.

ESPHome mantiene display, touch, red, OTA, reloj y drivers. `UiEngineComponent` no hereda del componente LVGL ni controla el bus; crea y actualiza objetos mediante composición. Esto reduce dependencias y facilita migrar el hardware sin modificar templates.

### ADR-017: Configuración por HTTP y eventos por MQTT

**Estado:** Cerrada e implementada.

El JSON completo se inspecciona y depura por HTTP; MQTT transporta eventos pequeños. La división demostró ser simple de probar, permitió caché flash y evitó límites o fragmentación por mensajes grandes.

### ADR-018: Protector de pantalla como página especial

**Estado:** Cerrada e implementada.

El protector usa un template normal marcado con `screensaver`, pero el controlador lo excluye de navegación y administra entrada/salida por actividad. No se creó un segundo subsistema visual.

### ADR-019: Ajustes deterministas para actuadores con latencia

**Estado:** Cerrada e implementada para cortinas.

Cuando el transporte tiene segundos de latencia, “iniciar movimiento y detener después” es impreciso. Para ajustes finos se prefieren servicios idempotentes con objetivo explícito (`set_cover_position`) y pasos configurables.

### ADR-020: Validar cada nivel de recuperación antes de aplicarlo

**Estado:** Cerrada e implementada.

HTTP, flash y configuración embebida son fuentes de datos, no garantías de validez. Cada candidato debe superar parseo y validación. Una fuente inválida no puede bloquear el uso de la siguiente fuente segura.

### ADR-021: Configurador local antes de integrarlo en Home Assistant

**Estado:** Cerrada e implementada en v0.1.

La primera interfaz de configuración es una aplicación web local servida desde el mismo repositorio. Lee y escribe los contratos existentes, consulta las entidades mediante la API de Home Assistant sin exponer el token al navegador, valida antes de guardar, conserva una copia recuperable y ordena la recarga por MQTT. Este corte permite probar la experiencia completa sin empaquetar prematuramente una integración o panel de Home Assistant. El formato de `ui.json` y `backend-map.json` no depende de esta interfaz, por lo que más adelante podrá alojarse como panel o iframe sin modificar el firmware.

## Configurador visual v0.1

No se priorizarán más templates hasta resolver la experiencia de configuración. La primera versión implementa:

1. Ver la lista de páginas actuales.
2. Agregar, eliminar, duplicar y reordenar páginas.
3. Elegir template y variante.
4. Mostrar solo los campos admitidos por ese template.
5. Elegir entidades de Home Assistant sin escribir IDs manualmente.
6. Editar títulos, captions, unidades, colores y acciones.
7. Validar antes de guardar.
8. Generar `ui.json` y el mapa de backend.
9. Mantener copia anterior recuperable.
10. Ordenar una recarga y mostrar el resultado del guardado.

Queda para la siguiente iteración la confirmación explícita de aceptación desde la CYD, la restauración visual desde el historial y formularios especializados para servicios avanzados de cada dominio.

## Roadmap actualizado

### Completado

- Hardware y LVGL validados.
- Runtime C++ y registry de templates.
- Configuración dinámica, HTTP, flash y MQTT.
- Integración bidireccional de laboratorio con Home Assistant.
- ButtonGrid, Climate, ClockWeather, SensorGrid y Cover.
- Sonido y protector de pantalla.
- Recuperación segura ante configuración incompatible.
- Configurador visual local v0.1 con selección de entidades, vista previa, validación, historial y recarga.

### Siguiente

- Validación de uso del configurador v0.1.
- Confirmación de aceptación o rechazo enviada por la CYD.
- Restauración desde el historial.
- Formularios de backend específicos para climate, cover y otros dominios.

### Posterior

- Empaquetar el backend para despliegue estable.
- Theme centralizado y configurable.
- Nuevos templates: multimedia, ventilación, robot aspirador, seguridad e información.
- Pruebas automatizadas y simulador LVGL de escritorio.
- Definir licencia y proceso de publicación.

## Norma de mantenimiento documental

A partir de esta versión, cada commit que agregue un template, cambie el schema, modifique el ciclo de vida o altere una frontera de seguridad debe actualizar la documentación técnica correspondiente. Los cambios operativos menores pueden acumularse en `docs/STATUS.md`, pero las decisiones de arquitectura requieren un ADR nuevo o la actualización explícita del ADR afectado.

---

**Fin de la Documentación Oficial 1.0 — 28 de julio de 2026.**
