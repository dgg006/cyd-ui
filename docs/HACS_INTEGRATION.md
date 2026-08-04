# Integración de Home Assistant y distribución por HACS

Estado: desarrollo 0.2.2, validado en la instancia doméstica del proyecto; todavía no publicado para usuarios finales.

## Estado actual

La integración ya guarda el editor, aplica la configuración al panel por la
API nativa de ESPHome y mantiene los estados mediante el puente nativo. La
versión del recurso web se mantiene sincronizada con `manifest.json`: cada
actualización cambia esa versión para que Home Assistant y el teléfono no usen
una copia antigua del editor desde la caché del navegador.

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
- Almacenamiento atómico en `.storage/cyd_ui.config` con diez revisiones anteriores.
- Comandos WebSocket administrativos para leer y guardar el proyecto completo.
- Catálogo de entidades consultado directamente desde el estado interno de Home Assistant, sin token externo.
- Validación estructural y límite de tamaño antes de cada guardado.
- Editor visual reutilizado dentro del panel de Home Assistant, aislado mediante Shadow DOM para no alterar el resto de la interfaz.
- Importación inicial de la configuración de desarrollo incluida en el paquete de prueba.
- Traductor nativo de acciones y estados implementado con lista positiva de servicios.
- Puente nativo activo: aplica la configuración guardada y sincroniza los estados actuales al iniciar o reconectar la CYD.
- Migración reversible: libera primero el procesamiento de comandos, inicia el puente nativo y conserva el estado previo de las automatizaciones para poder restaurarlo.
- La eliminación permanente de la integración restaura el puente temporal antes de retirar el almacenamiento administrado.
- Limpieza del panel y del recurso al descargar la entrada.

Los recursos del editor se regeneran desde el configurador local probado con:

```powershell
py -3.13 tools\build_ha_frontend.py
```

Una prueba automática comprueba que el proyecto importable y el catálogo de iconos coincidan con sus fuentes actuales.

El archivo raíz `hacs.json` declara el repositorio como integración y fija Home Assistant 2026.7 como versión mínima.

## Antes de publicar

- Añadir iconos de marca locales.
- Validar físicamente la resincronización automática tras reiniciar o reconectar la CYD en la red doméstica.
- Sustituir el proyecto inicial personal por un asistente genérico antes de publicar el repositorio.
- Incorporar pruebas bajo Home Assistant y ejecutar Hassfest y la validación de HACS.
- Crear una versión y un GitHub Release.
- Probar instalación, actualización, descarga y recuperación en una instancia separada.

La integración ESPHome oficial sigue siendo responsable de la conexión cifrada con la CYD. Antes de una publicación general faltan pruebas de instalación en una instancia limpia, una configuración inicial genérica y la validación formal de HACS.
