from __future__ import annotations

from pathlib import Path
import shutil
import sys

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ICON_FILES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}


def render_svg(svg_path: Path, size: int, output_path: Path) -> None:
    renderer = QSvgRenderer(QByteArray(svg_path.read_bytes()))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {svg_path}")

    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    if not image.save(str(output_path), "PNG"):
        raise RuntimeError(f"Failed to save PNG: {output_path}")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    svg_path = project_root / "src" / "token_monitor" / "assets" / "token_orb.svg"
    iconset_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else project_root / "build" / "token_orb.iconset"

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    _ = app

    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    for filename, size in ICON_FILES.items():
        render_svg(svg_path, size, iconset_dir / filename)

    print(f"Generated macOS iconset: {iconset_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
