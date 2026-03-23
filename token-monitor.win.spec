# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

KEEP_TRANSLATIONS = {
    'qtbase_zh_CN.qm',
    'qtbase_zh_TW.qm',
}

EXCLUDED_BINARIES = {
    'PySide6/Qt6Pdf.dll',
    'PySide6/Qt6Qml.dll',
    'PySide6/Qt6QmlMeta.dll',
    'PySide6/Qt6QmlModels.dll',
    'PySide6/Qt6QmlWorkerScript.dll',
    'PySide6/Qt6Quick.dll',
    'PySide6/Qt6VirtualKeyboard.dll',
    'PySide6/plugins/generic/qtuiotouchplugin.dll',
    'PySide6/plugins/imageformats/qgif.dll',
    'PySide6/plugins/imageformats/qicns.dll',
    'PySide6/plugins/imageformats/qico.dll',
    'PySide6/plugins/imageformats/qjpeg.dll',
    'PySide6/plugins/imageformats/qpdf.dll',
    'PySide6/plugins/imageformats/qtga.dll',
    'PySide6/plugins/imageformats/qtiff.dll',
    'PySide6/plugins/imageformats/qwbmp.dll',
    'PySide6/plugins/imageformats/qwebp.dll',
    'PySide6/plugins/networkinformation/qnetworklistmanager.dll',
    'PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll',
    'PySide6/plugins/platforms/qdirect2d.dll',
    'PySide6/plugins/platforms/qminimal.dll',
    'PySide6/plugins/platforms/qoffscreen.dll',
    'PySide6/plugins/styles/qmodernwindowsstyle.dll',
}


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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
a.binaries = [
    entry for entry in a.binaries
    if entry[0].replace('\\', '/') not in EXCLUDED_BINARIES
]
a.datas = [
    entry for entry in a.datas
    if not (
        entry[0].replace('\\', '/').startswith('PySide6/translations/')
        and entry[0].split('\\')[-1].split('/')[-1] not in KEEP_TRANSLATIONS
    )
]
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
    icon='src/token_monitor/assets/token_orb.ico',
)
