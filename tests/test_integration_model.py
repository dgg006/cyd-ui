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

    def test_duplicate_control_is_rejected(self):
        self.ui["pages"][1]["controls"][0]["id"] = self.ui["pages"][0]["controls"][0]["id"]
        self.assertTrue(
            any("repetido" in error for error in MODEL.validate_document(self.ui, self.backend_map))
        )

    def test_revision_history_is_bounded_and_immutable(self):
        current = {
            "revision": 10,
            "updated_at": "old",
            "ui": self.ui,
            "backend_map": self.backend_map,
            "history": [{"revision": number} for number in range(10)],
        }
        result = MODEL.create_revision(current, self.ui, self.backend_map, "new")
        self.assertEqual(11, result["revision"])
        self.assertEqual(10, len(result["history"]))
        self.assertEqual(1, result["history"][0]["revision"])
        self.ui["pages"][0]["title"] = "modificado después"
        self.assertNotEqual("modificado después", result["ui"]["pages"][0]["title"])


if __name__ == "__main__":
    unittest.main()
