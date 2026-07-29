"""Reversible migration from generated automations to the native bridge."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .bridge import CydUiBridge
from .const import DOMAIN
from .storage import CydUiStorage


TEMPORARY_AUTOMATIONS = (
    "automation.cyd_ui_ejecutar_controles",
    "automation.cyd_ui_sincronizar_estados",
)


async def _async_set_automations(
    hass: HomeAssistant, service: str, entity_ids: list[str]
) -> None:
    if not entity_ids:
        return
    await hass.services.async_call(
        "automation",
        service,
        {},
        target={"entity_id": entity_ids},
        blocking=True,
    )


def bridge_status(hass: HomeAssistant) -> dict[str, Any]:
    """Describe current ownership without changing external state."""
    data = hass.data[DOMAIN]
    storage: CydUiStorage = data["storage"]
    automations = {
        entity_id: (state.state if (state := hass.states.get(entity_id)) else "missing")
        for entity_id in TEMPORARY_AUTOMATIONS
    }
    return {
        "enabled": bool(storage.data.get("native_bridge_enabled", False)),
        "running": data.get("bridge") is not None,
        "temporary_automations": automations,
    }


async def async_restore_enabled_bridge(hass: HomeAssistant) -> None:
    """Restore a bridge that already owns command processing after restart."""
    data = hass.data[DOMAIN]
    storage: CydUiStorage = data["storage"]
    if not storage.data.get("native_bridge_enabled") or data.get("bridge") is not None:
        return
    bridge = CydUiBridge(hass, storage)
    await bridge.async_start()
    data["bridge"] = bridge


async def async_migrate_to_native_bridge(hass: HomeAssistant) -> dict[str, Any]:
    """Disable old command ownership before starting the native bridge."""
    data = hass.data[DOMAIN]
    storage: CydUiStorage = data["storage"]
    if storage.data.get("ui") is None:
        raise ValueError("Primero debe importarse un proyecto válido.")
    if data.get("bridge") is not None:
        return bridge_status(hass)

    previous_states = {
        entity_id: state.state
        for entity_id in TEMPORARY_AUTOMATIONS
        if (state := hass.states.get(entity_id)) is not None
    }
    previously_enabled = [
        entity_id for entity_id, state in previous_states.items() if state == "on"
    ]
    command_automation = [TEMPORARY_AUTOMATIONS[0]] if TEMPORARY_AUTOMATIONS[0] in previously_enabled else []
    state_automation = [TEMPORARY_AUTOMATIONS[1]] if TEMPORARY_AUTOMATIONS[1] in previously_enabled else []
    bridge: CydUiBridge | None = None
    try:
        # Command ownership is released first, so one touch can never be handled twice.
        await _async_set_automations(hass, "turn_off", command_automation)
        bridge = CydUiBridge(hass, storage)
        await bridge.async_start()
        await _async_set_automations(hass, "turn_off", state_automation)
        await storage.async_set_bridge_enabled(True, previous_states)
        data["bridge"] = bridge
    except Exception:
        if bridge is not None:
            await bridge.async_stop()
        await _async_set_automations(hass, "turn_on", previously_enabled)
        raise
    return bridge_status(hass)


async def async_rollback_to_automations(hass: HomeAssistant) -> dict[str, Any]:
    """Stop native ownership and restore every available temporary automation."""
    data = hass.data[DOMAIN]
    storage: CydUiStorage = data["storage"]
    previous_states = storage.data.get("temporary_automation_states", {})
    if bridge := data.pop("bridge", None):
        await bridge.async_stop()
    previously_enabled = [
        entity_id
        for entity_id, state in previous_states.items()
        if state == "on" and hass.states.get(entity_id) is not None
    ]
    try:
        await _async_set_automations(hass, "turn_on", previously_enabled)
        await storage.async_set_bridge_enabled(False, {})
    except Exception:
        # If rollback cannot restore the automations, recover native ownership.
        await async_restore_enabled_bridge(hass)
        raise
    return bridge_status(hass)
