import json
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import paho.mqtt.client as mqtt
import websocket


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQTT_BROKER = "192.168.31.240"
MQTT_PORT = 1883
COMMAND_TOPIC = "esphome_ui/cyd-ui/cmd"
EVENT_TOPIC = "esphome_ui/cyd-ui/event"
POLL_SECONDS = 15.0
_FETCH_ENTITY = object()
ALLOWED_SOUNDS = {"attention", "notification", "success", "warning", "error"}


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
    latest_entities = {}
    mqtt_connected = threading.Event()

    client = mqtt.Client(client_id="cyd-ui-ha-bridge", clean_session=True)
    client.username_pw_set(mqtt_username, mqtt_password)

    def format_value(mapping, value):
        if value is None:
            return ""
        value_map = mapping.get("value_map", {})
        if str(value) in value_map:
            return str(value_map[str(value)])
        if "decimals" in mapping:
            return f"{float(value):.{int(mapping['decimals'])}f}"
        return str(value)

    def publish_state(control_id, force=False, entity=_FETCH_ENTITY):
        mapping = backend_map[control_id]
        if mapping.get("publish_state") is False:
            return
        try:
            if "static_value" in mapping:
                state = mapping["static_value"]
                event = {"type": "control_changed", "id": control_id, "active": False,
                         "value": state, "reliability": "valid"}
            elif "static_active" in mapping:
                event = {"type": "control_changed", "id": control_id,
                         "active": bool(mapping["static_active"]), "value": "", "reliability": "valid"}
            else:
                if entity is _FETCH_ENTITY:
                    entity = ha_request(ha_base_url, ha_token, f"/api/states/{mapping['entity_id']}")
                if entity is None:
                    raise OSError("Entidad no disponible")
                state = entity["state"]
                unavailable = state in ("unknown", "unavailable")
                if "attribute" in mapping:
                    attribute_value = entity.get("attributes", {}).get(mapping["attribute"])
                    value = format_value(mapping, attribute_value)
                    unavailable = unavailable or attribute_value is None
                    active = False
                else:
                    value = format_value(mapping, state) if mapping.get("value_only") else ""
                    active = state not in ("off", "unknown", "unavailable") if mapping.get("state_active") else state == "on"
                event = {
                    "type": "control_changed",
                    "id": control_id,
                    "active": active,
                    "value": value,
                    "reliability": "unavailable" if unavailable else "valid",
                }
        except (OSError, KeyError, urllib.error.HTTPError, urllib.error.URLError):
            event = {
                "type": "control_changed",
                "id": control_id,
                "active": False,
                "value": "",
                "reliability": "unavailable",
            }

        signature = (event["active"], event.get("value", ""), event["reliability"])
        if force or last_states.get(control_id) != signature:
            client.publish(EVENT_TOPIC, json.dumps(event, separators=(",", ":")), qos=1)
            last_states[control_id] = signature
            print(f"estado {control_id}: active={event['active']} value={event.get('value', '')} reliability={event['reliability']}", flush=True)

    def publish_all(force=False):
        entity_cache = {}
        for mapping in backend_map.values():
            entity_id = mapping.get("entity_id")
            if not entity_id or mapping.get("publish_state") is False or entity_id in entity_cache:
                continue
            try:
                entity_cache[entity_id] = ha_request(ha_base_url, ha_token, f"/api/states/{entity_id}")
                latest_entities[entity_id] = entity_cache[entity_id]
            except (OSError, urllib.error.HTTPError, urllib.error.URLError):
                entity_cache[entity_id] = None

        for control_id, mapping in backend_map.items():
            entity_id = mapping.get("entity_id")
            entity = entity_cache.get(entity_id, _FETCH_ENTITY) if entity_id else _FETCH_ENTITY
            publish_state(control_id, force=force, entity=entity)

    def publish_entity(entity_id, entity, force=False):
        latest_entities[entity_id] = entity
        for control_id, mapping in backend_map.items():
            if mapping.get("entity_id") == entity_id:
                publish_state(control_id, force=force, entity=entity)

    def publish_attribute_value(entity_id, attribute, value, force=True):
        cached = latest_entities.get(entity_id)
        if cached is not None:
            cached.setdefault("attributes", {})[attribute] = value
        synthetic = {"state": cached.get("state", "off") if cached else "off",
                     "attributes": {attribute: value}}
        for control_id, mapping in backend_map.items():
            if mapping.get("entity_id") == entity_id and mapping.get("attribute") == attribute:
                publish_state(control_id, force=force, entity=synthetic)

    def websocket_worker():
        ws_url = re.sub(r"^https://", "wss://", ha_base_url) + "/api/websocket"
        while True:
            ws = None
            try:
                ws = websocket.create_connection(ws_url, timeout=20)
                ws.recv()  # auth_required
                ws.send(json.dumps({"type": "auth", "access_token": ha_token}))
                auth_result = json.loads(ws.recv())
                if auth_result.get("type") != "auth_ok":
                    raise RuntimeError("Home Assistant rechazo la autenticacion WebSocket")
                ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"}))
                ws.recv()  # result de la suscripcion
                ws.send(json.dumps({"id": 2, "type": "subscribe_events", "event_type": "call_service"}))
                ws.recv()  # result de la suscripcion
                ws.send(json.dumps({"id": 3, "type": "subscribe_events", "event_type": "cyd_ui_sound"}))
                ws.recv()  # result de la suscripcion
                print("Eventos de Home Assistant en tiempo real conectados", flush=True)

                while True:
                    message = json.loads(ws.recv())
                    if message.get("type") != "event":
                        continue
                    event = message.get("event", {})
                    data = event.get("data", {})
                    mqtt_connected.wait()
                    if event.get("event_type") == "state_changed":
                        entity_id = data.get("entity_id")
                        entity = data.get("new_state")
                        if entity_id and entity:
                            publish_entity(entity_id, entity)
                    elif (event.get("event_type") == "call_service"
                          and data.get("domain") == "climate"
                          and data.get("service") == "set_temperature"):
                        service_data = data.get("service_data", {})
                        target = data.get("target", {})
                        entity_ids = service_data.get("entity_id", target.get("entity_id", []))
                        if isinstance(entity_ids, str):
                            entity_ids = [entity_ids]
                        temperature = service_data.get("temperature")
                        if temperature is not None:
                            for entity_id in entity_ids:
                                publish_attribute_value(entity_id, "temperature", temperature)
                    elif event.get("event_type") == "cyd_ui_sound":
                        sound = data.get("sound", "notification")
                        if sound in ALLOWED_SOUNDS:
                            client.publish(
                                EVENT_TOPIC,
                                json.dumps({"type": "sound", "sound": sound}, separators=(",", ":")),
                                qos=1,
                            )
                            print(f"sonido solicitado por Home Assistant: {sound}", flush=True)
                        else:
                            print(f"sonido de Home Assistant ignorado: {sound}", flush=True)
            except Exception as error:
                print(f"Canal en tiempo real desconectado; reintento en 3 s: {error}", flush=True)
                time.sleep(3)
            finally:
                if ws is not None:
                    ws.close()

    def on_connect(client, userdata, flags, result_code):
        if result_code != 0:
            raise RuntimeError(f"MQTT rechazo la conexion: {result_code}")
        client.subscribe(COMMAND_TOPIC, qos=1)
        mqtt_connected.set()
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
    threading.Thread(target=websocket_worker, daemon=True).start()

    try:
        next_poll = 0.0
        while True:
            try:
                command = commands.get(timeout=0.1)
                if command.get("type") == "sync_request":
                    publish_all(force=True)
                elif command.get("type") == "action":
                    control_id = command.get("id")
                    mapping = backend_map.get(control_id)
                    if (mapping and mapping.get("allow_control") is True
                            and mapping.get("entity_id")
                            and command.get("action") == mapping.get("action")):
                        requested_service = mapping.get("service", mapping["action"])
                        if requested_service == "set_temperature":
                            entity = latest_entities.get(mapping["entity_id"])
                            if entity is None:
                                entity = ha_request(ha_base_url, ha_token, f"/api/states/{mapping['entity_id']}")
                            attributes = entity.get("attributes", {})
                            current_target = float(attributes["temperature"])
                            new_target = current_target + float(mapping["temperature_delta"])
                            new_target = max(float(attributes.get("min_temp", new_target)), new_target)
                            new_target = min(float(attributes.get("max_temp", new_target)), new_target)
                            payload = {"entity_id": mapping["entity_id"], "temperature": new_target}
                            service = requested_service
                        elif requested_service == "set_cover_position":
                            entity = latest_entities.get(mapping["entity_id"])
                            if entity is None:
                                entity = ha_request(ha_base_url, ha_token, f"/api/states/{mapping['entity_id']}")
                            current_position = float(entity.get("attributes", {}).get("current_position", 0))
                            new_position = max(0.0, min(100.0, current_position + float(mapping["position_delta"])))
                            payload = {"entity_id": mapping["entity_id"], "position": round(new_position)}
                            service = requested_service
                        else:
                            payload = {"entity_id": mapping["entity_id"]}
                            service = requested_service
                        if service == "set_temperature":
                            publish_attribute_value(mapping["entity_id"], "temperature", new_target)
                        elif service == "set_cover_position":
                            publish_attribute_value(mapping["entity_id"], "current_position", round(new_position))
                        ha_request(ha_base_url, ha_token,
                                   f"/api/services/{mapping['domain']}/{service}",
                                   method="POST", payload=payload)
                        if service != "set_temperature":
                            time.sleep(0.25)
                            entity = ha_request(ha_base_url, ha_token, f"/api/states/{mapping['entity_id']}")
                            publish_entity(mapping["entity_id"], entity, force=True)
            except queue.Empty:
                pass

            if time.monotonic() >= next_poll:
                publish_all()
                next_poll = time.monotonic() + POLL_SECONDS
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
