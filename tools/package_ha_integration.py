"""Create a reproducible manual-test package for the Home Assistant integration."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
INTEGRATION = ROOT / "custom_components" / "cyd_ui"
DIST = ROOT / "dist"
PACKAGE = DIST / "cyd-ui-ha-0.1.0.zip"
EXCLUDED_SUFFIXES = {".pyc"}
PRIVATE_MARKERS = (
    "C:\\Users\\",
    "192.168.",
    "10.0.",
)


def package() -> tuple[Path, str]:
    """Rebuild frontend assets, scan text files and create the ZIP."""
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_ha_frontend.py")],
        check=True,
        cwd=ROOT,
    )
    files = [
        path
        for path in INTEGRATION.rglob("*")
        if path.is_file()
        and path.suffix not in EXCLUDED_SUFFIXES
        and "__pycache__" not in path.parts
    ]
    for path in files:
        if path.suffix.lower() in {".py", ".js", ".json", ".css", ".md"}:
            text = path.read_text(encoding="utf-8")
            for marker in PRIVATE_MARKERS:
                if marker in text:
                    raise RuntimeError(f"Dato privado detectado en {path.name}: {marker}")

    DIST.mkdir(exist_ok=True)
    with ZipFile(PACKAGE, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT).as_posix())
    digest = sha256(PACKAGE.read_bytes()).hexdigest()
    (DIST / f"{PACKAGE.name}.sha256").write_text(
        f"{digest}  {PACKAGE.name}\n", encoding="ascii"
    )
    return PACKAGE, digest


if __name__ == "__main__":
    output, checksum = package()
    print(output)
    print(f"SHA256 {checksum}")
