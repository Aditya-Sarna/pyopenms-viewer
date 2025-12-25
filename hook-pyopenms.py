# PyInstaller hook for pyopenms
# Collect the entire package (dylibs, data files, hidden imports) so that the
# bundled app ships every dependency required by libOpenMS and Qt.

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
import os
import sys

datas, binaries, hiddenimports = collect_all('pyopenms')

# Explicitly collect dynamic libraries from pyopenms package
# This is critical on Windows where DLLs may not be picked up by collect_all
binaries += collect_dynamic_libs('pyopenms')

# Add site-packages pyopenms directory to binary search path
# This helps PyInstaller find _pyopenms_1.pyd and other extension modules
try:
    import pyopenms
    pyopenms_dir = os.path.dirname(pyopenms.__file__)
    if os.path.exists(pyopenms_dir):
        for root, dirs, files in os.walk(pyopenms_dir):
            for file in files:
                if file.endswith(('.pyd', '.dll', '.so', '.dylib')):
                    src = os.path.join(root, file)
                    # Preserve directory structure relative to pyopenms
                    rel_path = os.path.relpath(root, os.path.dirname(pyopenms_dir))
                    binaries.append((src, rel_path))
except ImportError:
    pass

# Ensure all hidden imports for pyopenms submodules
hiddenimports += [
    'pyopenms',
    'pyopenms._pyopenms_1',
    'pyopenms.version',
]

