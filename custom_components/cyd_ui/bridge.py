"""Native Home Assistant bridge, kept disabled until migration is explicit."""

from __future__ import annotations

import json
import logging
import asyncio
import hashlib
import io
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from PIL import Image, ImageOps
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import EVENT_SERVICE_REGISTERED, EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .bridge_model import command_for_action, fallback_metadata_is_fresh, update_for_state
from .storage import CydUiStorage


_LOGGER = logging.getLogger(__name__)
ACTION_EVENT = "esphome.cyd_ui_action"
READY_EVENT = "esphome.cyd_ui_ready"
ESPHOME_DOMAIN = "esphome"
UPDATE_SERVICE = "cyd_ui_update_control"
APPLY_CONFIG_SERVICE = "cyd_ui_apply_config"


class CydUiBridge:
    """Translate actions and states without generated automations."""

    def __init__(self, hass: HomeAssistant, storage: CydUiStorage) -> None:
        self._hass = hass
        self._storage = storage
        self._unsubscribers: list[Any] = []
        self._ready_generation = 0
        self._media_selection: dict[str, int] = {}
        self._artwork_cache: dict[str, str] = {}

    async def async_start(self) -> None:
        """Start listeners only after the migration disables old automations."""
        self._unsubscribers = [
            self._hass.bus.async_listen(ACTION_EVENT, self._async_handle_action),
            self._hass.bus.async_listen(READY_EVENT, self._async_handle_ready),
            self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_handle_state),
            self._hass.bus.async_listen(
                EVENT_SERVICE_REGISTERED, self._async_handle_service_registered
            ),
        ]
        if await self.async_apply_config():
            await self.async_sync_all()

    async def _async_handle_ready(self, _event: Event) -> None:
        """Restore the stored project and live states after the CYD reconnects."""
        self._ready_generation += 1
        generation = self._ready_generation
        if await self.async_apply_config():
            await self.async_sync_all()
        # The ESPHome API accepts the configuration before LVGL has necessarily
        # finished rebuilding it. Replaying only live states a moment later
        # closes that startup race without resetting the visible page again.
        self._hass.async_create_task(self._async_resync_after_ready(generation))

    async def _async_resync_after_ready(self, generation: int) -> None:
        await asyncio.sleep(3)
        if generation != self._ready_generation:
            return
        await self.async_sync_all()

    async def async_stop(self) -> None:
        """Remove all event listeners."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    def _mappings(self) -> dict[str, dict[str, Any]]:
        backend_map = self._storage.data.get("backend_map", {})
        return backend_map.get("controls", {}) if isinstance(backend_map, dict) else {}

    def _effective_entity_id(self, control_id: str, mapping: dict[str, Any]) -> str | None:
        selector_id = mapping.get("media_selector_id") or (
            control_id if isinstance(mapping.get("entity_ids"), list) else None
        )
        selector = self._mappings().get(selector_id, {}) if selector_id else {}
        players = selector.get("entity_ids")
        if isinstance(players, list):
            players = [item for item in players if isinstance(item, str) and "." in item]
            if players:
                index = self._media_selection.get(str(selector_id), 0) % len(players)
                return players[index]
        entity_id = mapping.get("entity_id")
        return entity_id if isinstance(entity_id, str) and "." in entity_id else None

    async def _async_select_player(self, selector_id: str, delta: int) -> bool:
        selector = self._mappings().get(selector_id)
        players = selector.get("entity_ids") if isinstance(selector, dict) else None
        if not isinstance(players, list):
            return False
        players = [item for item in players if isinstance(item, str) and "." in item]
        if not players:
            return False
        self._media_selection[selector_id] = (
            self._media_selection.get(selector_id, 0) + delta
        ) % len(players)
        for control_id, mapping in self._mappings().items():
            if control_id == selector_id or mapping.get("media_selector_id") == selector_id:
                await self._async_publish_control(control_id, mapping)
        return True

    async def _async_handle_service_registered(self, event: Event) -> None:
        """Apply the stored project when the CYD reconnects to ESPHome API."""
        if (
            event.data.get("domain") == ESPHOME_DOMAIN
            and event.data.get("service") == APPLY_CONFIG_SERVICE
        ):
            if await self.async_apply_config():
                await self.async_sync_all()

    async def async_apply_config(self) -> bool:
        """Send the complete UI document through the native ESPHome API."""
        if not self._hass.services.has_service(ESPHOME_DOMAIN, APPLY_CONFIG_SERVICE):
            return False
        ui = self._storage.data.get("ui")
        if not isinstance(ui, dict):
            return False
        payload = json.dumps(ui, ensure_ascii=False, separators=(",", ":"))
        try:
            await self._hass.services.async_call(
                ESPHOME_DOMAIN,
                APPLY_CONFIG_SERVICE,
                {"config": payload},
                blocking=True,
            )
        except HomeAssistantError as error:
            _LOGGER.info(
                "CYD unavailable for direct config delivery; saved project remains pending: %s",
                error,
            )
            return False
        return True

    async def _async_handle_action(self, event: Event) -> None:
        control_id = event.data.get("control_id")
        action = event.data.get("action")
        if not isinstance(control_id, str) or not isinstance(action, str):
            return
        mapping = self._mappings().get(control_id)
        if action in {"previous_player", "next_player"} and isinstance(mapping, dict):
            if await self._async_select_player(control_id, -1 if action == "previous_player" else 1):
                return
        entity_id = self._effective_entity_id(control_id, mapping) if isinstance(mapping, dict) else None
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
            watches_entity = self._effective_entity_id(control_id, mapping) == entity_id
            watches_fallback = mapping.get("fallback_entity_id") == entity_id
            if (watches_entity or watches_fallback) and mapping.get("publish_state") is not False:
                await self._async_publish_control(control_id, mapping)

    async def async_sync_all(self) -> None:
        """Send a complete state snapshot after startup or project changes."""
        for control_id, mapping in self._mappings().items():
            if self._effective_entity_id(control_id, mapping) and mapping.get("publish_state") is not False:
                await self._async_publish_control(control_id, mapping)

    async def _async_publish_control(
        self, control_id: str, mapping: dict[str, Any]
    ) -> None:
        if not self._hass.services.has_service(ESPHOME_DOMAIN, UPDATE_SERVICE):
            return
        entity_id = self._effective_entity_id(control_id, mapping)
        state = self._hass.states.get(entity_id) if entity_id else None
        update = update_for_state(
            control_id,
            mapping,
            state.state if state else None,
            dict(state.attributes) if state else None,
        )
        fallback_id = mapping.get("fallback_entity_id")
        fallback_for = mapping.get("fallback_for_entity_id")
        fallback_allowed = not fallback_for or fallback_for == entity_id
        if update["reliability"] != "valid" and isinstance(fallback_id, str) and fallback_allowed:
            fallback_state = self._hass.states.get(fallback_id)
            # Alternative Jarvis text entities are useful for online radio,
            # but they can keep the previous station metadata when a local MP3
            # starts. Only trust them when they were refreshed at least as
            # recently as the selected media player.
            fallback_is_fresh = fallback_metadata_is_fresh(
                state.last_changed if state else None,
                fallback_state.last_updated if fallback_state else None,
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
            update = update_for_state(
                control_id,
                fallback_mapping,
                fallback_state.state if fallback_state else None,
                dict(fallback_state.attributes) if fallback_state else None,
            )
        if mapping.get("attribute") == "media_image_url":
            source_url = update.get("value")
            if (
                update.get("reliability") == "valid"
                and isinstance(source_url, str)
                and source_url.startswith(("http://", "https://"))
            ):
                prepared = await self._async_prepare_artwork(source_url)
                if prepared:
                    update["value"] = prepared
                else:
                    update["value"] = ""
                    update["reliability"] = "unavailable"
        try:
            await self._hass.services.async_call(
                ESPHOME_DOMAIN, UPDATE_SERVICE, update, blocking=False
            )
        except HomeAssistantError as error:
            _LOGGER.debug("CYD unavailable for state update: %s", error)

    async def _async_prepare_artwork(self, source_url: str) -> str | None:
        """Download and shrink artwork so a non-PSRAM ESP32 can decode it."""
        if cached := self._artwork_cache.get(source_url):
            return cached
        parsed = urlsplit(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        digest = hashlib.sha256(source_url.encode()).hexdigest()[:16]
        filename = f"artwork-{digest}.jpg"
        target_dir = Path(self._hass.config.path("www", "cyd_ui"))
        target = target_dir / filename
        try:
            session = async_get_clientsession(self._hass)
            async with session.get(source_url, timeout=8) as response:
                response.raise_for_status()
                raw = await response.content.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024:
                raise ValueError("artwork exceeds 512 KiB")

            def resize_and_store() -> None:
                target_dir.mkdir(parents=True, exist_ok=True)
                with Image.open(io.BytesIO(raw)) as image:
                    image = ImageOps.fit(
                        image.convert("RGB"), (72, 72), Image.Resampling.LANCZOS
                    )
                    image.save(target, "JPEG", quality=82, optimize=True)
                old_files = sorted(
                    target_dir.glob("artwork-*.jpg"),
                    key=lambda item: item.stat().st_mtime,
                    reverse=True,
                )
                for old_file in old_files[12:]:
                    old_file.unlink(missing_ok=True)

            await self._hass.async_add_executor_job(resize_and_store)
        except Exception as error:  # artwork is optional; keep the UI responsive
            _LOGGER.warning("Unable to prepare CYD artwork %s: %s", source_url, error)
            return None
        result = urlunsplit(
            (parsed.scheme, parsed.netloc, f"/local/cyd_ui/{filename}", f"v={digest}", "")
        )
        self._artwork_cache[source_url] = result
        return result
