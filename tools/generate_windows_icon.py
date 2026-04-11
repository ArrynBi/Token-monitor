from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageEnhance, ImageFilter
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


def build_icon_frame(svg_path: Path, size: int) -> Image.Image:
    # Oversample first, then downscale and sharpen medium desktop sizes so Windows
    # can pick a crisper native frame instead of relying on extra scaling.
    oversample_size = min(max(size * 4, 256), 1024)
    image = render_svg_to_png(svg_path, oversample_size)
    if oversample_size != size:
        image = image.resize((size, size), Image.Resampling.LANCZOS)

    if 32 <= size <= 128:
        image = ImageEnhance.Contrast(image).enhance(1.08)
        image = image.filter(ImageFilter.UnsharpMask(radius=1.1, percent=165, threshold=2))
    elif size == 24:
        image = image.filter(ImageFilter.UnsharpMask(radius=0.8, percent=130, threshold=2))

    return image


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    assets_dir = project_root / "src" / "token_monitor" / "assets"
    svg_path = assets_dir / "token_orb.svg"
    ico_path = assets_dir / "token_orb.ico"

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    _ = app

    # Include the common Explorer/desktop high-DPI pick targets so Windows can
    # use a native frame instead of scaling 48->72 or 64->96.
    sizes = [16, 20, 24, 32, 40, 48, 64, 72, 80, 96, 128, 192, 256]
    frames = {size: build_icon_frame(svg_path, size) for size in sizes}
    largest_size = max(sizes)
    frames[largest_size].save(
        ico_path,
        format="ICO",
        bitmap_format="bmp",
        sizes=[(size, size) for size in sizes],
        append_images=[frames[size] for size in sizes if size != largest_size],
    )

    print(f"Generated Windows icon: {ico_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
