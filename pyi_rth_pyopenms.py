"""
PyInstaller runtime hook for pyopenms.

This hook runs when the frozen application starts, before any user code.
It adds the DLL directory to the Windows DLL search path using os.add_dll_directory().

This is necessary because pyopenms C++ extension modules (_pyopenms_*.pyd) depend on
DLLs in the share/ directory (OpenMS.dll, Qt6Core.dll, etc.) that need to be findable
at runtime.
"""
import os
import sys

# In frozen mode, all DLLs should be in the same directory as the executable
# because hook-pyopenms.py places them there with: binaries.append((src, '.'))
if getattr(sys, 'frozen', False):
    # Get the directory containing the executable
    exe_dir = sys._MEIPASS  # PyInstaller's temporary extraction directory
    
    # Add the executable directory to DLL search path
    # This is the Windows-specific API for DLL loading (Python 3.8+)
    if hasattr(os, 'add_dll_directory') and os.path.exists(exe_dir):
        try:
            os.add_dll_directory(exe_dir)
            print(f"[pyi_rth_pyopenms] Added DLL directory: {exe_dir}")
        except Exception as e:
            print(f"[pyi_rth_pyopenms] Warning: Could not add DLL directory: {e}")
    
    # Also check if there's a 'share' subdirectory (fallback)
    share_dir = os.path.join(exe_dir, 'share')
    if os.path.exists(share_dir) and hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(share_dir)
            print(f"[pyi_rth_pyopenms] Added DLL directory: {share_dir}")
        except Exception as e:
            print(f"[pyi_rth_pyopenms] Warning: Could not add share DLL directory: {e}")
