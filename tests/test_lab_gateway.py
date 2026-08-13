import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = PROJECT_ROOT / "tools" / "cyd_lab_gateway.py"
spec = importlib.util.spec_from_file_location("cyd_lab_gateway", MODULE_PATH)
gateway = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gateway
spec.loader.exec_module(gateway)


class RuntimeProjectTests(unittest.TestCase):
    def test_reads_native_integration_document(self):
        project = gateway.RuntimeProject.from_storage(
            {
                "revision": 12,
                "ui": {"schema_version": 1, "pages": []},
                "backend_map": {
                    "controls": {"living": {"entity_id": "light.living"}}
                },
            }
        )
        self.assertEqual(project.revision, 12)
        self.assertIn("living", project.mappings)

    def test_rejects_incomplete_document(self):
        with self.assertRaises(RuntimeError):
            gateway.RuntimeProject.from_storage({"revision": 1, "ui": None})


class GatewayHelpersTests(unittest.TestCase):
    def test_websocket_url_supports_wireguard_http(self):
        self.assertEqual(
            gateway._websocket_url("http://192.168.68.77:8123"),
            "ws://192.168.68.77:8123/api/websocket",
        )

    def test_climate_power_is_blocked_by_default(self):
        self.assertIn(
            ("climate", "set_hvac_mode"), gateway.REMOTE_BLOCKED_COMMANDS
        )

    def test_device_state_callback_is_deliberately_empty(self):
        self.assertIsNone(gateway.LabGateway._on_device_state(object()))


class GatewayApplyTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_revision_is_applied_only_once(self):
        bridge = gateway.LabGateway.__new__(gateway.LabGateway)
        bridge.project = gateway.RuntimeProject(
            revision=7,
            ui={"schema_version": 1, "pages": []},
            mappings={},
        )
        bridge._applied_revision = None
        bridge._apply_lock = asyncio.Lock()
        calls = []

        async def execute(name, data):
            calls.append((name, data))

        async def sync_all():
            return None

        bridge._execute = execute
        bridge._sync_all = sync_all

        await bridge._apply_project()
        await bridge._apply_project()

        self.assertEqual(len(calls), 1)
        self.assertEqual(bridge._applied_revision, 7)

    async def test_media_player_can_be_selected_by_index(self):
        bridge = gateway.LabGateway.__new__(gateway.LabGateway)
        bridge.project = gateway.RuntimeProject(
            revision=8,
            ui={"schema_version": 1, "pages": []},
            mappings={
                "media_player": {
                    "entity_ids": [
                        "media_player.living",
                        "media_player.kitchen",
                    ]
                },
                "media_volume": {"media_selector_id": "media_player"},
            },
        )
        bridge._media_selection = {}
        published = []

        async def publish(control_id, mapping):
            published.append(control_id)

        bridge._publish_control = publish

        self.assertTrue(await bridge._select_player("media_player", 1))
        self.assertEqual(
            bridge._effective_entity_id(
                "media_volume", bridge.project.mappings["media_volume"]
            ),
            "media_player.kitchen",
        )
        self.assertEqual(published, ["media_player", "media_volume"])

    async def test_media_player_rejects_out_of_range_index(self):
        bridge = gateway.LabGateway.__new__(gateway.LabGateway)
        bridge.project = gateway.RuntimeProject(
            revision=8,
            ui={"schema_version": 1, "pages": []},
            mappings={
                "media_player": {"entity_ids": ["media_player.living"]}
            },
        )
        bridge._media_selection = {}

        self.assertFalse(await bridge._select_player("media_player", 2))


if __name__ == "__main__":
    unittest.main()
