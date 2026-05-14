# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for the Content Analysis backend.

Bundles protocol.py (entry point) along with analyzer.py, rules.py, and utils.py
into a single-folder executable named 'backend'.

Output: backend-dist/backend/backend.exe (Windows)
"""

import os
import sys

block_cipher = None

# All backend Python files
backend_dir = os.path.join(os.getcwd(), 'backend')

a = Analysis(
    [os.path.join(backend_dir, 'protocol.py')],
    pathex=[backend_dir],
    binaries=[],
    datas=[],
    hiddenimports=['analyzer', 'rules', 'utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Must be console app for stdin/stdout communication
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend',
)
