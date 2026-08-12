import importlib.util
import io
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "cyd_ui_artwork_test", ROOT / "custom_components" / "cyd_ui" / "artwork.py"
)
ARTWORK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTWORK)


class ArtworkTests(unittest.TestCase):
    def _source(self) -> bytes:
        image = Image.new("RGB", (160, 100), "#E43B44")
        output = io.BytesIO()
        image.save(output, "PNG")
        return output.getvalue()

    def test_theme_background_matches_firmware_surface(self):
        self.assertEqual("#0B1219", ARTWORK.artwork_background(None))
        self.assertEqual(
            "#EAF0F4",
            ARTWORK.artwork_background(
                {"settings": {"appearance": {"mode": "light"}}}
            ),
        )

    def test_artwork_is_circular_antialiased_and_small(self):
        encoded = ARTWORK.circular_artwork_jpeg(
            self._source(), background="#0B1219"
        )
        self.assertLess(len(encoded), 16 * 1024)
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual((72, 72), image.size)
            corner = image.convert("RGB").getpixel((0, 0))
            center = image.convert("RGB").getpixel((36, 36))
            edge = image.convert("RGB").getpixel((3, 15))
        expected = (0x0B, 0x12, 0x19)
        self.assertLessEqual(max(abs(a - b) for a, b in zip(corner, expected)), 4)
        self.assertGreater(center[0], 180)
        self.assertNotEqual(corner, edge)


if __name__ == "__main__":
    unittest.main()
