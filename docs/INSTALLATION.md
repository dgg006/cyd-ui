# Instalación experimental

## Home Assistant mediante HACS

1. Instalá HACS si todavía no está disponible.
2. En HACS, abrí **Repositorios personalizados**.
3. Añadí `https://github.com/dgg006/cyd-ui` como **Integración**.
4. Descargá CYD UI y reiniciá Home Assistant.
5. Añadí la integración desde **Ajustes → Dispositivos y servicios**.
6. Abrí el panel lateral **CYD UI**.

La integración administra el editor y sus datos. El firmware de la pantalla se
compila e instala mediante ESPHome.

## ESPHome

1. Instalá ESPHome 2026.7 o posterior.
2. Copiá `secrets.example.yaml` como `secrets.yaml`.
3. Generá claves propias y completá Wi-Fi, MQTT y la URL de configuración.
4. Editá `examples/project.example.json` o importalo desde el editor.
5. Ejecutá:

```powershell
esphome run cyd-ui.yaml
```

## Recuperación

Si la red configurada no está disponible, la CYD crea el punto de acceso
`CYD UI Setup`. El ejemplo usa `12345678`; cambialo antes de una instalación
permanente y mantené sincronizado el texto mostrado por el firmware.

La última configuración validada permanece en flash si el servidor de
configuración o Home Assistant no están disponibles.

