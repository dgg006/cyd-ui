import importlib.util
from pathlib import Path
import sys
import types
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_ROOT = PROJECT_ROOT / "custom_components" / "cyd_ui"
PACKAGE = "cyd_ui_bridge_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(INTEGRATION_ROOT)]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(
    f"{PACKAGE}.bridge_model", INTEGRATION_ROOT / "bridge_model.py"
)
MODEL = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = MODEL
spec.loader.exec_module(MODEL)


class NativeBridgeModelTests(unittest.TestCase):
    def test_unknown_or_unmapped_action_is_rejected(self):
        self.assertIsNone(MODEL.command_for_action("x", "toggle", None, "off", {}))
        mapping = {
            "entity_id": "light.test",
            "domain": "light",
            "action": "toggle",
            "allow_control": True,
        }
        self.assertIsNone(MODEL.command_for_action("x", "turn_on", mapping, "off", {}))

    def test_heater_power_is_limited_to_heat_and_off(self):
        mapping = {
            "entity_id": "climate.heater",
            "domain": "climate",
            "action": "toggle",
            "service": "toggle_hvac",
            "allow_control": True,
        }
        on = MODEL.command_for_action("heater", "toggle", mapping, "off", {})
        off = MODEL.command_for_action("heater", "toggle", mapping, "heat", {})
        self.assertEqual("heat", on["data"]["hvac_mode"])
        self.assertEqual("off", off["data"]["hvac_mode"])
        self.assertEqual("set_hvac_mode", on["service"])
        self.assertIsNone(
            MODEL.command_for_action("heater", "toggle", mapping, "unavailable", {})
        )

    def test_temperature_and_cover_are_bounded(self):
        temperature = MODEL.command_for_action(
            "up",
            "increment",
            {
                "entity_id": "climate.heater",
                "action": "increment",
                "service": "set_temperature",
                "temperature_delta": 1,
                "allow_control": True,
            },
            "heat",
            {"temperature": 21.5},
        )
        self.assertEqual(22.5, temperature["data"]["temperature"])
        cover = MODEL.command_for_action(
            "open_step",
            "open_step",
            {
                "entity_id": "cover.test",
                "action": "open_step",
                "service": "set_cover_position",
                "position_delta": 10,
                "allow_control": True,
            },
            "open",
            {"current_position": 95},
        )
        self.assertEqual(100, cover["data"]["position"])

    def test_numeric_state_keeps_requested_decimals(self):
        update = MODEL.update_for_state(
            "target",
            {"attribute": "temperature", "decimals": 1},
            "heat",
            {"temperature": 22},
        )
        self.assertEqual("22.0", update["value"])
        self.assertEqual("valid", update["reliability"])

    def test_binary_value_map_is_applied(self):
        update = MODEL.update_for_state(
            "motion",
            {"value_only": True, "value_map": {"on": "Movimiento", "off": "Libre"}},
            "off",
            {},
        )
        self.assertEqual("Libre", update["value"])

    def test_binary_sensor_uses_its_on_off_state_for_the_icon(self):
        active = MODEL.update_for_state(
            "motion",
            {
                "domain": "binary_sensor",
                "value_only": True,
                "value_map": {"on": "Movimiento", "off": "Libre"},
            },
            "on",
            {},
        )
        inactive = MODEL.update_for_state(
            "motion",
            {"domain": "binary_sensor", "value_only": True},
            "off",
            {},
        )
        self.assertTrue(active["active"])
        self.assertFalse(inactive["active"])


if __name__ == "__main__":
    unittest.main()
