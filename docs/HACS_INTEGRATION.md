# Integración de Home Assistant y distribución por HACS

Estado: bootstrap 0.1.0, todavía no instalable para usuarios finales.

## Objetivo

La parte de Home Assistant se distribuirá como una integración personalizada mediante HACS. El firmware continuará instalándose mediante ESPHome Device Builder o un instalador web de firmware.

La integración deberá asumir progresivamente estas responsabilidades:

1. Registrar `CYD UI` en **Ajustes → Dispositivos y servicios**.
2. Mostrar el editor como panel administrativo en la barra lateral.
3. Guardar `ui.json` y `backend-map.json` dentro del almacenamiento administrado por Home Assistant.
4. Consultar directamente entidades, atributos y servicios sin usar un token externo.
5. Traducir pulsaciones y sincronizar estados sin automatizaciones generadas.
6. Entregar configuración a cada panel y conservar versiones recuperables.

## Bootstrap implementado

La carpeta `custom_components/cyd_ui` contiene:

- `manifest.json` con `config_flow` y entrada única.
- Flujo gráfico sin YAML.
- Traducciones en español e inglés.
- Panel administrativo `CYD UI`.
- Recurso JavaScript servido por la propia integración.
- Comando WebSocket autenticado `cyd_ui/status`.
- Limpieza del panel y del recurso al descargar la entrada.

El archivo raíz `hacs.json` declara el repositorio como integración y fija Home Assistant 2026.7 como versión mínima.

## Antes de publicar

- Elegir propietario y URL definitiva del repositorio; reemplazar `OWNER` en `manifest.json`.
- Añadir iconos de marca locales.
- Incorporar pruebas bajo Home Assistant y ejecutar Hassfest y la validación de HACS.
- Crear una versión y un GitHub Release.
- Probar instalación, actualización, descarga y recuperación en una instancia separada.

No se instalará este bootstrap en el Home Assistant doméstico hasta completar como mínimo las pruebas de carga y descarga. La integración ESPHome oficial sigue siendo responsable de la conexión cifrada con la CYD.
