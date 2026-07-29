from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import paho.mqtt.publish as mqtt_publish
import paho.mqtt.client as mqtt_client


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = Path(__file__).resolve().parent / "static"
ICON_CATALOG_PATH = PROJECT_ROOT / "components" / "ui_engine" / "icons.json"
MDI_FONT_PATH = PROJECT_ROOT / "fonts" / "materialdesignicons-webfont.ttf"
CONFIG_PATH = PROJECT_ROOT / "config" / "ui.json"
BACKEND_MAP_PATH = PROJECT_ROOT / "config" / "backend-map.json"
HISTORY_ROOT = PROJECT_ROOT / "config" / "history"
SECRETS_PATH = PROJECT_ROOT / "secrets.yaml"
HA_ACCESS_PATH = Path.home() / "Desktop" / "Nabu Casa.txt"

MQTT_BROKER = "192.168.31.240"
MQTT_PORT = 1883
EVENT_TOPIC = "esphome_ui/cyd-ui/event"
LDR_TOPIC = "esphome_ui/cyd-ui/telemetry/ldr_voltage"
MAX_BODY_BYTES = 512 * 1024
MAX_PAGES = 8
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
ICON_CATALOG = json.loads(ICON_CATALOG_PATH.read_text(encoding="utf-8"))
ICON_NAMES = {item["name"] for item in ICON_CATALOG}
IDLE_MODES = {"clock_weather", "screen_off", "dim", "none"}
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    "button_grid": {
        "label": "Botones",
        "variants": {"two_buttons": 2, "four_buttons": 4, "six_buttons": 6},
        "controls": {"kind": "repeated", "type": "button"},
    },
    "climate": {
        "label": "Climatización",
        "variants": {"thermostat": 5},
        "controls": {"kind": "fixed", "roles": [
            {"role": "current_temperature", "type": "value", "caption": "Actual"},
            {"role": "target_temperature", "type": "value", "caption": "Objetivo"},
            {"role": "decrease", "type": "button", "caption": "-", "action": "decrement"},
            {"role": "power", "type": "button", "caption": "Estado", "action": "toggle"},
            {"role": "increase", "type": "button", "caption": "+", "action": "increment"},
        ]},
    },
    "clock_weather": {
        "label": "Reloj y clima", "variants": {"screensaver": 3}, "screensaver": True,
        "controls": {"kind": "fixed", "roles": [
            {"role": "condition", "type": "value", "caption": "Estado"},
            {"role": "outside_temperature", "type": "value", "caption": "Exterior"},
            {"role": "humidity", "type": "value", "caption": "Humedad"},
        ]},
    },
    "sensor_grid": {
        "label": "Sensores", "variants": {"four_values": 4},
        "controls": {"kind": "variable", "type": "value", "minimum": 1, "maximum": 4},
    },
    "cover": {
        "label": "Cortina", "variants": {"position_controls": 6},
        "controls": {"kind": "fixed", "roles": [
            {"role": "position", "type": "value", "caption": "Posición"},
            {"role": "state", "type": "value", "caption": "Estado"},
            {"role": "open", "type": "button", "caption": "Abrir todo", "action": "open"},
            {"role": "close", "type": "button", "caption": "Cerrar todo", "action": "close"},
            {"role": "close_step", "type": "button", "caption": "Cerrar 10%", "action": "close_step"},
            {"role": "open_step", "type": "button", "caption": "Abrir 10%", "action": "open_step"},
        ]},
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def yaml_secret(name: str) -> str:
    text = SECRETS_PATH.read_text(encoding="utf-8")
    match = re.search(rf"(?m)^{re.escape(name)}:\s*[\"']?([^\"'\r\n]+)", text)
    if not match:
        raise RuntimeError(f"Falta {name} en secrets.yaml")
    return match.group(1).strip()


def ha_access() -> tuple[str, str]:
    lines = HA_ACCESS_PATH.read_text(encoding="utf-8").splitlines()
    base_url = next(line.strip().rstrip("/") for line in lines if line.strip().startswith("https://"))
    token_line = next(line for line in lines if "token" in line.lower())
    return base_url, token_line.split(":", 1)[1].strip()


def fetch_ha_entities() -> list[dict[str, Any]]:
    base_url, token = ha_access()
    request = urllib.request.Request(
        f"{base_url}/api/states",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        states = json.loads(response.read())
    entities = []
    for state in states:
        entity_id = state.get("entity_id", "")
        attributes = state.get("attributes", {})
        attribute_values = {
            key: value
            for key, value in attributes.items()
            if isinstance(value, (str, int, float, bool)) and not isinstance(value, (dict, list))
        }
        entities.append({
            "entity_id": entity_id,
            "domain": entity_id.partition(".")[0],
            "name": attributes.get("friendly_name", entity_id),
            "state": state.get("state", ""),
            "device_class": attributes.get("device_class", ""),
            "unit": attributes.get("unit_of_measurement", ""),
            "attributes": sorted(attributes.keys()),
            "attribute_values": attribute_values,
        })
    return sorted(entities, key=lambda item: (item["domain"], item["name"].casefold()))


def validate_project(ui: Any, backend_map: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(ui, dict):
        return ["La configuración debe ser un objeto JSON."]
    if ui.get("schema_version") != 1:
        errors.append("schema_version debe ser 1.")
    timeout = ui.get("screensaver_timeout", 30)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 0 <= timeout <= 3600:
        errors.append("El tiempo del protector debe estar entre 0 y 3600 segundos.")
    settings = ui.get("settings", {})
    if not isinstance(settings, dict):
        errors.append("Configuración: settings debe ser un objeto.")
        settings = {}
    display = settings.get("display", {})
    inactivity = settings.get("inactivity", {})
    night = settings.get("night", {})
    sound = settings.get("sound", {})
    for name, section in (("pantalla", display), ("inactividad", inactivity), ("noche", night), ("sonido", sound)):
        if not isinstance(section, dict):
            errors.append(f"Configuración de {name}: debe ser un objeto.")
    if all(isinstance(section, dict) for section in (display, inactivity, night, sound)):
        for key in ("brightness", "minimum_brightness", "maximum_brightness"):
            value = display.get(key)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100):
                errors.append(f"Pantalla: {key} debe estar entre 0 y 100.")
        if display.get("minimum_brightness", 15) > display.get("maximum_brightness", 100):
            errors.append("Pantalla: el brillo mínimo no puede superar el máximo.")
        if "auto_brightness" in display and not isinstance(display["auto_brightness"], bool):
            errors.append("Pantalla: auto_brightness debe ser sí o no.")
        dark, bright = display.get("ldr_dark_voltage", 3.0), display.get("ldr_bright_voltage", 0.2)
        if (not isinstance(dark, (int, float)) or isinstance(dark, bool) or
                not isinstance(bright, (int, float)) or isinstance(bright, bool) or
                not 0 <= dark <= 3.3 or not 0 <= bright <= 3.3 or dark == bright):
            errors.append("Pantalla: la calibración LDR debe usar dos valores distintos entre 0 y 3,3 V.")
        idle_timeout = inactivity.get("timeout", timeout)
        if not isinstance(idle_timeout, int) or isinstance(idle_timeout, bool) or not 0 <= idle_timeout <= 3600:
            errors.append("Inactividad: el tiempo debe estar entre 0 y 3600 segundos.")
        if inactivity.get("mode", "clock_weather") not in IDLE_MODES:
            errors.append("Inactividad: modo desconocido.")
        dim = inactivity.get("dim_brightness", 10)
        if not isinstance(dim, int) or isinstance(dim, bool) or not 0 <= dim <= 100:
            errors.append("Inactividad: el brillo tenue debe estar entre 0 y 100.")
        if "enabled" in night and not isinstance(night["enabled"], bool):
            errors.append("Horario nocturno: enabled debe ser sí o no.")
        for key in ("start", "end"):
            value = night.get(key, "23:00" if key == "start" else "07:00")
            if not isinstance(value, str) or not TIME_PATTERN.fullmatch(value):
                errors.append(f"Horario nocturno: {key} debe usar HH:MM.")
        night_brightness = night.get("brightness", 15)
        if not isinstance(night_brightness, int) or isinstance(night_brightness, bool) or not 0 <= night_brightness <= 100:
            errors.append("Horario nocturno: el brillo debe estar entre 0 y 100.")
        if night.get("mode", "screen_off") not in IDLE_MODES:
            errors.append("Horario nocturno: modo desconocido.")
        for key in ("enabled", "touch", "navigation", "notifications"):
            if key in sound and not isinstance(sound[key], bool):
                errors.append(f"Sonido: {key} debe ser sí o no.")
        volume = sound.get("volume", 5)
        if not isinstance(volume, int) or isinstance(volume, bool) or not 0 <= volume <= 10:
            errors.append("Sonido: el volumen debe estar entre 0 y 10.")
    pages = ui.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        return errors + [f"Debe haber entre 1 y {MAX_PAGES} páginas."]
    mappings = backend_map.get("controls") if isinstance(backend_map, dict) else None
    if not isinstance(mappings, dict):
        errors.append("El mapa de backend debe contener un objeto controls.")
        mappings = {}
    ids: set[str] = set()
    screensavers = 0
    for page_index, page in enumerate(pages, start=1):
        prefix = f"Página {page_index}"
        if not isinstance(page, dict):
            errors.append(f"{prefix}: debe ser un objeto.")
            continue
        template_name = page.get("template")
        catalog = TEMPLATE_CATALOG.get(template_name)
        if catalog is None:
            errors.append(f"{prefix}: template desconocido '{template_name}'.")
            continue
        variant = page.get("variant")
        expected_count = catalog["variants"].get(variant)
        if expected_count is None:
            errors.append(f"{prefix}: variante '{variant}' no admitida.")
        title_optional = template_name == "clock_weather" and variant == "screensaver"
        if not isinstance(page.get("title", ""), str) or (not title_optional and not page["title"].strip()):
            errors.append(f"{prefix}: el título es obligatorio salvo en el protector.")
        if page.get("screensaver") is True:
            screensavers += 1
            if template_name != "clock_weather":
                errors.append(f"{prefix}: solo clock_weather puede ser protector de pantalla.")
        controls = page.get("controls")
        if not isinstance(controls, list) or not 1 <= len(controls) <= 6:
            errors.append(f"{prefix}: debe contener entre 1 y 6 controles.")
            continue
        kind = catalog["controls"]["kind"]
        if kind in {"fixed", "repeated"} and expected_count is not None and len(controls) != expected_count:
            errors.append(f"{prefix}: la variante requiere {expected_count} controles.")
        if kind == "variable":
            minimum, maximum = catalog["controls"]["minimum"], catalog["controls"]["maximum"]
            if not minimum <= len(controls) <= maximum:
                errors.append(f"{prefix}: admite entre {minimum} y {maximum} controles.")
        expected_roles = {item["role"]: item["type"] for item in catalog["controls"].get("roles", [])}
        seen_roles: set[str] = set()
        for control_index, control in enumerate(controls, start=1):
            label = f"{prefix}, control {control_index}"
            if not isinstance(control, dict):
                errors.append(f"{label}: debe ser un objeto.")
                continue
            control_id = control.get("id", "")
            if not isinstance(control_id, str) or not ID_PATTERN.fullmatch(control_id):
                errors.append(f"{label}: ID inválido; use minúsculas, números y guion bajo.")
            elif control_id in ids:
                errors.append(f"{label}: el ID '{control_id}' está repetido.")
            else:
                ids.add(control_id)
            if not isinstance(control.get("caption"), str) or not control["caption"].strip():
                errors.append(f"{label}: el texto visible es obligatorio.")
            if control.get("type") not in {"button", "value"}:
                errors.append(f"{label}: type debe ser button o value.")
            if not COLOR_PATTERN.fullmatch(str(control.get("color", ""))):
                errors.append(f"{label}: color debe tener formato #RRGGBB.")
            for icon_field in ("icon", "icon_on", "icon_off"):
                icon_name = control.get(icon_field, "")
                if not isinstance(icon_name, str) or (icon_name and icon_name not in ICON_NAMES):
                    errors.append(f"{label}: {icon_field} no es un icono MDI admitido.")
            role = control.get("role", "")
            if expected_roles:
                if role not in expected_roles:
                    errors.append(f"{label}: role '{role}' no admitido.")
                elif control.get("type") != expected_roles[role]:
                    errors.append(f"{label}: role '{role}' requiere type={expected_roles[role]}.")
                seen_roles.add(role)
            # Un control puede quedar sin backend durante el diseño. El editor crea
            # una asociación vacía al abrirlo y el bridge simplemente lo ignora.
        missing_roles = set(expected_roles) - seen_roles
        if missing_roles:
            errors.append(f"{prefix}: faltan roles {', '.join(sorted(missing_roles))}.")
    if screensavers > 1:
        errors.append("Solo puede existir un protector de pantalla.")
    unused_mappings = sorted(set(mappings) - ids)
    if unused_mappings:
        errors.append("Hay asociaciones sin control: " + ", ".join(unused_mappings))
    for control_id in ids:
        mapping = mappings.get(control_id)
        if not isinstance(mapping, dict):
            continue
        entity_id = mapping.get("entity_id", "")
        if entity_id and not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", str(entity_id)):
            errors.append(f"La entidad de '{control_id}' no es un ID válido de Home Assistant.")
    return errors


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def backup_current() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = HISTORY_ROOT / stamp
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(CONFIG_PATH, destination / CONFIG_PATH.name)
    shutil.copy2(BACKEND_MAP_PATH, destination / BACKEND_MAP_PATH.name)
    return stamp


def publish_event(event: dict[str, Any]) -> None:
    mqtt_publish.single(EVENT_TOPIC, payload=json.dumps(event, separators=(",", ":")), qos=1,
                        hostname=MQTT_BROKER, port=MQTT_PORT,
                        auth={"username": yaml_secret("mqtt_username"), "password": yaml_secret("mqtt_password")})


def publish_reload() -> None:
    publish_event({"type": "reload"})


def read_ldr_voltage(timeout: float = 2.0) -> float | None:
    """Read the retained LDR telemetry without ever blocking the editor indefinitely."""
    result: dict[str, float] = {}
    received = threading.Event()
    client = mqtt_client.Client()
    client.username_pw_set(yaml_secret("mqtt_username"), yaml_secret("mqtt_password"))

    def on_connect(active_client: mqtt_client.Client, _userdata: Any, _flags: Any, return_code: int) -> None:
        if return_code == 0:
            active_client.subscribe(LDR_TOPIC, qos=0)
        else:
            received.set()

    def on_message(_client: mqtt_client.Client, _userdata: Any, message: Any) -> None:
        try:
            result["value"] = float(message.payload.decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            pass
        finally:
            received.set()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=10)
    client.loop_start()
    try:
        received.wait(timeout)
    finally:
        client.loop_stop()
        client.disconnect()
    return result.get("value")


class ConfiguratorHandler(SimpleHTTPRequestHandler):
    server_version = "CydUiConfigurator/0.1"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def json_response(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("Tamaño de solicitud inválido.")
        return json.loads(self.rfile.read(length))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/project":
            self.json_response({"ui": read_json(CONFIG_PATH), "backend_map": read_json(BACKEND_MAP_PATH)})
            return
        if parsed.path == "/api/catalog":
            self.json_response(TEMPLATE_CATALOG)
            return
        if parsed.path == "/api/icons":
            self.json_response({"icons": ICON_CATALOG})
            return
        if parsed.path == "/assets/materialdesignicons-webfont.ttf":
            body = MDI_FONT_PATH.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "font/ttf")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/entities":
            try:
                self.json_response({"entities": fetch_ha_entities()})
            except (OSError, StopIteration, urllib.error.HTTPError, urllib.error.URLError) as error:
                self.json_response({"error": f"No se pudo consultar Home Assistant: {error}"}, HTTPStatus.BAD_GATEWAY)
            return
        if parsed.path == "/api/device-status":
            try:
                self.json_response({"ldr_voltage": read_ldr_voltage()})
            except Exception as error:
                self.json_response({"ldr_voltage": None, "error": str(error)})
            return
        if parsed.path == "/config/ui.json":
            self.json_response(read_json(CONFIG_PATH))
            return
        super().do_GET()

    def do_POST(self) -> None:
        try:
            payload = self.read_body()
            if self.path == "/api/validate":
                errors = validate_project(payload.get("ui"), payload.get("backend_map"))
                self.json_response({"valid": not errors, "errors": errors})
                return
            if self.path == "/api/save":
                ui, backend_map = payload.get("ui"), payload.get("backend_map")
                errors = validate_project(ui, backend_map)
                if errors:
                    self.json_response({"saved": False, "errors": errors}, HTTPStatus.UNPROCESSABLE_ENTITY)
                    return
                backup = backup_current()
                atomic_write_json(CONFIG_PATH, ui)
                atomic_write_json(BACKEND_MAP_PATH, backend_map)
                reload_error = None
                try:
                    publish_reload()
                except Exception as error:
                    reload_error = str(error)
                self.json_response({"saved": True, "backup": backup, "reload_error": reload_error})
                return
            if self.path == "/api/reload":
                publish_reload()
                self.json_response({"reloaded": True})
                return
            if self.path == "/api/test-sound":
                publish_event({"type": "sound", "sound": "notification"})
                self.json_response({"played": True})
                return
            self.json_response({"error": "Ruta desconocida."}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as error:
            self.json_response({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self.json_response({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Configurador visual local para CYD UI Engine")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8125)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ConfiguratorHandler)
    print(f"Configurador disponible en http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
