import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_ROOT = PROJECT_ROOT / "custom_components" / "cyd_ui"


def load_module(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        f"cyd_ui_model_test.{module_name}", INTEGRATION_ROOT / filename
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType("cyd_ui_model_test")
package.__path__ = [str(INTEGRATION_ROOT)]
sys.modules[package.__name__] = package
load_module("const", "const.py")
MODEL = load_module("model", "model.py")


class IntegrationModelTests(unittest.TestCase):
    def setUp(self):
        self.ui = json.loads(
            (PROJECT_ROOT / "config" / "ui.json").read_text(encoding="utf-8")
        )
        self.backend_map = json.loads(
            (PROJECT_ROOT / "config" / "backend-map.json").read_text(encoding="utf-8")
        )

    def test_current_project_is_safe_to_import(self):
        self.assertEqual([], MODEL.validate_document(self.ui, self.backend_map))

    def test_old_media_page_is_migrated_without_mutating_source(self):
        media = next(page for page in self.ui["pages"] if page["template"] == "media")
        artwork = next(control for control in media["controls"] if control["role"] == "artwork")
        media["controls"].remove(artwork)
        self.backend_map["controls"].pop(artwork["id"])
        migrated_ui, migrated_map, changed = MODEL.migrate_media_artwork(
            self.ui, self.backend_map
        )
        self.assertTrue(changed)
        migrated_media = next(
            page for page in migrated_ui["pages"] if page["template"] == "media"
        )
        migrated_artwork = next(
            control for control in migrated_media["controls"]
            if control["role"] == "artwork"
        )
        self.assertEqual("media_image_url", migrated_map["controls"][migrated_artwork["id"]]["attribute"])
        self.assertFalse(any(control["role"] == "artwork" for control in media["controls"]))
        self.assertEqual([], MODEL.validate_document(migrated_ui, migrated_map))

    def test_duplicate_control_is_rejected(self):
        self.ui["pages"][1]["controls"][0]["id"] = self.ui["pages"][0]["controls"][0]["id"]
        self.assertTrue(
            any("repetido" in error for error in MODEL.validate_document(self.ui, self.backend_map))
        )

    def test_corrupted_device_settings_are_rejected(self):
        self.ui["settings"]["display"]["brightness"] = None
        self.ui["settings"]["inactivity"]["mode"] = "0"
        self.ui["settings"]["night"]["end"] = "no"
        errors = MODEL.validate_document(self.ui, self.backend_map)
        self.assertTrue(any("brightness" in error for error in errors))
        self.assertTrue(any("Inactividad" in error for error in errors))
        self.assertTrue(any("Horario nocturno" in error for error in errors))

    def test_revision_history_is_bounded_and_immutable(self):
        current = {
            "revision": 10,
            "updated_at": "old",
            "ui": self.ui,
            "backend_map": self.backend_map,
            "history": [{"revision": number} for number in range(10)],
            "native_bridge_enabled": True,
            "temporary_automation_states": {"automation.old": "on"},
            "scheduled_reminders": [{"id": "mate"}],
            "reminder_history": [{"id": "hecho"}],
        }
        result = MODEL.create_revision(current, self.ui, self.backend_map, "new")
        self.assertEqual(11, result["revision"])
        self.assertEqual(10, len(result["history"]))
        self.assertEqual(1, result["history"][0]["revision"])
        self.assertTrue(result["native_bridge_enabled"])
        self.assertEqual(
            {"automation.old": "on"}, result["temporary_automation_states"]
        )
        self.assertEqual([{"id": "mate"}], result["scheduled_reminders"])
        self.assertEqual([{"id": "hecho"}], result["reminder_history"])
        self.ui["pages"][0]["title"] = "modificado después"
        self.assertNotEqual("modificado después", result["ui"]["pages"][0]["title"])

    def test_restore_is_non_destructive_and_creates_a_new_revision(self):
        old_ui = json.loads(json.dumps(self.ui))
        old_ui["pages"][0]["title"] = "Version anterior"
        current = {
            "revision": 5,
            "updated_at": "actual",
            "ui": self.ui,
            "backend_map": self.backend_map,
            "history": [{"revision": 3, "updated_at": "vieja", "ui": old_ui, "backend_map": self.backend_map}],
            "scheduled_reminders": [{"id": "no_perder"}],
        }
        result = MODEL.restore_revision(current, 3, "restaurada")
        self.assertIsNotNone(result)
        self.assertEqual(6, result["revision"])
        self.assertEqual("Version anterior", result["ui"]["pages"][0]["title"])
        self.assertEqual(5, result["history"][-1]["revision"])
        self.assertEqual([{"id": "no_perder"}], result["scheduled_reminders"])

    def test_unknown_revision_is_not_restored(self):
        self.assertIsNone(MODEL.restore_revision({"history": []}, 99, "now"))


if __name__ == "__main__":
    unittest.main()
