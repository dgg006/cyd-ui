"""Pure recurrence calculations for the reminder scheduler."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


REPEAT_MODES = {"once", "daily", "weekdays", "weekly", "custom"}


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("La fecha debe incluir la zona horaria.")
    return parsed.astimezone(timezone.utc)


def timezone_for(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def next_occurrence(
    item: dict[str, Any], after: datetime, default_timezone: str = "UTC"
) -> dict[str, Any] | None:
    """Return the next wall-clock occurrence, preserving local time across DST."""
    if str(item.get("repeat", "once")) == "once":
        return None
    weekdays = item.get("weekdays", [])
    if not isinstance(weekdays, list) or not weekdays:
        return None
    zone = timezone_for(str(item.get("timezone") or default_timezone))
    hour, minute = (int(part) for part in str(item.get("local_time", "00:00")).split(":"))
    now_local = after.astimezone(zone)
    previous_local = parse_utc(str(item["scheduled_at"])).astimezone(zone)
    candidate_date = max(now_local.date(), previous_local.date())
    for offset in range(8):
        date = candidate_date + timedelta(days=offset)
        candidate = datetime(date.year, date.month, date.day, hour, minute, tzinfo=zone)
        if candidate.weekday() in weekdays and candidate > now_local + timedelta(seconds=5):
            return {
                **item,
                "scheduled_at": candidate.astimezone(timezone.utc).isoformat(),
                "status": "pending",
                "attempts": 0,
                "last_error": None,
            }
    return None
