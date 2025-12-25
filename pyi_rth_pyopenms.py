"""
PyInstaller runtime hook for pyopenms.

This hook runs when the frozen application starts, before any user code.
It sets up the Windows DLL search path so pyopenms can find its dependency DLLs.

Critical: This must run BEFORE pyopenms is imported. The hook modifies both
os.add_dll_directory() and PATH environment variable to ensure DLL loading works.
"""
import os
import sys

# Debug output with explicit flush to ensure visibility
def debug_print(msg):
    print(msg, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()

# In frozen mode, all DLLs should be in the same directory as the executable
# because hook-pyopenms.py places them there with: binaries.append((src, '.'))
if getattr(sys, 'frozen', False):
    debug_print("[pyi_rth_pyopenms] Runtime hook executing!")
    
    # Get the directory containing the executable
    exe_dir = sys._MEIPASS  # PyInstaller's temporary extraction directory
    debug_print(f"[pyi_rth_pyopenms] exe_dir (sys._MEIPASS): {exe_dir}")
    
    # CRITICAL: Add to PATH first (this affects LoadLibrary calls)
    # Windows searches PATH for DLLs when loading extension modules
    current_path = os.environ.get('PATH', '')
    if exe_dir not in current_path:
        os.environ['PATH'] = exe_dir + os.pathsep + current_path
        debug_print(f"[pyi_rth_pyopenms] Added exe_dir to PATH")
    
    # Add the executable directory to DLL search path
    # This is the Windows-specific API for DLL loading (Python 3.8+)
    if hasattr(os, 'add_dll_directory') and os.path.exists(exe_dir):
        try:
            os.add_dll_directory(exe_dir)
            debug_print(f"[pyi_rth_pyopenms] os.add_dll_directory({exe_dir}) succeeded")
        except Exception as e:
            debug_print(f"[pyi_rth_pyopenms] WARNING: os.add_dll_directory failed: {e}")
    
    # Also check if there's a 'share' subdirectory (fallback)
    share_dir = os.path.join(exe_dir, 'share')
    if os.path.exists(share_dir):
        debug_print(f"[pyi_rth_pyopenms] Found share directory: {share_dir}")
        
        # Add to PATH
        if share_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = share_dir + os.pathsep + os.environ['PATH']
            debug_print(f"[pyi_rth_pyopenms] Added share_dir to PATH")
        
        # Add to DLL search
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(share_dir)
                debug_print(f"[pyi_rth_pyopenms] os.add_dll_directory({share_dir}) succeeded")
            except Exception as e:
                debug_print(f"[pyi_rth_pyopenms] WARNING: Could not add share to DLL search: {e}")
    else:
        debug_print(f"[pyi_rth_pyopenms] No share directory found (not an error - DLLs might be in root)")
    
    debug_print("[pyi_rth_pyopenms] Runtime hook completed")
