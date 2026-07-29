"""Home Assistant managed storage for CYD UI."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORAGE_KEY, STORAGE_VERSION
from .model import create_revision, validate_document


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
        }

    async def async_load(self) -> None:
        """Load the last valid project, if one exists."""
        if stored := await self._store.async_load():
            self.data = stored

    async def async_save(
        self, ui: dict[str, Any], backend_map: dict[str, Any]
    ) -> list[str]:
        """Validate and persist an all-or-nothing project revision."""
        if errors := validate_document(ui, backend_map):
            return errors
        next_data = create_revision(
            self.data, ui, backend_map, dt_util.utcnow().isoformat()
        )
        await self._store.async_save(next_data)
        self.data = next_data
        return []
