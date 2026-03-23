#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ICONSET_DIR="$ROOT/build/token_orb.iconset"
ICNS_PATH="$ROOT/src/token_monitor/assets/token_orb.icns"
APP_PATH="$ROOT/dist/Token悬浮球.app"
RELEASE_DIR="$ROOT/release/macos"
PACKAGE_DIR="$RELEASE_DIR/Token悬浮球-macos"
ZIP_PATH="$ROOT/release/token-monitor-macos.zip"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found: $PYTHON_BIN"
  exit 1
fi

if ! command -v iconutil >/dev/null 2>&1; then
  echo "iconutil not found. Please run this script on macOS."
  exit 1
fi

cd "$ROOT"

"$PYTHON_BIN" "tools/generate_macos_icon.py" "$ICONSET_DIR"
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH"
"$PYTHON_BIN" -m PyInstaller --clean --noconfirm "token-monitor.mac.spec"

mkdir -p "$RELEASE_DIR"
rm -rf "$PACKAGE_DIR" "$ZIP_PATH"
mkdir -p "$PACKAGE_DIR"
cp -R "$APP_PATH" "$PACKAGE_DIR/"
if [ -f "$ROOT/config.example.json" ]; then
  cp "$ROOT/config.example.json" "$PACKAGE_DIR/"
fi
ditto -c -k --sequesterRsrc --keepParent "$PACKAGE_DIR" "$ZIP_PATH"

echo
echo "macOS build complete:"
echo "  $APP_PATH"
echo "Release package updated:"
echo "  $PACKAGE_DIR"
echo "ZIP package:"
echo "  $ZIP_PATH"
