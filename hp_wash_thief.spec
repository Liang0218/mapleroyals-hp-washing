# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Windows onedir build.
# Build on Windows:  pyinstaller hp_wash_thief.spec

block_cipher = None

a = Analysis(
    ['hp_wash_thief/ui/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('examples/int_gear.json', 'examples'),
        ('examples/default_equipment.json', 'examples'),
    ],
    hiddenimports=[
        'hp_wash_thief',
        'hp_wash_thief.core',
        'hp_wash_thief.core.api',
        'hp_wash_thief.core.equipment',
        'hp_wash_thief.core.optimizer',
        'hp_wash_thief.core.simulator',
        'hp_wash_thief.core.report',
        'hp_wash_thief.core.policy',
        'hp_wash_thief.core.policy.mp_wash_shortfall',
        'hp_wash_thief.core.policy.int_dump_shortfall',
        'hp_wash_thief.core.policy.mp_wash_hardcore',
        'hp_wash_thief.ui',
        'hp_wash_thief.ui.app',
        'hp_wash_thief.ui.equipment_panel',
        'hp_wash_thief.ui.result_panel',
        'hp_wash_thief.ui.user_errors',
        'hp_wash_thief.ui.resources',
        'customtkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# customtkinter is handled by PyInstaller hook-customtkinter.py (collect_all breaks on 6.x).

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MapleRoyalsHpWash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MapleRoyalsHpWash',
)
