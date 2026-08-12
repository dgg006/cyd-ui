"""Connect a local CYD to a remote Home Assistant through this PC."""

from __future__ import annotations

import argparse
import asyncio
import copy
import importlib.util
import json
import os
import re
import signal
import socket
import threading
import time
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import websocket
import yaml
from aioesphomeapi import APIClient, HomeassistantServiceCall, UserService


def _load_artwork_processor():
    path = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "cyd_ui"
        / "artwork.py"
    )
    spec = importlib.util.spec_from_file_location("cyd_ui_artwork", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar artwork.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ARTWORK_PROCESSOR = _load_artwork_processor()


class ArtworkProxy:
    """Expose remote Home Assistant artwork to a CYD on the work LAN."""

    def __init__(self, device_host: str, port: int = 45958) -> None:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect((device_host, 9))
            self.local_host = probe.getsockname()[0]
        finally:
            probe.close()
        self.port = port
        self.source_url = ""
        self.background = ARTWORK_PROCESSOR.DARK_ARTWORK_BACKGROUND
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
                if self.path.partition("?")[0] != "/artwork.jpg" or not proxy.source_url:
                    self.send_error(404)
                    return
                try:
                    request = urllib.request.Request(
                        proxy.source_url,
                        headers={"User-Agent": "CYD-UI-Lab-Gateway/1"},
                    )
                    with urllib.request.urlopen(request, timeout=8) as response:
                        content = response.read(256 * 1024 + 1)
                        content_type = response.headers.get_content_type()
                    if len(content) > 256 * 1024 or content_type not in {"image/jpeg", "image/png"}:
                        raise ValueError("carátula no admitida")
                    content = ARTWORK_PROCESSOR.circular_artwork_jpeg(
                        content, size=72, background=proxy.background
                    )
                    content_type = "image/jpeg"
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(content)
                    print(f"Carátula servida a la CYD: {len(content)} bytes", flush=True)
                except Exception as error:  # keep the firmware request bounded
                    self.send_error(502, str(error))

            def log_message(self, _format: str, *_args: Any) -> None:
                return

        self.server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def publish(self, source_url: str, background: str) -> str:
        self.source_url = source_url
        self.background = background
        version = abs(hash((source_url, background))) & 0xFFFFFFFF
        return f"http://{self.local_host}:{self.port}/artwork.jpg?v={version}"


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / "secrets.yaml"
DEFAULT_DEVICE_HOST = "192.168.31.150"
DEFAULT_DEVICE_PORT = 6053
DEFAULT_HOME_ASSISTANT_URL = "http://192.168.68.77:8123"
CONFIG_POLL_SECONDS = 5.0
DEVICE_CONNECT_TIMEOUT_SECONDS = 15.0
DEVICE_DISCONNECT_TIMEOUT_SECONDS = 2.0
RECONNECT_SECONDS = 3.0
REMOTE_BLOCKED_COMMANDS = {("climate", "set_hvac_mode")}
SINGLE_INSTANCE_PORT = 45957


def _load_bridge_model():
    path = PROJECT_ROOT / "custom_components" / "cyd_ui" / "bridge_model.py"
    spec = importlib.util.spec_from_file_location("cyd_ui_bridge_model", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar bridge_model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRIDGE_MODEL = _load_bridge_model()


def _read_desktop_access() -> tuple[str | None, str | None]:
    path = Path.home() / "Desktop" / "Nabu Casa.txt"
    if not path.exists():
        return None, None
    text = path.read_text(encoding="utf-8")
    url_match = re.search(r"https://\S+", text)
    token_match = re.search(r"(?im)^.*token.*?:\s*(\S+)", text)
    return (
        url_match.group(0).rstrip("/") if url_match else None,
        token_match.group(1) if token_match else None,
    )


def read_access() -> tuple[list[str], str, str]:
    secrets = yaml.safe_load(SECRETS_PATH.read_text(encoding="utf-8"))
    api_key = secrets.get("api_encryption_key")
    if not api_key:
        raise RuntimeError("Falta api_encryption_key en secrets.yaml")
    desktop_url, desktop_token = _read_desktop_access()
    token = os.environ.get("HASS_TOKEN") or desktop_token
    if not token:
        raise RuntimeError("Falta HASS_TOKEN o el token en Desktop/Nabu Casa.txt")
    candidates = [DEFAULT_HOME_ASSISTANT_URL]
    for candidate in (os.environ.get("HASS_URL"), desktop_url):
        if candidate and candidate.rstrip("/") not in candidates:
            candidates.append(candidate.rstrip("/"))
    return candidates, token, str(api_key)


def _http_json(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        return json.loads(data) if data else None


def _websocket_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/api/websocket"


def _authenticate_websocket(base_url: str, token: str):
    ws = websocket.create_connection(_websocket_url(base_url), timeout=20)
    hello = json.loads(ws.recv())
    if hello.get("type") != "auth_required":
        ws.close()
        raise RuntimeError("Respuesta WebSocket inesperada de Home Assistant")
    ws.send(json.dumps({"type": "auth", "access_token": token}))
    result = json.loads(ws.recv())
    if result.get("type") != "auth_ok":
        ws.close()
        raise RuntimeError("Home Assistant rechazó la autenticación")
    return ws


def fetch_project(base_url: str, token: str) -> dict[str, Any]:
    ws = _authenticate_websocket(base_url, token)
    try:
        ws.send(json.dumps({"id": 1, "type": "cyd_ui/config/get"}))
        while True:
            message = json.loads(ws.recv())
            if message.get("id") != 1:
                continue
            if not message.get("success"):
                raise RuntimeError(f"CYD UI rechazó config/get: {message.get('error')}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise RuntimeError("CYD UI devolvió un proyecto inválido")
            return result
    finally:
        ws.close()


class HomeAssistantLink:
    """REST plus a state-event WebSocket with endpoint fallback."""

    def __init__(
        self,
        candidates: list[str],
        token: str,
        emit: Callable[[tuple[str, Any]], None],
    ) -> None:
        self._candidates = candidates
        self._token = token
        self._emit = emit
        self._base_url: str | None = None
        self._stop = threading.Event()

    @property
    def base_url(self) -> str:
        if self._base_url is None:
            self._base_url = self._select_endpoint()
        return self._base_url

    def _select_endpoint(self) -> str:
        errors: list[str] = []
        for candidate in self._candidates:
            try:
                result = _http_json(candidate, self._token, "/api/", timeout=6)
                if isinstance(result, dict) and result.get("message") == "API running.":
                    return candidate.rstrip("/")
            except Exception as error:
                errors.append(f"{candidate}: {error}")
        raise RuntimeError("Home Assistant no accesible. " + " | ".join(errors))

    def start(self) -> None:
        threading.Thread(
            target=self._event_worker, name="cyd-ha-events", daemon=True
        ).start()
        threading.Thread(
            target=self._heartbeat_worker, name="cyd-ha-heartbeat", daemon=True
        ).start()

    def stop(self) -> None:
        self._stop.set()

    def states(self) -> list[dict[str, Any]]:
        result = _http_json(self.base_url, self._token, "/api/states")
        return result if isinstance(result, list) else []

    def project(self) -> dict[str, Any]:
        return fetch_project(self.base_url, self._token)

    def call_service(self, command: dict[str, Any]) -> None:
        payload = dict(command.get("data", {}))
        payload.update(command.get("target", {}))
        _http_json(
            self.base_url,
            self._token,
            f"/api/services/{command['domain']}/{command['service']}",
            method="POST",
            payload=payload,
        )

    def _heartbeat_worker(self) -> None:
        while not self._stop.is_set():
            try:
                _http_json(
                    self.base_url,
                    self._token,
                    "/api/events/cyd_ui_lab_gateway_online",
                    method="POST",
                    payload={"device_id": "cyd-ui"},
                    timeout=8,
                )
            except Exception:
                pass
            self._stop.wait(20)

    def _event_worker(self) -> None:
        while not self._stop.is_set():
            ws = None
            try:
                ws = _authenticate_websocket(self.base_url, self._token)
                ws.settimeout(30)
                ws.send(json.dumps({
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": "state_changed",
                }))
                ws.send(json.dumps({
                    "id": 2,
                    "type": "subscribe_events",
                    "event_type": "cyd_ui_lab_command",
                }))
                confirmations = [json.loads(ws.recv()), json.loads(ws.recv())]
                if not all(item.get("success") for item in confirmations):
                    raise RuntimeError("No se pudo suscribir a state_changed")
                self._emit(("ha_connected", self.base_url))
                while not self._stop.is_set():
                    try:
                        message = json.loads(ws.recv())
                    except websocket.WebSocketTimeoutException:
                        continue
                    if message.get("type") != "event":
                        continue
                    event = message.get("event", {})
                    data = event.get("data", {})
                    if event.get("event_type") == "state_changed":
                        self._emit(("ha_state", data))
                    elif event.get("event_type") == "cyd_ui_lab_command":
                        self._emit(("ha_command", data))
            except Exception as error:
                self._emit(("ha_disconnected", str(error)))
                self._base_url = None
                self._stop.wait(RECONNECT_SECONDS)
            finally:
                if ws is not None:
                    ws.close()


@dataclass
class RuntimeProject:
    revision: int
    ui: dict[str, Any]
    mappings: dict[str, dict[str, Any]]

    @classmethod
    def from_storage(cls, stored: dict[str, Any]) -> "RuntimeProject":
        ui = copy.deepcopy(stored.get("ui"))
        backend_map = copy.deepcopy(stored.get("backend_map"))
        mappings = backend_map.get("controls") if isinstance(backend_map, dict) else None
        if not isinstance(ui, dict) or not isinstance(mappings, dict):
            raise RuntimeError("El proyecto guardado en CYD UI está incompleto")
        for page in ui.get("pages", []):
            if not isinstance(page, dict) or page.get("template") != "media":
                continue
            controls = page.get("controls")
            if not isinstance(controls, list) or any(
                isinstance(item, dict) and item.get("role") == "artwork"
                for item in controls
            ):
                continue
            player = next(
                (item for item in controls
                 if isinstance(item, dict) and item.get("role") == "player"),
                None,
            )
            if not isinstance(player, dict):
                continue
            player_id = str(player.get("id", "media_player"))
            artwork_id = f"{player_id}_artwork"
            existing_ids = {
                item.get("id") for item in controls if isinstance(item, dict)
            }
            suffix = 2
            while artwork_id in existing_ids:
                artwork_id = f"{player_id}_artwork_{suffix}"
                suffix += 1
            artwork = {
                "type": "value", "id": artwork_id, "caption": "Carátula",
                "role": "artwork", "color": "#FFFFFF", "meta": {}, "unit": "",
            }
            volume_index = next(
                (index for index, item in enumerate(controls)
                 if isinstance(item, dict) and item.get("role") == "volume"),
                len(controls),
            )
            controls.insert(volume_index, artwork)
            player_mapping = mappings.get(player_id, {})
            entity_id = player_mapping.get("entity_id", "")
            artwork_mapping = {
                "entity_id": entity_id,
                "domain": "media_player",
                "attribute": "media_image_url",
                "media_selector_id": player_id,
            }
            if entity_id == "media_player.jarvis_assist_parlante":
                artwork_mapping.update({
                    "fallback_entity_id": "text.jarvis_assist_pantalla_url_de_caratula",
                    "fallback_for_entity_id": entity_id,
                })
            mappings[artwork_id] = artwork_mapping
        return cls(int(stored.get("revision", 0)), ui, mappings)


class LabGateway:
    def __init__(
        self, device_host: str, device_port: int, allow_climate_power: bool
    ) -> None:
        candidates, token, api_key = read_access()
        self.device_host = device_host
        self.device_port = device_port
        self.api_key = api_key
        self.allow_climate_power = allow_climate_power
        self.artwork_proxy = ArtworkProxy(device_host)
        self.loop = asyncio.get_running_loop()
        self.events: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        self.ha = HomeAssistantLink(candidates, token, self._emit_from_thread)
        self.project: RuntimeProject | None = None
        self.states: dict[str, dict[str, Any]] = {}
        self.client: APIClient | None = None
        self.services: dict[str, UserService] = {}
        self.stop_event = asyncio.Event()
        self.device_lost = asyncio.Event()
        self.ha_available = True
        self._last_config_poll = 0.0

    def _emit_from_thread(self, event: tuple[str, Any]) -> None:
        self.loop.call_soon_threadsafe(self.events.put_nowait, event)

    async def _device_stopped(self, expected_disconnect: bool) -> None:
        if not expected_disconnect:
            self.device_lost.set()

    async def _load_ha_snapshot(self) -> None:
        stored, states = await asyncio.gather(
            asyncio.to_thread(self.ha.project),
            asyncio.to_thread(self.ha.states),
        )
        self.project = RuntimeProject.from_storage(stored)
        self.states = {
            state["entity_id"]: state
            for state in states
            if isinstance(state, dict) and isinstance(state.get("entity_id"), str)
        }

    async def _execute(self, name: str, data: dict[str, Any]) -> None:
        service = self.services.get(name)
        if self.client is None or service is None:
            raise RuntimeError(f"La pantalla no expone la acción {name}")
        await self.client.execute_service(service, data)

    async def _apply_project(self) -> None:
        if self.project is None:
            return
        payload = json.dumps(self.project.ui, ensure_ascii=False, separators=(",", ":"))
        await self._execute("apply_config", {"config": payload})
        await asyncio.sleep(0.35)
        await self._sync_all()
        print(
            f"Proyecto aplicado: revisión {self.project.revision}, "
            f"{len(self.project.ui.get('pages', []))} páginas, "
            f"{len(self.project.mappings)} controles",
            flush=True,
        )

    async def _publish_control(self, control_id: str, mapping: dict[str, Any]) -> None:
        if mapping.get("publish_state") is False:
            return
        entity_id = mapping.get("entity_id")
        if not isinstance(entity_id, str):
            return
        state = self.states.get(entity_id)
        update = BRIDGE_MODEL.update_for_state(
            control_id,
            mapping,
            state.get("state") if state else None,
            state.get("attributes") if state else None,
        )
        fallback_id = mapping.get("fallback_entity_id")
        fallback_for = mapping.get("fallback_for_entity_id")
        fallback_allowed = not fallback_for or fallback_for == entity_id
        if (
            update["reliability"] != "valid"
            and isinstance(fallback_id, str)
            and fallback_allowed
        ):
            fallback_state = self.states.get(fallback_id)
            fallback_is_fresh = BRIDGE_MODEL.fallback_metadata_is_fresh(
                state.get("last_changed") if state else None,
                fallback_state.get("last_updated") if fallback_state else None,
            )
            if not fallback_is_fresh:
                fallback_state = None
            fallback_mapping = dict(mapping)
            fallback_mapping.pop("attribute", None)
            if mapping.get("fallback_attribute"):
                fallback_mapping["attribute"] = mapping["fallback_attribute"]
                fallback_mapping.pop("value_only", None)
            else:
                fallback_mapping["value_only"] = True
            update = BRIDGE_MODEL.update_for_state(
                control_id,
                fallback_mapping,
                fallback_state.get("state") if fallback_state else None,
                fallback_state.get("attributes") if fallback_state else None,
            )
        if (
            mapping.get("attribute") == "media_image_url"
            and update["reliability"] == "valid"
            and isinstance(update["value"], str)
            and update["value"].startswith(("http://", "https://"))
        ):
            update["value"] = self.artwork_proxy.publish(
                update["value"], ARTWORK_PROCESSOR.artwork_background(self.project.ui)
            )
        await self._execute("update_control", {
            "control_id": update["control_id"],
            "active": update["active"],
            "value": update["value"],
            "reliability": update["reliability"],
        })

    async def _sync_all(self) -> None:
        if self.project is None:
            return
        for control_id, mapping in self.project.mappings.items():
            await self._publish_control(control_id, mapping)

    async def _handle_ha_state(self, data: dict[str, Any]) -> None:
        entity_id = data.get("entity_id")
        new_state = data.get("new_state")
        if not isinstance(entity_id, str) or not isinstance(new_state, dict):
            return
        self.states[entity_id] = new_state
        if self.project is None:
            return
        for control_id, mapping in self.project.mappings.items():
            if (
                mapping.get("entity_id") == entity_id
                or mapping.get("fallback_entity_id") == entity_id
            ):
                await self._publish_control(control_id, mapping)

    @staticmethod
    def _service_data(call: HomeassistantServiceCall) -> dict[str, str]:
        return {**call.data, **call.data_template, **call.variables}

    def _on_device_service(self, call: HomeassistantServiceCall) -> None:
        self.events.put_nowait(("device_service", call))

    @staticmethod
    def _on_device_state(_state: Any) -> None:
        """No-op: subscribing marks this client as a live HA-style client."""

    async def _handle_device_service(self, call: HomeassistantServiceCall) -> None:
        data = self._service_data(call)
        if call.service == "esphome.cyd_ui_ready":
            await self._apply_project()
            return
        if call.service != "esphome.cyd_ui_action" or self.project is None:
            return
        control_id = data.get("control_id")
        action = data.get("action")
        if not control_id or not action:
            return
        mapping = self.project.mappings.get(control_id)
        entity_id = mapping.get("entity_id") if isinstance(mapping, dict) else None
        state = self.states.get(entity_id) if entity_id else None
        command = BRIDGE_MODEL.command_for_action(
            control_id,
            action,
            mapping,
            state.get("state") if state else None,
            state.get("attributes") if state else None,
        )
        if command is None:
            print(f"Acción rechazada por seguridad: {control_id}/{action}", flush=True)
            return
        command_key = (command["domain"], command["service"])
        if command_key in REMOTE_BLOCKED_COMMANDS and not self.allow_climate_power:
            print("Encendido/apagado del calefactor bloqueado en modo laboratorio", flush=True)
            return
        await asyncio.to_thread(self.ha.call_service, command)
        print(
            f"Acción enviada: {control_id} -> {command['domain']}.{command['service']}",
            flush=True,
        )

    async def _poll_project(self) -> None:
        now = time.monotonic()
        if now - self._last_config_poll < CONFIG_POLL_SECONDS:
            return
        self._last_config_poll = now
        try:
            next_project = RuntimeProject.from_storage(
                await asyncio.to_thread(self.ha.project)
            )
        except Exception as error:
            print(f"No se pudo revisar la configuración: {error}", flush=True)
            return
        if self.project is None or next_project.revision != self.project.revision:
            self.project = next_project
            await self._apply_project()

    async def _check_device_health(self) -> None:
        """Detect a socket already marked closed without extra device traffic."""
        if self.client is None or self.client.connected_address is None:
            raise ConnectionError("la conexión API con la pantalla se cerró")

    async def _connect_device(self) -> None:
        self.device_lost.clear()
        self.client = APIClient(
            self.device_host,
            self.device_port,
            noise_psk=self.api_key,
            client_info="CYD Lab Gateway",
            expected_name="cyd-ui",
        )
        await asyncio.wait_for(
            self.client.connect(on_stop=self._device_stopped, login=True),
            timeout=DEVICE_CONNECT_TIMEOUT_SECONDS,
        )
        info = await self.client.device_info()
        _, available_services = await self.client.list_entities_services()
        self.services = {service.name: service for service in available_services}
        required = {"apply_config", "update_control"}
        if missing := required - self.services.keys():
            raise RuntimeError(f"Faltan acciones nativas: {', '.join(sorted(missing))}")
        self.client.subscribe_service_calls(self._on_device_service)
        # SubscribeStatesRequest sets ESPHome's state_subscription flag. The
        # firmware uses it to distinguish HA-compatible clients from diagnostics.
        self.client.subscribe_states(self._on_device_state)
        print(f"Pantalla conectada por API nativa: {info.name}", flush=True)

    async def _wait_for_ha_ready(self) -> None:
        """Wait for HA and the CYD UI integration to finish booting."""
        while not self.stop_event.is_set():
            try:
                await self._load_ha_snapshot()
                self.ha_available = True
                # The full snapshot supersedes state/disconnect events queued
                # while Home Assistant was restarting.
                while not self.events.empty():
                    try:
                        self.events.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                print("Home Assistant y CYD UI volvieron a estar disponibles", flush=True)
                return
            except Exception:
                await asyncio.sleep(RECONNECT_SECONDS)

    async def run(self) -> None:
        await self._load_ha_snapshot()
        print(f"Home Assistant accesible por {self.ha.base_url}", flush=True)
        self.ha.start()
        while not self.stop_event.is_set():
            try:
                if not self.ha_available:
                    await self._wait_for_ha_ready()
                    if self.stop_event.is_set():
                        break
                await self._connect_device()
                await self._apply_project()
                while not self.stop_event.is_set() and not self.device_lost.is_set():
                    try:
                        event_type, payload = await asyncio.wait_for(
                            self.events.get(), timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        await self._check_device_health()
                        await self._poll_project()
                        continue
                    if event_type == "ha_state":
                        await self._handle_ha_state(payload)
                    elif event_type == "device_service":
                        await self._handle_device_service(payload)
                    elif event_type == "ha_connected":
                        if self.ha_available:
                            print("Eventos de Home Assistant conectados", flush=True)
                            states = await asyncio.to_thread(self.ha.states)
                            self.states = {
                                state["entity_id"]: state
                                for state in states
                                if isinstance(state, dict) and state.get("entity_id")
                            }
                            await self._sync_all()
                    elif event_type == "ha_disconnected":
                        print("Home Assistant desconectado; reconectando…", flush=True)
                        self.ha_available = False
                        self.device_lost.set()
                    elif event_type == "ha_command":
                        service = str(payload.get("service", ""))
                        data = payload.get("data", {})
                        if service and isinstance(data, dict):
                            print(f"Comando remoto recibido: {service}", flush=True)
                            await self._execute(service, data)
                            print(f"Comando remoto ejecutado: {service}", flush=True)
            except asyncio.CancelledError:
                break
            except Exception as error:
                print(f"Puente desconectado; reintento en 3 s: {error}", flush=True)
            finally:
                if self.client is not None:
                    try:
                        await asyncio.wait_for(
                            self.client.disconnect(),
                            timeout=DEVICE_DISCONNECT_TIMEOUT_SECONDS,
                        )
                    except Exception:
                        pass
                    self.client = None
                    self.services = {}
            if not self.stop_event.is_set():
                await asyncio.sleep(RECONNECT_SECONDS)
        self.ha.stop()

    def stop(self) -> None:
        self.stop_event.set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Puente local CYD ↔ Home Assistant")
    parser.add_argument("--device", default=DEFAULT_DEVICE_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_DEVICE_PORT)
    parser.add_argument(
        "--allow-climate-power",
        action="store_true",
        help="Permitir encender/apagar climatización desde el laboratorio",
    )
    return parser.parse_args()


async def async_main() -> None:
    instance_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        instance_lock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        instance_lock.listen(1)
    except OSError:
        print("El CYD Lab Gateway ya está funcionando.", flush=True)
        return
    args = parse_args()
    gateway = LabGateway(args.device, args.port, args.allow_climate_power)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, gateway.stop)
        except NotImplementedError:
            pass
    print("CYD Lab Gateway iniciado. Ctrl+C para detener.", flush=True)
    try:
        await gateway.run()
    finally:
        instance_lock.close()


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
