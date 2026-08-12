"""Persistent one-shot reminder scheduler for CYD UI."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant

from .storage import CydUiStorage


RETRY_SECONDS = 60
MAX_LATE_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("La fecha debe incluir la zona horaria.")
    return parsed.astimezone(timezone.utc)


class ReminderScheduler:
    """Schedule reminders and retry delivery while a panel is unavailable."""

    def __init__(self, hass: HomeAssistant, storage: CydUiStorage) -> None:
        self.hass = hass
        self.storage = storage
        self._timers: dict[str, asyncio.TimerHandle] = {}

    async def async_start(self) -> None:
        """Restore pending timers after a Home Assistant restart."""
        now = _utc_now()
        scheduled = []
        history = list(self.storage.data.get("reminder_history", []))
        for item in self.storage.data.get("scheduled_reminders", []):
            try:
                due = _parse_utc(item["scheduled_at"])
            except (KeyError, TypeError, ValueError):
                continue
            if due < now - timedelta(hours=MAX_LATE_HOURS):
                history.append({**item, "status": "expired", "completed_at": now.isoformat()})
                continue
            scheduled.append(item)
        await self.storage.async_update_reminders(scheduled, history)
        for item in scheduled:
            self._arm(item)

    async def async_shutdown(self) -> None:
        """Cancel runtime timers; persisted reminders remain intact."""
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()

    def list_items(self) -> list[dict[str, Any]]:
        """Return pending reminders in chronological order."""
        return sorted(
            self.storage.data.get("scheduled_reminders", []),
            key=lambda item: item.get("scheduled_at", ""),
        )

    async def async_add(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist and arm a new one-shot reminder."""
        due = _parse_utc(str(data["scheduled_at"]))
        if due <= _utc_now() + timedelta(seconds=5):
            raise ValueError("Elegí una fecha y hora futura.")
        item = {
            "id": uuid4().hex,
            "scheduled_at": due.isoformat(),
            "created_at": _utc_now().isoformat(),
            "status": "pending",
            "attempts": 0,
            "last_error": None,
            "payload": {
                "reminder_id": str(data["reminder_id"]),
                "title": str(data.get("title", "Recordatorio")),
                "message": str(data["message"]),
                "level": str(data.get("level", "reminder")),
                "sound_mode": str(data.get("sound_mode", "once")),
                "alarm_duration": int(data.get("alarm_duration", 120)),
                "snooze_minutes": int(data.get("snooze_minutes", 0)),
            },
        }
        scheduled = [*self.storage.data.get("scheduled_reminders", []), item]
        await self.storage.async_update_reminders(
            scheduled, list(self.storage.data.get("reminder_history", []))
        )
        self._arm(item)
        return item

    async def async_cancel(self, schedule_id: str) -> bool:
        """Cancel one pending reminder."""
        scheduled = self.storage.data.get("scheduled_reminders", [])
        remaining = [item for item in scheduled if item.get("id") != schedule_id]
        if len(remaining) == len(scheduled):
            return False
        if timer := self._timers.pop(schedule_id, None):
            timer.cancel()
        await self.storage.async_update_reminders(
            remaining, list(self.storage.data.get("reminder_history", []))
        )
        return True

    def _arm(self, item: dict[str, Any], delay_override: float | None = None) -> None:
        schedule_id = item["id"]
        if timer := self._timers.pop(schedule_id, None):
            timer.cancel()
        delay = delay_override
        if delay is None:
            delay = max(0.0, (_parse_utc(item["scheduled_at"]) - _utc_now()).total_seconds())
        self._timers[schedule_id] = self.hass.loop.call_later(
            delay,
            lambda: self.hass.async_create_task(self._async_deliver(schedule_id)),
        )

    async def _async_deliver(self, schedule_id: str) -> None:
        self._timers.pop(schedule_id, None)
        item = next(
            (item for item in self.storage.data.get("scheduled_reminders", []) if item.get("id") == schedule_id),
            None,
        )
        if item is None:
            return
        try:
            from .api import async_send_reminder

            await async_send_reminder(self.hass, item["payload"])
        except Exception as error:  # Home Assistant service availability is transient.
            item = {**item, "status": "retrying", "attempts": int(item.get("attempts", 0)) + 1,
                    "last_error": str(error)}
            scheduled = [item if current.get("id") == schedule_id else current
                         for current in self.storage.data.get("scheduled_reminders", [])]
            await self.storage.async_update_reminders(
                scheduled, list(self.storage.data.get("reminder_history", []))
            )
            self._arm(item, RETRY_SECONDS)
            return

        completed = {**item, "status": "delivered", "completed_at": _utc_now().isoformat(), "last_error": None}
        remaining = [current for current in self.storage.data.get("scheduled_reminders", [])
                     if current.get("id") != schedule_id]
        history = [*self.storage.data.get("reminder_history", []), completed]
        await self.storage.async_update_reminders(remaining, history)
