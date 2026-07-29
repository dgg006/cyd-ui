import importlib.util
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("configurator_server", PROJECT_ROOT / "configurator" / "server.py")
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)

class ConfiguratorValidationTests(unittest.TestCase):
    def setUp(self):
        self.ui = json.loads((PROJECT_ROOT / "config" / "ui.json").read_text(encoding="utf-8"))
        self.backend_map = json.loads((PROJECT_ROOT / "config" / "backend-map.json").read_text(encoding="utf-8"))

    def test_current_project_is_valid(self):
        self.assertEqual([], SERVER.validate_project(self.ui, self.backend_map))

    def test_duplicate_control_is_rejected(self):
        self.ui["pages"][1]["controls"][0]["id"] = self.ui["pages"][0]["controls"][0]["id"]
        self.assertTrue(any("repetido" in e for e in SERVER.validate_project(self.ui, self.backend_map)))

    def test_unknown_template_is_rejected(self):
        self.ui["pages"][0]["template"] = "camera"
        self.assertTrue(any("template desconocido" in e for e in SERVER.validate_project(self.ui, self.backend_map)))

    def test_invalid_color_is_rejected(self):
        self.ui["pages"][0]["controls"][0]["color"] = "blue"
        self.assertTrue(any("#RRGGBB" in e for e in SERVER.validate_project(self.ui, self.backend_map)))

    def test_partial_entity_name_is_rejected(self):
        self.backend_map["controls"]["living"]["entity_id"] = "luz living"
        self.assertTrue(any("ID válido" in e for e in SERVER.validate_project(self.ui, self.backend_map)))

    def test_known_mdi_icon_is_accepted(self):
        self.ui["pages"][0]["controls"][0]["icon"] = "mdi:lightbulb"
        self.assertEqual([], SERVER.validate_project(self.ui, self.backend_map))

    def test_unknown_mdi_icon_is_rejected(self):
        self.ui["pages"][0]["controls"][0]["icon"] = "mdi:no-existe"
        self.assertTrue(any("icon" in error.lower() for error in SERVER.validate_project(self.ui, self.backend_map)))

    def test_icon_catalog_matches_firmware_registry(self):
        import re

        registry = (PROJECT_ROOT / "components" / "ui_engine" / "icon_registry.cpp").read_text(encoding="utf-8")
        catalog_names = {item["name"] for item in SERVER.ICON_CATALOG}
        registry_names = set(re.findall(r'\{"(mdi:[^"]+)",', registry))
        self.assertEqual(catalog_names, registry_names)

if __name__ == "__main__":
    unittest.main()
