# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\qt_data_extractor\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/qt_data_extractor/design/*.ui', 'design')],
    hiddenimports=['win32timezone', 'data_agent'],
    hookspath=['src/qt_data_extractor/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='data-extractor',
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
    icon=['static\\logo-256.ico'],
)
