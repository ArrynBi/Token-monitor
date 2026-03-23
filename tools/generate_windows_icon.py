from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_svg_to_png(svg_path: Path, size: int) -> Image.Image:
    renderer = QSvgRenderer(QByteArray(svg_path.read_bytes()))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {svg_path}")

    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    ptr = image.bits()
    return Image.frombuffer("RGBA", (size, size), bytes(ptr), "raw", "BGRA", 0, 1)


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    assets_dir = project_root / "src" / "token_monitor" / "assets"
    svg_path = assets_dir / "token_orb.svg"
    ico_path = assets_dir / "token_orb.ico"

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    _ = app

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [render_svg_to_png(svg_path, size) for size in sizes]
    images[0].save(ico_path, format="ICO", sizes=[(size, size) for size in sizes], append_images=images[1:])

    print(f"Generated Windows icon: {ico_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
