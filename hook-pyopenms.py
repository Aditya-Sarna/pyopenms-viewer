# PyInstaller hook for pyopenms
# Collects all dynamic libraries that pyopenms depends on

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files
import os
from pathlib import Path

# Collect all .dylib files from pyopenms
datas = collect_data_files('pyopenms', include_py_files=False)
binaries = collect_dynamic_libs('pyopenms')

# Also explicitly collect all .dylib files from the pyopenms directory
try:
    import pyopenms
    pyopenms_dir = Path(pyopenms.__file__).parent
    for dylib in pyopenms_dir.glob('*.dylib'):
        binaries.append((str(dylib), 'pyopenms'))
except Exception as e:
    print(f"Warning: Could not collect pyopenms dylibs: {e}")

