"""WebSocket API exposed to the CYD UI administration panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, VERSION
from .model import validate_document
from .migration import (
    async_migrate_to_native_bridge,
    async_rollback_to_automations,
    bridge_status,
)
from .storage import CydUiStorage


ESPHOME_DOMAIN = "esphome"
PREVIEW_NOTIFICATION_SERVICE = "cyd_ui_preview_notification_sound"
START_TOUCH_CALIBRATION_SERVICE = "cyd_ui_start_touch_calibration"
RELOAD_UI_SERVICE = "cyd_ui_reload_ui"


def _domain_data(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data[DOMAIN]


def _state_by_friendly_name(hass: HomeAssistant, friendly_name: str):
    """Find one of the panel's diagnostic entities without hard-coding its slug."""
    return next(
        (
            state
            for state in hass.states.async_all()
            if state.attributes.get("friendly_name") == friendly_name
        ),
        None,
    )


def _number_state(state: Any) -> float | None:
    if state is None or state.state in ("unknown", "unavailable"):
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/status"})
@websocket_api.require_admin
@callback
def websocket_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return bootstrap and persistent-storage status."""
    storage: CydUiStorage = _domain_data(hass)["storage"]
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "ready": True,
            "phase": "storage",
            "revision": storage.data["revision"],
            "configured": storage.data["ui"] is not None,
            "bridge": bridge_status(hass),
            "message": "Integración y almacenamiento cargados correctamente.",
        },
    )


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/bridge/status"})
@websocket_api.require_admin
@callback
def websocket_bridge_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return bridge ownership and legacy automation state."""
    connection.send_result(msg["id"], bridge_status(hass))


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/bridge/migrate"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_bridge_migrate(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Atomically transfer ownership to the native bridge."""
    connection.send_result(msg["id"], await async_migrate_to_native_bridge(hass))


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/bridge/rollback"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_bridge_rollback(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Restore generated automations and stop native ownership."""
    connection.send_result(msg["id"], await async_rollback_to_automations(hass))


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/config/get"})
@websocket_api.require_admin
@callback
def websocket_config_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the current project to the administration panel."""
    storage: CydUiStorage = _domain_data(hass)["storage"]
    connection.send_result(msg["id"], storage.data)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cyd_ui/config/save",
        vol.Required("ui"): dict,
        vol.Required("backend_map"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_config_save(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate and atomically persist a complete project."""
    storage: CydUiStorage = _domain_data(hass)["storage"]
    errors = await storage.async_save(msg["ui"], msg["backend_map"])
    if errors:
        connection.send_error(msg["id"], "invalid_config", "\n".join(errors))
        return
    bridge = _domain_data(hass).get("bridge")
    device_applied = False
    if bridge is not None:
        device_applied = await bridge.async_apply_config()
        await bridge.async_sync_all()
    connection.send_result(
        msg["id"],
        {
            "saved": True,
            "revision": storage.data["revision"],
            "updated_at": storage.data["updated_at"],
            "device_applied": device_applied,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cyd_ui/config/validate",
        vol.Required("ui"): dict,
        vol.Required("backend_map"): dict,
    }
)
@websocket_api.require_admin
@callback
def websocket_config_validate(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate a draft without persisting it."""
    errors = validate_document(msg["ui"], msg["backend_map"])
    connection.send_result(msg["id"], {"valid": not errors, "errors": errors})


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/entities/list"})
@websocket_api.require_admin
@callback
def websocket_entities_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return searchable entity metadata without an external access token."""
    entities = []
    for state in hass.states.async_all():
        attributes = state.attributes
        primitive_attributes = {
            key: value
            for key, value in attributes.items()
            if isinstance(value, (str, int, float, bool))
        }
        entities.append(
            {
                "entity_id": state.entity_id,
                "domain": state.domain,
                "name": attributes.get("friendly_name", state.entity_id),
                "state": state.state,
                "device_class": attributes.get("device_class", ""),
                "unit": attributes.get("unit_of_measurement", ""),
                "attributes": sorted(attributes),
                "attribute_values": primitive_attributes,
            }
        )
    entities.sort(key=lambda item: (item["domain"], item["name"].casefold()))
    connection.send_result(msg["id"], {"entities": entities})


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/device/status"})
@websocket_api.require_admin
@callback
def websocket_device_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return live diagnostics published by the CYD itself."""
    ldr = _number_state(_state_by_friendly_name(hass, "Voltaje LDR"))
    backlight = _state_by_friendly_name(hass, "Backlight")
    brightness = None
    if backlight is not None:
        raw_brightness = backlight.attributes.get("brightness")
        if isinstance(raw_brightness, (int, float)):
            brightness = float(raw_brightness) * 100.0 / 255.0
    connection.send_result(
        msg["id"],
        {
            "ldr_voltage": ldr,
            "brightness_percent": brightness,
            "mode": None,
            "night": False,
            "touch_calibration": None,
        },
    )


async def _async_call_panel_service(
    hass: HomeAssistant, service: str, data: dict[str, Any]
) -> None:
    if not hass.services.has_service(ESPHOME_DOMAIN, service):
        raise RuntimeError("La pantalla no está conectada a Home Assistant.")
    await hass.services.async_call(ESPHOME_DOMAIN, service, data, blocking=True)


@websocket_api.websocket_command(
    {vol.Required("type"): "cyd_ui/sound/preview", vol.Required("volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=10))}
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_sound_preview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Play a notification sample at the unsaved editor volume."""
    try:
        await _async_call_panel_service(
            hass, PREVIEW_NOTIFICATION_SERVICE, {"volume": msg["volume"]}
        )
    except RuntimeError as error:
        connection.send_error(msg["id"], "device_unavailable", str(error))
        return
    connection.send_result(msg["id"], {"sent": True})


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/touch_calibration/start"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_touch_calibration_start(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Ask the CYD to show its four-point touch calibration flow."""
    try:
        await _async_call_panel_service(hass, START_TOUCH_CALIBRATION_SERVICE, {})
    except RuntimeError as error:
        connection.send_error(msg["id"], "device_unavailable", str(error))
        return
    connection.send_result(msg["id"], {"started": True})


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/device/reload"})
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_device_reload(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Request a safe redraw of the panel."""
    try:
        await _async_call_panel_service(hass, RELOAD_UI_SERVICE, {})
    except RuntimeError as error:
        connection.send_error(msg["id"], "device_unavailable", str(error))
        return
    connection.send_result(msg["id"], {"sent": True})


def async_register_commands(hass: HomeAssistant) -> None:
    """Register all commands exactly once per Home Assistant process."""
    websocket_api.async_register_command(hass, websocket_status)
    websocket_api.async_register_command(hass, websocket_bridge_status)
    websocket_api.async_register_command(hass, websocket_bridge_migrate)
    websocket_api.async_register_command(hass, websocket_bridge_rollback)
    websocket_api.async_register_command(hass, websocket_config_get)
    websocket_api.async_register_command(hass, websocket_config_validate)
    websocket_api.async_register_command(hass, websocket_config_save)
    websocket_api.async_register_command(hass, websocket_entities_list)
    websocket_api.async_register_command(hass, websocket_device_status)
    websocket_api.async_register_command(hass, websocket_sound_preview)
    websocket_api.async_register_command(hass, websocket_touch_calibration_start)
    websocket_api.async_register_command(hass, websocket_device_reload)
