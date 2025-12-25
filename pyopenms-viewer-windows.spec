# -*- mode: python ; coding: utf-8 -*-
# Windows-specific spec file for single-file executable
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
import sys
import os

# CRITICAL: Add pyopenms directory to DLL search path BEFORE Analysis runs
# This ensures PyInstaller's isolated subprocesses can find OpenMS.dll
if sys.platform == 'win32':
    import site
    site_packages = site.getsitepackages()[0]
    pyopenms_dir = os.path.join(site_packages, 'pyopenms')
    share_dir = os.path.join(site_packages, 'share')
    
    # Add to PATH for subprocess inheritance
    if os.path.exists(pyopenms_dir):
        os.environ['PATH'] = pyopenms_dir + os.pathsep + os.environ.get('PATH', '')
        print(f"[SPEC] Added to PATH: {pyopenms_dir}")
    if os.path.exists(share_dir):
        os.environ['PATH'] = share_dir + os.pathsep + os.environ.get('PATH', '')
        print(f"[SPEC] Added to PATH: {share_dir}")
    
    # Add to DLL search directories (Python 3.8+)
    if hasattr(os, 'add_dll_directory'):
        if os.path.exists(pyopenms_dir):
            os.add_dll_directory(pyopenms_dir)
            print(f"[SPEC] Added DLL directory: {pyopenms_dir}")
        if os.path.exists(share_dir):
            os.add_dll_directory(share_dir)
            print(f"[SPEC] Added DLL directory: {share_dir}")

datas = []
binaries = []
hiddenimports = []

# Collect all pyopenms resources
tmp_ret = collect_all('pyopenms')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Explicitly collect dynamic libraries from pyopenms
# Critical for Windows to find _pyopenms_1.pyd
binaries += collect_dynamic_libs('pyopenms')

# Collect plotly resources
tmp_ret = collect_all('plotly')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Add explicit hidden imports for pyopenms extension modules
hiddenimports += [
    'pyopenms._pyopenms_1',
    'pyopenms.version',
]

a = Analysis(
    ['pyopenms_viewer/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['pyi_rth_pyopenms.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Single-file executable for Windows
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pyopenms-viewer',
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
