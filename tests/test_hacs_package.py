import json
import re
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

    def test_frontend_cache_version_matches_manifest(self):
        """A release must invalidate the browser cache for the editor assets."""
        manifest = json.loads((INTEGRATION_ROOT / "manifest.json").read_text(encoding="utf-8"))
        const_source = (INTEGRATION_ROOT / "const.py").read_text(encoding="utf-8")
        panel_source = (INTEGRATION_ROOT / "frontend" / "cyd-ui-panel.js").read_text(encoding="utf-8")
        const_version = re.search(r'^VERSION = "([^"]+)"$', const_source, re.MULTILINE)
        panel_version = re.search(r'^const ASSET_VERSION = "([^"]+)";', panel_source, re.MULTILINE)

        self.assertIsNotNone(const_version)
        self.assertIsNotNone(panel_version)
        self.assertEqual(manifest["version"], const_version.group(1))
        self.assertEqual(manifest["version"], panel_version.group(1))

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
            "services.yaml",
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

    def test_embedded_project_matches_current_editor_files(self):
        embedded = json.loads(
            (INTEGRATION_ROOT / "frontend" / "initial-project.json").read_text(
                encoding="utf-8"
            )
        )
        current_ui = json.loads(
            (PROJECT_ROOT / "config" / "ui.json").read_text(encoding="utf-8")
        )
        current_backend = json.loads(
            (PROJECT_ROOT / "config" / "backend-map.json").read_text(encoding="utf-8")
        )
        self.assertEqual(current_ui, embedded["ui"])
        self.assertEqual(current_backend, embedded["backend_map"])

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

    def test_settings_calibration_does_not_depend_on_field_positions(self):
        """Adding or reordering settings sections must not corrupt calibration."""
        editor = (INTEGRATION_ROOT / "frontend" / "editor-app.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("pageForm.firstElementChild", editor)
        self.assertNotIn('displayGrid.querySelectorAll("input")', editor)
        self.assertIn('ldrDarkField.querySelector("input")', editor)
        self.assertIn('ldrBrightField.querySelector("input")', editor)

    def test_remote_delivery_is_not_reported_as_a_save_failure(self):
        editor = (INTEGRATION_ROOT / "frontend" / "editor-app.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("delivery_note", editor)
        self.assertNotIn(
            'reload_error:result.device_applied?null:"la pantalla no está conectada',
            editor,
        )

    def test_reminder_center_is_packaged_end_to_end(self):
        api_source = (INTEGRATION_ROOT / "api.py").read_text(encoding="utf-8")
        panel_source = (INTEGRATION_ROOT / "frontend" / "cyd-ui-panel.js").read_text(
            encoding="utf-8"
        )
        editor_source = (INTEGRATION_ROOT / "frontend" / "editor-app.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('"cyd_ui/reminder/send"', api_source)
        self.assertIn('"cyd_ui/reminder/dismiss"', api_source)
        self.assertIn('id="reminderCenterButton"', panel_source)
        self.assertIn('"/api/reminder/send"', editor_source)
        self.assertIn('"/api/reminder/dismiss"', editor_source)
        self.assertIn("SHOW_ALARM_REMINDER_SERVICE", api_source)
        services = (INTEGRATION_ROOT / "services.yaml").read_text(encoding="utf-8")
        self.assertIn("show_reminder:", services)
        self.assertIn("sound_mode:", services)
        self.assertIn("snooze_minutes:", services)

    def test_release_urls_point_to_the_published_repository(self):
        manifest = json.loads((INTEGRATION_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("https://github.com/dgg006/cyd-ui", manifest["documentation"])
        self.assertEqual(
            "https://github.com/dgg006/cyd-ui/issues", manifest["issue_tracker"]
        )


if __name__ == "__main__":
    unittest.main()
