"""Home Assistant integration for CYD UI."""

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_PATH,
    PANEL_TITLE,
    STATIC_URL,
    VERSION,
)


@websocket_api.websocket_command({vol.Required("type"): "cyd_ui/status"})
@callback
def websocket_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the integration bootstrap status to the editor panel."""
    connection.require_admin()
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "ready": True,
            "phase": "bootstrap",
            "message": "Base de la integración cargada correctamente.",
        },
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CYD UI from a config entry."""
    data = hass.data.setdefault(DOMAIN, {})
    frontend_root = Path(__file__).parent / "frontend"
    module_url = f"{STATIC_URL}/cyd-ui-panel.js?v={VERSION}"

    if not data.get("static_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(frontend_root), False)]
        )
        data["static_registered"] = True

    if not data.get("websocket_registered"):
        websocket_api.async_register_command(hass, websocket_status)
        data["websocket_registered"] = True

    frontend.add_extra_js_url(hass, module_url)
    frontend.async_register_built_in_panel(
        hass,
        PANEL_COMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_PATH,
        require_admin=True,
    )
    data["module_url"] = module_url
    data["entry_id"] = entry.entry_id
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the visible CYD UI panel."""
    data = hass.data.get(DOMAIN, {})
    frontend.async_remove_panel(hass, PANEL_PATH)
    if module_url := data.get("module_url"):
        frontend.remove_extra_js_url(hass, module_url)
    data.pop("entry_id", None)
    data.pop("module_url", None)
    return True
