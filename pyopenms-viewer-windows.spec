# -*- mode: python ; coding: utf-8 -*-
# Windows-specific spec file for single-file executable
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
import sys
import os
import site

# CRITICAL: Add pyopenms directory to DLL search path BEFORE Analysis runs
# This ensures PyInstaller's isolated subprocesses can find OpenMS.dll
if sys.platform == 'win32':
    # Find pyopenms directory using PyInstaller's utilities
    from PyInstaller.utils.hooks import get_package_paths
    try:
        pkg_base, pkg_dir = get_package_paths('pyopenms')
        pyopenms_dir = pkg_dir  # This is site-packages/pyopenms
        share_dir = os.path.join(pkg_base, 'share')  # This is site-packages/share
        
        print(f"[SPEC EARLY] pkg_base (site-packages): {pkg_base}", flush=True)
        print(f"[SPEC EARLY] pyopenms directory: {pyopenms_dir}", flush=True)
        print(f"[SPEC EARLY] share directory: {share_dir}", flush=True)
        
        # APPROACH 1: Modify PATH (inherited by subprocesses)
        if os.path.exists(pyopenms_dir):
            old_path = os.environ.get('PATH', '')
            os.environ['PATH'] = pyopenms_dir + os.pathsep + old_path
            print(f"[SPEC EARLY] Added to PATH: {pyopenms_dir}", flush=True)
        else:
            print(f"[SPEC EARLY] WARNING: pyopenms directory not found: {pyopenms_dir}", flush=True)
            
        if os.path.exists(share_dir):
            os.environ['PATH'] = share_dir + os.pathsep + os.environ.get('PATH', '')
            print(f"[SPEC EARLY] Added to PATH: {share_dir}", flush=True)
        else:
            print(f"[SPEC EARLY] NOTE: share directory not found: {share_dir}", flush=True)
        
        # APPROACH 2: Force site.py to process .pth files again
        # This ensures zzz_pyopenms_dll.pth gets executed in subprocesses
        print(f"[SPEC EARLY] Forcing site.py to reprocess .pth files...", flush=True)
        for sitedir in site.getsitepackages():
            if os.path.isdir(sitedir):
                site.addsitedir(sitedir)
                print(f"[SPEC EARLY] Reprocessed site directory: {sitedir}", flush=True)
        
        # APPROACH 3: Add to DLL search directories (affects main process only)
        if hasattr(os, 'add_dll_directory'):
            if os.path.exists(pyopenms_dir):
                try:
                    dll_dir = os.add_dll_directory(pyopenms_dir)
                    print(f"[SPEC EARLY] Added DLL directory: {pyopenms_dir}", flush=True)
                except Exception as e:
                    print(f"[SPEC EARLY] Failed to add DLL directory: {e}", flush=True)
            if os.path.exists(share_dir):
                try:
                    os.add_dll_directory(share_dir)
                    print(f"[SPEC EARLY] Added DLL directory: {share_dir}", flush=True)
                except Exception as e:
                    print(f"[SPEC EARLY] Failed to add DLL directory (share): {e}", flush=True)
        
        # APPROACH 4: Test if OpenMS.dll is accessible
        openms_dll = os.path.join(pyopenms_dir, 'OpenMS.dll')
        if os.path.exists(openms_dll):
            print(f"[SPEC EARLY] ✓ Found OpenMS.dll at: {openms_dll}", flush=True)
        else:
            print(f"[SPEC EARLY] ✗ ERROR: OpenMS.dll not found at: {openms_dll}", flush=True)
            
    except Exception as e:
        print(f"[SPEC EARLY] ERROR: Failed to locate pyopenms: {e}", flush=True)
        import traceback
        traceback.print_exc()

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
    hookspath=['.', 'pre_safe_import_module'],  # Include both standard hooks and pre-safe-import hooks
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
