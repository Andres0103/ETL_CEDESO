# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Administrador\\Desktop\\raizal_v9_final\\raizal_v2\\backend\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\Administrador\\Desktop\\raizal_v9_final\\raizal_v2\\frontend\\public', 'frontend'), ('C:\\Users\\Administrador\\Desktop\\raizal_v9_final\\raizal_v2\\backend', 'backend')],
    hiddenimports=['flask', 'pandas', 'openpyxl', 'numpy', 'openpyxl.styles', 'openpyxl.utils'],
    hookspath=[],
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
    name='PaquetesAlimentarios_Raizal',
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
)
