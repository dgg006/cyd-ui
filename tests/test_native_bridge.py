import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import install_ha_native_bridge as native_bridge


class NativeBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controls = native_bridge.load_controls()

    def test_command_bridge_contains_only_allowed_controls(self):
        automation = native_bridge.build_command_automation(self.controls)
        choices = automation["actions"][0]["choose"]
        rendered = str(choices)

        self.assertIn("living", rendered)
        self.assertIn("climate_living_down", rendered)
        self.assertIn("climate_living_up", rendered)
        self.assertNotIn("climate_living_power", rendered)
        self.assertNotIn("turn_on", rendered)

    def test_state_bridge_has_recovery_triggers(self):
        automation = native_bridge.build_state_automation(self.controls)
        trigger_types = {trigger["trigger"] for trigger in automation["triggers"]}

        self.assertEqual(trigger_types, {"homeassistant", "time_pattern", "state"})
        self.assertTrue(automation["actions"])

    def test_temperature_values_keep_one_decimal(self):
        mapping = self.controls["climate_living_target"]
        action = native_bridge.update_action("climate_living_target", mapping)

        self.assertIn("%.1f", action["data"]["value"])


if __name__ == "__main__":
    unittest.main()
