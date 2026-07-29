# Configurador visual local

Primera interfaz gráfica para editar `config/ui.json` y `config/backend-map.json` sin tocar el firmware.

```powershell
py -3.13 configurator\server.py
```

Abrir `http://127.0.0.1:8125`.

- Valida el contrato que consume el firmware antes de guardar.
- Conserva una copia en `config/history/<fecha-hora>/`.
- Escribe ambos archivos de forma atómica.
- Ordena una recarga MQTT después de guardar.
- Las credenciales nunca se envían al navegador.
- El protector de pantalla se configura sin título y permite elegir su espera entre `Nunca` y `1 hora`.
- Los atributos muestran nombres legibles y valores de ejemplo obtenidos de Home Assistant; las acciones se eligen según el tipo de entidad.

El servidor de configuración que consume el firmware debe servir la carpeta `config` en el puerto 8124, porque la URL del dispositivo termina en `/ui.json`.
