"""Pure command and state translation for the future native bridge."""

from __future__ import annotations

from typing import Any


UNRELIABLE_STATES = {"unknown", "unavailable"}
ALLOWED_SERVICES: dict[str, set[str]] = {
    "light": {"toggle", "turn_on", "turn_off"},
    "switch": {"toggle", "turn_on", "turn_off"},
    "input_boolean": {"toggle", "turn_on", "turn_off"},
    "fan": {"toggle", "turn_on", "turn_off"},
    "scene": {"turn_on"},
    "script": {"turn_on"},
    "button": {"press"},
    "cover": {"open_cover", "close_cover"},
    "media_player": {
        "media_play_pause", "media_previous_track", "media_next_track",
        "volume_down", "volume_up", "volume_mute",
    },
}


def command_for_action(
    control_id: str,
    action: str,
    mapping: dict[str, Any] | None,
    entity_state: str | None,
    attributes: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Translate one allowed panel action into a constrained HA service call."""
    if not mapping or not mapping.get("allow_control"):
        return None
    entity_id = mapping.get("entity_id")
    if not isinstance(entity_id, str) or "." not in entity_id:
        return None
    if action != mapping.get("action"):
        return None
    if entity_state is None or entity_state in UNRELIABLE_STATES:
        return None

    domain = mapping.get("domain") or entity_id.partition(".")[0]
    service = mapping.get("service") or action
    attributes = attributes or {}
    data: dict[str, Any] = {}

    if service == "toggle_hvac":
        domain, service = "climate", "set_hvac_mode"
        data["hvac_mode"] = "heat" if entity_state == "off" else "off"
    elif service == "set_temperature":
        current = attributes.get("temperature")
        delta = mapping.get("temperature_delta")
        if not isinstance(current, (int, float)) or not isinstance(delta, (int, float)):
            return None
        domain, service = "climate", "set_temperature"
        data["temperature"] = round(float(current) + float(delta), 1)
    elif service == "set_cover_position":
        current = attributes.get("current_position")
        delta = mapping.get("position_delta")
        if not isinstance(current, (int, float)) or not isinstance(delta, (int, float)):
            return None
        domain, service = "cover", "set_cover_position"
        data["position"] = round(max(0.0, min(100.0, float(current) + float(delta))))
    elif service not in ALLOWED_SERVICES.get(str(domain), set()):
        return None

    return {
        "control_id": control_id,
        "domain": domain,
        "service": service,
        "target": {"entity_id": entity_id},
        "data": data,
    }


def update_for_state(
    control_id: str,
    mapping: dict[str, Any],
    entity_state: str | None,
    attributes: dict[str, Any] | None,
) -> dict[str, Any]:
    """Translate a HA state into the generic update expected by the CYD."""
    attributes = attributes or {}
    source: Any = None
    if attribute := mapping.get("attribute"):
        source = attributes.get(attribute)
    elif mapping.get("value_only"):
        source = entity_state

    unreliable = entity_state is None or entity_state in UNRELIABLE_STATES
    if mapping.get("attribute") and source is None:
        unreliable = True

    if value_map := mapping.get("value_map"):
        source = value_map.get(str(source), source)
    if source is not None and isinstance(mapping.get("scale"), (int, float)):
        try:
            source = float(source) * float(mapping["scale"])
        except (TypeError, ValueError):
            pass
    if source is None:
        value = ""
    elif "decimals" in mapping:
        try:
            value = f"{float(source):.{int(mapping['decimals'])}f}"
        except (TypeError, ValueError):
            value = str(source)
    else:
        value = str(source)

    # Binary sensors are value-only controls, but their icon still needs the
    # boolean state. Older saved projects did not carry state_active, so keep
    # this inference here instead of requiring every user to re-save a page.
    if isinstance(mapping.get("active_states"), list):
        active = not unreliable and entity_state in mapping["active_states"]
    elif mapping.get("state_active") or (
        mapping.get("domain") == "binary_sensor" and mapping.get("value_only")
    ):
        active = not unreliable and entity_state != "off"
    elif mapping.get("attribute") or mapping.get("value_only"):
        active = False
    else:
        active = entity_state == "on"

    return {
        "control_id": control_id,
        "active": active,
        "value": value,
        "reliability": "unavailable" if unreliable else "valid",
    }
