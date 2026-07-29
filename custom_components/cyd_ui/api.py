"""WebSocket API exposed to the CYD UI administration panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, VERSION
from .model import validate_document
from .storage import CydUiStorage


def _domain_data(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data[DOMAIN]


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/status"})
@callback
def websocket_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return bootstrap and persistent-storage status."""
    connection.require_admin()
    storage: CydUiStorage = _domain_data(hass)["storage"]
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "ready": True,
            "phase": "storage",
            "revision": storage.data["revision"],
            "configured": storage.data["ui"] is not None,
            "message": "Integración y almacenamiento cargados correctamente.",
        },
    )


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/config/get"})
@callback
def websocket_config_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the current project to the administration panel."""
    connection.require_admin()
    storage: CydUiStorage = _domain_data(hass)["storage"]
    connection.send_result(msg["id"], storage.data)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cyd_ui/config/save",
        vol.Required("ui"): dict,
        vol.Required("backend_map"): dict,
    }
)
@websocket_api.async_response
async def websocket_config_save(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate and atomically persist a complete project."""
    connection.require_admin()
    storage: CydUiStorage = _domain_data(hass)["storage"]
    errors = await storage.async_save(msg["ui"], msg["backend_map"])
    if errors:
        connection.send_error(msg["id"], "invalid_config", "\n".join(errors))
        return
    connection.send_result(
        msg["id"],
        {
            "saved": True,
            "revision": storage.data["revision"],
            "updated_at": storage.data["updated_at"],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cyd_ui/config/validate",
        vol.Required("ui"): dict,
        vol.Required("backend_map"): dict,
    }
)
@callback
def websocket_config_validate(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate a draft without persisting it."""
    connection.require_admin()
    errors = validate_document(msg["ui"], msg["backend_map"])
    connection.send_result(msg["id"], {"valid": not errors, "errors": errors})


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/entities/list"})
@callback
def websocket_entities_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return searchable entity metadata without an external access token."""
    connection.require_admin()
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
    websocket_api.async_register_command(hass, websocket_config_get)
    websocket_api.async_register_command(hass, websocket_config_validate)
    websocket_api.async_register_command(hass, websocket_config_save)
    websocket_api.async_register_command(hass, websocket_entities_list)
