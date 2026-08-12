"""Home Assistant managed storage for CYD UI."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORAGE_KEY, STORAGE_VERSION
from .model import create_revision, migrate_media_artwork, restore_revision, validate_document


class CydUiStorage:
    """Keep the current project and a bounded revision history."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store[dict[str, Any]](
            hass, STORAGE_VERSION, STORAGE_KEY, atomic_writes=True
        )
        self.data: dict[str, Any] = {
            "revision": 0,
            "updated_at": None,
            "ui": None,
            "backend_map": {"controls": {}},
            "history": [],
            "native_bridge_enabled": False,
            "temporary_automation_states": {},
            "scheduled_reminders": [],
            "reminder_history": [],
        }
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Load the last valid project, if one exists."""
        if stored := await self._store.async_load():
            self.data = stored
        self.data.setdefault("scheduled_reminders", [])
        self.data.setdefault("reminder_history", [])
        if isinstance(self.data.get("ui"), dict):
            ui, backend_map, changed = migrate_media_artwork(
                self.data["ui"], self.data.get("backend_map", {"controls": {}})
            )
            if changed and not validate_document(ui, backend_map):
                self.data["ui"] = ui
                self.data["backend_map"] = backend_map
                self.data["revision"] = int(self.data.get("revision", 0)) + 1
                self.data["updated_at"] = dt_util.utcnow().isoformat()
                await self._store.async_save(self.data)

    async def async_save(
        self, ui: dict[str, Any], backend_map: dict[str, Any]
    ) -> list[str]:
        """Validate and persist an all-or-nothing project revision."""
        if errors := validate_document(ui, backend_map):
            return errors
        async with self._lock:
            next_data = create_revision(
                self.data, ui, backend_map, dt_util.utcnow().isoformat()
            )
            await self._store.async_save(next_data)
            self.data = next_data
        return []

    def history_summary(self) -> list[dict[str, Any]]:
        """Return lightweight revision metadata for the editor."""
        summaries = []
        for item in reversed(self.data.get("history", [])):
            if not isinstance(item, dict) or not isinstance(item.get("ui"), dict):
                continue
            summaries.append(
                {
                    "revision": item.get("revision"),
                    "updated_at": item.get("updated_at"),
                    "page_count": len(item["ui"].get("pages", [])),
                }
            )
        return summaries

    async def async_restore(self, revision: int) -> bool:
        """Restore an old project as a new, non-destructive revision."""
        async with self._lock:
            next_data = restore_revision(
                self.data, revision, dt_util.utcnow().isoformat()
            )
            if next_data is None:
                return False
            await self._store.async_save(next_data)
            self.data = next_data
        return True

    async def async_set_bridge_enabled(
        self, enabled: bool, automation_states: dict[str, str] | None = None
    ) -> None:
        """Persist bridge ownership independently from editor revisions."""
        next_data = dict(self.data)
        next_data["native_bridge_enabled"] = enabled
        if automation_states is not None:
            next_data["temporary_automation_states"] = automation_states
        async with self._lock:
            await self._store.async_save(next_data)
            self.data = next_data

    async def async_update_reminders(
        self, scheduled: list[dict[str, Any]], history: list[dict[str, Any]]
    ) -> None:
        """Persist the reminder agenda without creating a UI revision."""
        async with self._lock:
            next_data = dict(self.data)
            next_data["scheduled_reminders"] = scheduled
            next_data["reminder_history"] = history[-20:]
            await self._store.async_save(next_data)
            self.data = next_data

    async def async_remove(self) -> None:
        """Remove managed data when the integration is permanently deleted."""
        await self._store.async_remove()
