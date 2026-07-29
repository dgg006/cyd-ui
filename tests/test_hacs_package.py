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

    def test_release_urls_are_intentionally_not_published_yet(self):
        manifest = json.loads((INTEGRATION_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("/OWNER/", manifest["documentation"])
        self.assertIn("/OWNER/", manifest["issue_tracker"])


if __name__ == "__main__":
    unittest.main()
