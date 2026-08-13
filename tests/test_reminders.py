from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parent.parent / "custom_components" / "cyd_ui" / "reminder_model.py"
spec = importlib.util.spec_from_file_location("cyd_ui_reminder_model", MODULE_PATH)
reminder_model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reminder_model
spec.loader.exec_module(reminder_model)


class ReminderRecurrenceTests(unittest.TestCase):
    def setUp(self):
        self.timezone = "America/Montevideo"

    def item(self, repeat, weekdays):
        return {
            "id": "mate",
            "scheduled_at": "2026-08-13T13:00:00+00:00",
            "repeat": repeat,
            "weekdays": weekdays,
            "local_time": "10:00",
            "timezone": "America/Montevideo",
            "payload": {"message": "Tomar mate"},
        }

    def test_daily_keeps_local_wall_clock_time(self):
        next_item = reminder_model.next_occurrence(
            self.item("daily", list(range(7))),
            datetime(2026, 8, 13, 13, 1, tzinfo=timezone.utc),
            self.timezone,
        )

        self.assertEqual("2026-08-14T13:00:00+00:00", next_item["scheduled_at"])
        self.assertEqual("pending", next_item["status"])

    def test_custom_days_skip_unselected_days(self):
        next_item = reminder_model.next_occurrence(
            self.item("custom", [0, 2]),
            datetime(2026, 8, 13, 13, 1, tzinfo=timezone.utc),
            self.timezone,
        )

        self.assertEqual("2026-08-17T13:00:00+00:00", next_item["scheduled_at"])

    def test_one_shot_has_no_next_occurrence(self):
        self.assertIsNone(
            reminder_model.next_occurrence(
                self.item("once", []),
                datetime(2026, 8, 13, 13, 1, tzinfo=timezone.utc),
                self.timezone,
            )
        )


if __name__ == "__main__":
    unittest.main()
