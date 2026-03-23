# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


block_cipher = None
root = Path.cwd()
icon_file = root / 'src' / 'token_monitor' / 'assets' / 'token_orb.icns'


a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src/token_monitor/assets/token_orb.svg', 'token_monitor/assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Token悬浮球',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
)

app = BUNDLE(
    exe,
    name='Token悬浮球.app',
    icon=str(icon_file) if icon_file.exists() else None,
    bundle_identifier='com.arrynbi.token-orb',
)
