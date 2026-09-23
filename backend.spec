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

# markitdown 0.1.x splits functionality into subpackages and loads converters
# dynamically. Force-collect these so the bundled exe has them.
for _sub in ('markitdown.converters', 'markitdown.converter_utils'):
    try:
        extra_hiddenimports += collect_submodules(_sub)
    except Exception:
        pass

# markitdown discovers built-in converters via importlib.metadata entry points,
# which PyInstaller does not follow automatically. List them explicitly.
extra_hiddenimports += [
    'markitdown._markitdown', 'markitdown._base_converter',
    'markitdown._stream_info', 'markitdown._uri_utils',
    'markitdown.converters', 'markitdown.converter_utils',
    'magika',  # used by markitdown for content-type detection
]

# Ensure markitdown's package metadata (entry points) is bundled.
try:
    from PyInstaller.utils.hooks import copy_metadata
    markitdown_datas += copy_metadata('markitdown')
except Exception:
    pass
try:
    extra_hiddenimports += collect_submodules('magika')
    _mk_d, _mk_b, _mk_h = collect_all('magika')
    markitdown_datas += _mk_d
    markitdown_binaries += _mk_b
    extra_hiddenimports += _mk_h
except Exception:
    pass

# numpy is a transitive dependency of magika (used by markitdown). Bundle it.
try:
    _np_d, _np_b, _np_h = collect_all('numpy')
    markitdown_datas += _np_d
    markitdown_binaries += _np_b
    extra_hiddenimports += _np_h + ['numpy']
except Exception:
    pass

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
        'review_engine', 'dita_converter',
    ] + markitdown_hiddenimports + extra_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # NOTE: numpy is required by markitdown/magika — do NOT exclude it.
        'tkinter', 'matplotlib', 'scipy',
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
