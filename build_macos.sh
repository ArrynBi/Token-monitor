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
README_PATH="$PACKAGE_DIR/README-首次打开.txt"
LAUNCHER_PATH="$PACKAGE_DIR/打开Token悬浮球.command"

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

cat >"$README_PATH" <<'EOF'
Token悬浮球 macOS 版

首次打开建议：
1. 双击“打开Token悬浮球.command”
2. 它会自动去掉下载隔离标记，并启动 Token悬浮球.app
3. 第一次成功启动后，后续通常可以直接双击 Token悬浮球.app

配置文件位置：
~/Library/Application Support/Token悬浮球/config.json

说明：
- 下载包里附带了 config.example.json，可作为配置参考
- 如果 macOS 仍提示安全限制，请在“系统设置 -> 隐私与安全性”里允许打开
EOF

cat >"$LAUNCHER_PATH" <<'EOF'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$SCRIPT_DIR/Token悬浮球.app"

if [ ! -d "$APP_PATH" ]; then
  echo "未找到 Token悬浮球.app"
  exit 1
fi

xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true
open "$APP_PATH"
EOF

chmod +x "$LAUNCHER_PATH"
ditto -c -k --sequesterRsrc --keepParent "$PACKAGE_DIR" "$ZIP_PATH"

echo
echo "macOS build complete:"
echo "  $APP_PATH"
echo "Release package updated:"
echo "  $PACKAGE_DIR"
echo "ZIP package:"
echo "  $ZIP_PATH"
