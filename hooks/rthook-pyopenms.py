"""Runtime hook for pyOpenMS.

Sets up DLL search paths on Windows before importing pyopenms.
"""

import os
import sys

if sys.platform == 'win32':
    # Add the _internal directory to DLL search path
    if hasattr(os, 'add_dll_directory'):
        # Python 3.8+ on Windows
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        os.add_dll_directory(base_path)

        # Also add pyopenms directory if it exists
        pyopenms_path = os.path.join(base_path, 'pyopenms')
        if os.path.exists(pyopenms_path):
            os.add_dll_directory(pyopenms_path)
