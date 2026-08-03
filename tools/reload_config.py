import json
import re
from pathlib import Path

import paho.mqtt.publish as publish


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQTT_BROKER = "192.168.31.240"
MQTT_PORT = 1883
EVENT_TOPIC = "esphome_ui/cyd-ui/event"


def read_secret(name):
    text = (PROJECT_ROOT / "secrets.yaml").read_text(encoding="utf-8")
    match = re.search(rf"(?m)^{name}:\s*[\"']?([^\"'\r\n]+)", text)
    if not match:
        raise RuntimeError(f"Falta {name} en secrets.yaml")
    return match.group(1).strip()


publish.single(
    EVENT_TOPIC,
    payload=json.dumps({"type": "reload"}, separators=(",", ":")),
    qos=1,
    hostname=MQTT_BROKER,
    port=MQTT_PORT,
    auth={
        "username": read_secret("mqtt_username"),
        "password": read_secret("mqtt_password"),
    },
)
print("Recarga de configuracion enviada")
