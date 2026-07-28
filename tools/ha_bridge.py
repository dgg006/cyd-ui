import json
import queue
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import paho.mqtt.client as mqtt


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQTT_BROKER = "192.168.31.240"
MQTT_PORT = 1883
COMMAND_TOPIC = "esphome_ui/cyd-ui/cmd"
EVENT_TOPIC = "esphome_ui/cyd-ui/event"
POLL_SECONDS = 1.0


def read_mqtt_secrets():
    text = (PROJECT_ROOT / "secrets.yaml").read_text(encoding="utf-8")

    def value(name):
        match = re.search(rf"(?m)^{name}:\s*[\"']?([^\"'\r\n]+)", text)
        if not match:
            raise RuntimeError(f"Falta {name} en secrets.yaml")
        return match.group(1).strip()

    return value("mqtt_username"), value("mqtt_password")


def read_ha_access():
    path = Path.home() / "Desktop" / "Nabu Casa.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    base_url = next(line.strip().rstrip("/") for line in lines if line.strip().startswith("https://"))
    token_line = next(line for line in lines if "token" in line.lower())
    token = token_line.split(":", 1)[1].strip()
    return base_url, token


def ha_request(base_url, token, path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        return json.loads(body) if body else None


def main():
    mqtt_username, mqtt_password = read_mqtt_secrets()
    ha_base_url, ha_token = read_ha_access()
    backend_map = json.loads((PROJECT_ROOT / "config" / "backend-map.json").read_text(encoding="utf-8"))["controls"]
    commands = queue.Queue()
    last_states = {}

    client = mqtt.Client(client_id="cyd-ui-ha-bridge", clean_session=True)
    client.username_pw_set(mqtt_username, mqtt_password)

    def publish_state(control_id, force=False):
        mapping = backend_map[control_id]
        try:
            state = ha_request(ha_base_url, ha_token, f"/api/states/{mapping['entity_id']}")["state"]
            event = {
                "type": "control_changed",
                "id": control_id,
                "active": state == "on",
                "reliability": "unavailable" if state in ("unknown", "unavailable") else "valid",
            }
        except (OSError, KeyError, urllib.error.HTTPError, urllib.error.URLError):
            event = {
                "type": "control_changed",
                "id": control_id,
                "active": False,
                "reliability": "unavailable",
            }

        signature = (event["active"], event["reliability"])
        if force or last_states.get(control_id) != signature:
            client.publish(EVENT_TOPIC, json.dumps(event, separators=(",", ":")), qos=1)
            last_states[control_id] = signature
            print(f"estado {control_id}: active={event['active']} reliability={event['reliability']}", flush=True)

    def on_connect(client, userdata, flags, result_code):
        if result_code != 0:
            raise RuntimeError(f"MQTT rechazo la conexion: {result_code}")
        client.subscribe(COMMAND_TOPIC, qos=1)
        print("Puente HA bidireccional conectado", flush=True)

    def on_message(client, userdata, message):
        try:
            commands.put(json.loads(message.payload.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError):
            print("Comando MQTT invalido ignorado", flush=True)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=30)
    client.loop_start()

    try:
        next_poll = 0.0
        while True:
            try:
                command = commands.get(timeout=0.1)
                if command.get("type") == "sync_request":
                    for control_id in backend_map:
                        publish_state(control_id, force=True)
                elif command.get("type") == "action":
                    control_id = command.get("id")
                    mapping = backend_map.get(control_id)
                    if mapping and command.get("action") == mapping.get("action"):
                        ha_request(
                            ha_base_url,
                            ha_token,
                            f"/api/services/{mapping['domain']}/{mapping['action']}",
                            method="POST",
                            payload={"entity_id": mapping["entity_id"]},
                        )
                        time.sleep(0.25)
                        publish_state(control_id, force=True)
            except queue.Empty:
                pass

            if time.monotonic() >= next_poll:
                for control_id in backend_map:
                    publish_state(control_id)
                next_poll = time.monotonic() + POLL_SECONDS
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
