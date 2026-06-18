# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for the Content Analysis backend.

Bundles protocol.py (entry point) along with all backend modules
into a single-folder executable named 'backend'.

Output: backend-dist/backend/backend.exe (Windows)

Note: markitdown[all] must be installed in the build environment:
  pip install "markitdown[all]"
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# All backend Python files
backend_dir = os.path.join(os.getcwd(), 'backend')

# Collect all markitdown submodules and data files
markitdown_datas, markitdown_binaries, markitdown_hiddenimports = collect_all('markitdown')

# Collect dependencies that markitdown uses internally
extra_hiddenimports = collect_submodules('markitdown')

# Some markitdown converters use these libraries — collect them if installed
optional_packages = [
    'pdfminer', 'pdfminer.high_level',
    'pptx', 'docx', 'openpyxl',
    'bs4', 'lxml', 'html5lib',
    'PIL', 'speech_recognition',
    'youtube_transcript_api',
    'charset_normalizer', 'certifi', 'urllib3', 'requests',
    'mammoth', 'ebooklib', 'olefile', 'extract_msg',
    'nbformat', 'nbconvert',
]

for pkg in optional_packages:
    try:
        extra_hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    [os.path.join(backend_dir, 'protocol.py')],
    pathex=[backend_dir],
    binaries=markitdown_binaries,
    datas=markitdown_datas,
    hiddenimports=[
        'analyzer', 'rules', 'utils', 'markitdown_handler',
    ] + markitdown_hiddenimports + extra_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'numpy',
        'torch', 'tensorflow', 'transformers',
    ],
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
