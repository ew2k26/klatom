# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

src_path = os.path.abspath('.')

a = Analysis(
    ['mod_gui.py'],
    pathex=[src_path],
    binaries=[],
    datas=[],
    hiddenimports=[
        'aiohttp',
        'rich',
        'rich.console',
        'rich.panel',
        'rich.table',
        'rich.text',
        'rich.box',
        'rich.prompt',
        'rich.live',
        'rich._null_file',
        'checker',
        'config',
        'proxy',
        'engine',
        'ui',
        'wizard',
        'auth',
        'crypto',
        'security',
        'test_mode',
        'mod_gui',
        'gui',
        'github_loader',
        'generate_token',
        'session_info',
        'setup_github',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False if sys.platform == 'win32' else False,
    win_private_assemblies=False if sys.platform == 'win32' else False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon_path = os.path.join(src_path, 'ew2.ico')
_icon = _icon_path if os.path.exists(_icon_path) else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ew2-Mod',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
