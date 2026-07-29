# CYD UI

Motor declarativo de interfaces LVGL para la pantalla
**ESP32-2432S028R (Cheap Yellow Display)**, integrado con ESPHome y Home
Assistant.

> Estado: **versión preliminar 0.1.1**. El firmware fue validado en hardware
> real, pero la instalación HACS y la migración del puente nativo todavía deben
> probarse en una instancia separada antes de considerarse estables.

## Qué resuelve

CYD UI permite cambiar páginas, textos, iconos MDI, colores y entidades desde
una interfaz gráfica, sin recompilar el firmware por cada modificación normal.
El firmware no conoce conceptos como luces, escenas o calefactores: recibe
controles genéricos y emite acciones genéricas.

Funciones disponibles:

- páginas de 2, 4 y 6 botones;
- climatización, sensores, cortinas y reloj/clima;
- protector de pantalla y horario nocturno;
- brillo manual o automático mediante el LDR frontal;
- sonidos breves mediante el parlante integrado;
- calibración táctil guiada;
- caché de configuración en flash;
- editor visual dentro de Home Assistant;
- migración reversible desde automatizaciones temporales al puente nativo.

## Instalación experimental mediante HACS

1. En HACS, abrí **Repositorios personalizados**.
2. Añadí `https://github.com/dgg006/cyd-ui` como categoría **Integración**.
3. Instalá **CYD UI** y reiniciá Home Assistant.
4. Abrí **Ajustes → Dispositivos y servicios → Añadir integración**.
5. Buscá **CYD UI** y completá el flujo gráfico.
6. Abrí el panel lateral **CYD UI**.

No ejecutes **Migrar puente** en una instalación importante sin revisar antes
las asociaciones y disponer de una copia de seguridad. La migración es
reversible, pero esta ruta aún está en validación.

## Firmware ESPHome

El firmware se instala por separado; HACS administra la integración de Home
Assistant, no el binario de la CYD.

1. Copiá `secrets.example.yaml` como `secrets.yaml`.
2. Reemplazá todos los valores de ejemplo.
3. Revisá `cyd-ui.yaml` y `examples/project.example.json`.
4. Validá y compilá:

```powershell
esphome config cyd-ui.yaml
esphome compile cyd-ui.yaml
```

La configuración utiliza dos buses SPI, tal como requiere la CYD clásica:
ILI9341 para la pantalla y XPT2046 para el táctil.

## Estructura

```text
components/ui_engine/       componente externo ESPHome y templates LVGL
custom_components/cyd_ui/   integración instalable mediante HACS
configurator/static/        fuentes web reutilizadas por el editor
examples/                   proyecto genérico sin entidades personales
docs/                       arquitectura y contrato JSON
tests/                      pruebas de configuración e integración
```

## Principios del proyecto

1. Los cambios habituales de interfaz no requieren recompilar.
2. El firmware no contiene entidades ni decisiones de Home Assistant.
3. Cada template crea un máximo fijo de widgets y luego actualiza propiedades.
4. Una configuración nueva se aplica únicamente después de validarse completa.
5. La pantalla espera confirmación del backend antes de mostrar un comando como
   ejecutado.

## Limitaciones conocidas

- La fuente LVGL todavía debe ampliarse para mostrar correctamente todos los
  caracteres españoles, incluida la `ñ`.
- La entrega directa de la configuración guardada hacia la CYD sigue en
  desarrollo; la caché y el transporte actual continúan siendo necesarios.
- La publicación inicial no está incluida todavía en el catálogo predeterminado
  de HACS; se instala como repositorio personalizado.
- El proyecto está optimizado inicialmente para la CYD clásica sin PSRAM.

Consultá [la arquitectura](docs/ARCHITECTURE.md), el
[contrato JSON](docs/JSON_SCHEMA_V1.md) y el
[estado público](docs/ROADMAP.md).

## Privacidad y seguridad

Nunca subas `secrets.yaml`, tokens de Home Assistant ni mapas con entidades
reales. El ejemplo publicado contiene identificadores genéricos y ninguna
credencial.

## Licencia

Código distribuido bajo licencia MIT. La fuente Material Design Icons conserva
su licencia correspondiente en `fonts/MATERIAL_DESIGN_ICONS_LICENSE.txt`.
