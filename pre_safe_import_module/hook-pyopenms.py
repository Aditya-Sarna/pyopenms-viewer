# Pre-safe-import-module hook for pyopenms
# This runs BEFORE PyInstaller tries to import pyopenms in isolated subprocesses
# Critical for Windows where OpenMS.dll must be in PATH before importing

from PyInstaller.utils.hooks import get_package_paths
import os
import sys

def pre_safe_import_module(api):
    """
    Add pyopenms directory to DLL search path before importing.
    This hook runs in PyInstaller's isolated subprocess before the module is imported.
    """
    if sys.platform == 'win32':
        try:
            pkg_base, pkg_dir = get_package_paths('pyopenms')
            pyopenms_dir = pkg_dir
            share_dir = os.path.join(pkg_base, 'share')
            
            # Add to PATH (must be done before import)
            if os.path.exists(pyopenms_dir):
                os.environ['PATH'] = pyopenms_dir + os.pathsep + os.environ.get('PATH', '')
                
            if os.path.exists(share_dir):
                os.environ['PATH'] = share_dir + os.pathsep + os.environ.get('PATH', '')
            
            # Add to DLL search directories (Python 3.8+)
            if hasattr(os, 'add_dll_directory'):
                if os.path.exists(pyopenms_dir):
                    try:
                        os.add_dll_directory(pyopenms_dir)
                    except (OSError, FileNotFoundError):
                        pass
                        
                if os.path.exists(share_dir):
                    try:
                        os.add_dll_directory(share_dir)
                    except (OSError, FileNotFoundError):
                        pass
                        
        except Exception:
            # Silently fail - don't break PyInstaller if this doesn't work
            pass
