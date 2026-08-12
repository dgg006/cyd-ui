"""Home Assistant integration for CYD UI."""

from pathlib import Path
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol

from .api import async_dismiss_reminder, async_register_commands, async_send_reminder
from .const import (
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_PATH,
    PANEL_TITLE,
    STATIC_URL,
    SERVICE_DISMISS_REMINDER,
    SERVICE_SHOW_REMINDER,
    VERSION,
)
from .storage import CydUiStorage
from .reminders import ReminderScheduler
from .migration import async_rollback_to_automations, async_restore_enabled_bridge


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CYD UI from a config entry."""
    data = hass.data.setdefault(DOMAIN, {})
    frontend_root = Path(__file__).parent / "frontend"
    module_url = f"{STATIC_URL}/cyd-ui-panel.js?v={VERSION}"

    storage = CydUiStorage(hass)
    await storage.async_load()
    data["storage"] = storage

    @callback
    def mark_lab_gateway_online(_event) -> None:
        data["lab_gateway_seen"] = hass.loop.time()

    data["remove_lab_gateway_listener"] = hass.bus.async_listen(
        "cyd_ui_lab_gateway_online", mark_lab_gateway_online
    )
    scheduler = ReminderScheduler(hass, storage)
    await scheduler.async_start()
    data["reminder_scheduler"] = scheduler

    if not data.get("static_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(frontend_root), False)]
        )
        data["static_registered"] = True

    if not data.get("websocket_registered"):
        async_register_commands(hass)
        data["websocket_registered"] = True

    if not data.get("services_registered"):
        async def handle_show_reminder(call: ServiceCall) -> None:
            try:
                await async_send_reminder(hass, dict(call.data))
            except RuntimeError as error:
                raise HomeAssistantError(str(error)) from error

        async def handle_dismiss_reminder(call: ServiceCall) -> None:
            try:
                await async_dismiss_reminder(hass, str(call.data.get("reminder_id", "")))
            except RuntimeError as error:
                raise HomeAssistantError(str(error)) from error

        hass.services.async_register(
            DOMAIN,
            SERVICE_SHOW_REMINDER,
            handle_show_reminder,
            schema=vol.Schema(
                {
                    vol.Optional("reminder_id", default="recordatorio"): vol.All(str, vol.Length(min=1, max=64)),
                    vol.Optional("title", default="Recordatorio"): vol.All(str, vol.Length(max=80)),
                    vol.Required("message"): vol.All(str, vol.Length(min=1, max=280)),
                    vol.Optional("level", default="reminder"): vol.In(("info", "reminder", "warning", "urgent")),
                    vol.Optional("sound_mode", default="once"): vol.In(("silent", "once", "alarm")),
                    vol.Optional("alarm_duration", default=120): vol.All(vol.Coerce(int), vol.Range(min=10, max=120)),
                    vol.Optional("snooze_minutes", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
                }
            ),
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_DISMISS_REMINDER,
            handle_dismiss_reminder,
            schema=vol.Schema({vol.Optional("reminder_id", default=""): str}),
        )
        data["services_registered"] = True

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=module_url,
        require_admin=True,
    )
    data["module_url"] = module_url
    data["entry_id"] = entry.entry_id
    await async_restore_enabled_bridge(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the visible CYD UI panel."""
    data = hass.data.get(DOMAIN, {})
    frontend.async_remove_panel(hass, PANEL_PATH)
    data.pop("entry_id", None)
    data.pop("module_url", None)
    if bridge := data.pop("bridge", None):
        await bridge.async_stop()
    if scheduler := data.pop("reminder_scheduler", None):
        await scheduler.async_shutdown()
    if remove_listener := data.pop("remove_lab_gateway_listener", None):
        remove_listener()
    if data.pop("services_registered", False):
        hass.services.async_remove(DOMAIN, SERVICE_SHOW_REMINDER)
        hass.services.async_remove(DOMAIN, SERVICE_DISMISS_REMINDER)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Restore temporary ownership before permanently removing CYD UI."""
    data = hass.data.get(DOMAIN, {})
    storage: CydUiStorage | None = data.get("storage")
    if storage is None:
        return
    if storage.data.get("native_bridge_enabled"):
        await async_rollback_to_automations(hass)
    await storage.async_remove()
    data.pop("storage", None)
