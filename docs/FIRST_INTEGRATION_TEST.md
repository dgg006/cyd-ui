# Primera prueba de la integración CYD UI

Estado: paquete de desarrollo; no es todavía una publicación HACS.

## Alcance seguro de la primera prueba

1. Instalar `custom_components/cyd_ui` en Home Assistant.
2. Reiniciar Home Assistant.
3. Añadir **CYD UI** desde **Ajustes → Dispositivos y servicios**.
4. Abrir el panel lateral **CYD UI**.
5. Importar el proyecto preparado y comprobar páginas, entidades y vista previa.
6. Guardar una revisión y volver a abrir el panel.

Hasta terminar esas comprobaciones no se debe pulsar **Migrar puente**. La pantalla continuará funcionando mediante las dos automatizaciones temporales actuales.

## Migración posterior

El botón **Migrar puente** muestra una confirmación y ejecuta una transferencia reversible:

1. Guarda qué automatizaciones temporales estaban activas.
2. Desactiva primero la automatización que ejecuta comandos.
3. Inicia el puente nativo.
4. Desactiva la sincronización temporal de estados.
5. Persiste la nueva propiedad del puente.

Si un paso falla, el proceso detiene el puente nuevo y restaura las automatizaciones que estaban activas. El mismo botón permite volver deliberadamente al puente temporal.

## Límites actuales

- Guardar desde el panel de Home Assistant todavía no ordena recargar la configuración dinámica de la CYD.
- Sonido de prueba, telemetría LDR y calibración táctil continúan disponibles en el configurador local.
- La instalación HACS pública requiere definir repositorio, propietario, licencia, marca y release.
- La fuente con caracteres españoles se incorporará en la próxima carga de firmware.
