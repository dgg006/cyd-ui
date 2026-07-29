import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_ROOT = PROJECT_ROOT / "custom_components" / "cyd_ui"


class HacsPackageTests(unittest.TestCase):
    def test_repository_contains_one_custom_integration(self):
        integrations = [path for path in (PROJECT_ROOT / "custom_components").iterdir() if path.is_dir()]
        self.assertEqual([INTEGRATION_ROOT], integrations)

    def test_hacs_metadata_is_valid_json(self):
        metadata = json.loads((PROJECT_ROOT / "hacs.json").read_text(encoding="utf-8"))
        self.assertEqual("CYD UI", metadata["name"])
        self.assertEqual("2026.7.0", metadata["homeassistant"])

    def test_manifest_has_required_hacs_fields(self):
        manifest = json.loads((INTEGRATION_ROOT / "manifest.json").read_text(encoding="utf-8"))
        required = {"domain", "documentation", "issue_tracker", "codeowners", "name", "version"}
        self.assertTrue(required.issubset(manifest))
        self.assertEqual("cyd_ui", manifest["domain"])
        self.assertTrue(manifest["config_flow"])
        self.assertTrue(manifest["single_config_entry"])

    def test_runtime_files_are_present(self):
        expected = {
            "__init__.py",
            "config_flow.py",
            "const.py",
            "api.py",
            "bridge.py",
            "bridge_model.py",
            "migration.py",
            "manifest.json",
            "model.py",
            "storage.py",
            "frontend/cyd-ui-panel.js",
            "frontend/editor-app.js",
            "frontend/editor.css",
            "frontend/catalog.json",
            "frontend/icons.json",
            "frontend/initial-project.json",
            "frontend/materialdesignicons-webfont.ttf",
            "translations/en.json",
            "translations/es.json",
        }
        present = {
            path.relative_to(INTEGRATION_ROOT).as_posix()
            for path in INTEGRATION_ROOT.rglob("*")
            if path.is_file()
        }
        self.assertTrue(expected.issubset(present))

    def test_embedded_project_matches_public_example(self):
        embedded = json.loads(
            (INTEGRATION_ROOT / "frontend" / "initial-project.json").read_text(
                encoding="utf-8"
            )
        )
        example = json.loads(
            (PROJECT_ROOT / "examples" / "project.example.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(example, embedded)

    def test_icon_assets_match_firmware_catalog(self):
        embedded = json.loads(
            (INTEGRATION_ROOT / "frontend" / "icons.json").read_text(encoding="utf-8")
        )
        firmware = json.loads(
            (PROJECT_ROOT / "components" / "ui_engine" / "icons.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(firmware, embedded)

    def test_release_urls_and_codeowner_are_public(self):
        manifest = json.loads((INTEGRATION_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("https://github.com/dgg006/cyd-ui", manifest["documentation"])
        self.assertEqual("https://github.com/dgg006/cyd-ui/issues", manifest["issue_tracker"])
        self.assertEqual(["@dgg006"], manifest["codeowners"])

    def test_panel_uses_home_assistant_custom_panel_api(self):
        source = (INTEGRATION_ROOT / "__init__.py").read_text(encoding="utf-8")
        manifest = json.loads((INTEGRATION_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("panel_custom.async_register_panel", source)
        self.assertNotIn("async_register_built_in_panel", source)
        self.assertIn("panel_custom", manifest["dependencies"])

    def test_websocket_admin_checks_use_current_decorator(self):
        source = (INTEGRATION_ROOT / "api.py").read_text(encoding="utf-8")
        self.assertNotIn("connection.require_admin()", source)
        self.assertEqual(8, source.count("@websocket_api.require_admin"))

    def test_native_bridge_delivers_saved_ui_to_esphome(self):
        bridge = (INTEGRATION_ROOT / "bridge.py").read_text(encoding="utf-8")
        api = (INTEGRATION_ROOT / "api.py").read_text(encoding="utf-8")
        self.assertIn('APPLY_CONFIG_SERVICE = "cyd_ui_apply_config"', bridge)
        self.assertIn("async def async_apply_config", bridge)
        self.assertIn('"device_applied": device_applied', api)


if __name__ == "__main__":
    unittest.main()
