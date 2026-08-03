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


def _domain_data(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data[DOMAIN]


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
