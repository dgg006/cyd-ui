"""Small, memory-safe artwork preparation shared by CYD UI bridges."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw, ImageOps


ARTWORK_SIZE = 72
ARTWORK_SCALE = 4
DARK_ARTWORK_BACKGROUND = "#0B1219"
LIGHT_ARTWORK_BACKGROUND = "#EAF0F4"


def artwork_background(ui: dict[str, Any] | None) -> str:
    """Return the exact LVGL page color behind multimedia artwork."""
    settings = ui.get("settings", {}) if isinstance(ui, dict) else {}
    appearance = settings.get("appearance", {}) if isinstance(settings, dict) else {}
    return (
        LIGHT_ARTWORK_BACKGROUND
        if isinstance(appearance, dict) and appearance.get("mode") == "light"
        else DARK_ARTWORK_BACKGROUND
    )


def circular_artwork_jpeg(
    raw: bytes, *, size: int = ARTWORK_SIZE, background: str = DARK_ARTWORK_BACKGROUND
) -> bytes:
    """Crop, circle-mask, antialias and encode artwork for a non-PSRAM CYD."""
    if size < 8 or size > 256:
        raise ValueError("artwork size is outside the supported range")
    supersampled = size * ARTWORK_SCALE
    background_rgb = Image.new("RGB", (1, 1), background).getpixel((0, 0))
    with Image.open(io.BytesIO(raw)) as source:
        square = ImageOps.fit(
            source.convert("RGB"),
            (supersampled, supersampled),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
    mask = Image.new("L", (supersampled, supersampled), 0)
    ImageDraw.Draw(mask).ellipse(
        (0, 0, supersampled - 1, supersampled - 1), fill=255
    )
    canvas = Image.new("RGB", square.size, background_rgb)
    canvas.paste(square, (0, 0), mask)
    final = canvas.resize((size, size), Image.Resampling.LANCZOS)
    encoded = io.BytesIO()
    final.save(encoded, "JPEG", quality=88, optimize=True, subsampling=0)
    return encoded.getvalue()
