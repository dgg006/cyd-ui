"""Native Home Assistant bridge, kept disabled until migration is explicit."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant

from .bridge_model import command_for_action, update_for_state
from .storage import CydUiStorage


_LOGGER = logging.getLogger(__name__)
ACTION_EVENT = "esphome.cyd_ui_action"
ESPHOME_DOMAIN = "esphome"
UPDATE_SERVICE = "cyd_ui_update_control"


class CydUiBridge:
    """Translate actions and states without generated automations."""

    def __init__(self, hass: HomeAssistant, storage: CydUiStorage) -> None:
        self._hass = hass
        self._storage = storage
        self._unsubscribers: list[Any] = []

    async def async_start(self) -> None:
        """Start listeners only after the migration disables old automations."""
        self._unsubscribers = [
            self._hass.bus.async_listen(ACTION_EVENT, self._async_handle_action),
            self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_handle_state),
        ]
        await self.async_sync_all()

    async def async_stop(self) -> None:
        """Remove all event listeners."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    def _mappings(self) -> dict[str, dict[str, Any]]:
        backend_map = self._storage.data.get("backend_map", {})
        return backend_map.get("controls", {}) if isinstance(backend_map, dict) else {}

    async def _async_handle_action(self, event: Event) -> None:
        control_id = event.data.get("control_id")
        action = event.data.get("action")
        if not isinstance(control_id, str) or not isinstance(action, str):
            return
        mapping = self._mappings().get(control_id)
        entity_id = mapping.get("entity_id") if isinstance(mapping, dict) else None
        state = self._hass.states.get(entity_id) if entity_id else None
        command = command_for_action(
            control_id,
            action,
            mapping,
            state.state if state else None,
            dict(state.attributes) if state else None,
        )
        if command is None:
            _LOGGER.warning("Rejected CYD UI action %s/%s", control_id, action)
            return
        await self._hass.services.async_call(
            command["domain"],
            command["service"],
            command["data"],
            target=command["target"],
            blocking=True,
            context=event.context,
        )

    async def _async_handle_state(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if not isinstance(entity_id, str):
            return
        for control_id, mapping in self._mappings().items():
            if mapping.get("entity_id") == entity_id and mapping.get("publish_state") is not False:
                await self._async_publish_control(control_id, mapping)

    async def async_sync_all(self) -> None:
        """Send a complete state snapshot after startup or project changes."""
        for control_id, mapping in self._mappings().items():
            if mapping.get("entity_id") and mapping.get("publish_state") is not False:
                await self._async_publish_control(control_id, mapping)

    async def _async_publish_control(
        self, control_id: str, mapping: dict[str, Any]
    ) -> None:
        if not self._hass.services.has_service(ESPHOME_DOMAIN, UPDATE_SERVICE):
            return
        state = self._hass.states.get(mapping["entity_id"])
        update = update_for_state(
            control_id,
            mapping,
            state.state if state else None,
            dict(state.attributes) if state else None,
        )
        await self._hass.services.async_call(
            ESPHOME_DOMAIN, UPDATE_SERVICE, update, blocking=False
        )
