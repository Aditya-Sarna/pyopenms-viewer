# PyInstaller hook for pyopenms
# Collect the entire package (dylibs, data files, hidden imports) so that the
# bundled app ships every dependency required by libOpenMS and Qt.

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, get_package_paths
import os
import sys

datas, binaries, hiddenimports = collect_all('pyopenms')

# Explicitly collect dynamic libraries from pyopenms package
# This is critical on Windows where DLLs may not be picked up by collect_all
binaries += collect_dynamic_libs('pyopenms')

# Find pyopenms installation directory without importing it
# (importing may fail if DLLs aren't in PATH during build)
try:
    pkg_base, pkg_dir = get_package_paths('pyopenms')
    
    # Collect ALL files from pyopenms directory (including share/OpenMS binaries)
    if os.path.exists(pkg_dir):
        for root, dirs, files in os.walk(pkg_dir):
            for file in files:
                src = os.path.join(root, file)
                # Preserve directory structure relative to site-packages
                rel_path = os.path.relpath(root, pkg_base)
                
                # Add binaries to binaries list, everything else to datas
                if file.endswith(('.pyd', '.dll', '.so', '.dylib', '.exe')):
                    binaries.append((src, rel_path))
                else:
                    # Only add data files that aren't already collected
                    if not any(src == d[0] for d in datas):
                        datas.append((src, rel_path))
    
    # Also check for share/ directory at site-packages level (OpenMS THIRDPARTY libs)
    share_dir = os.path.join(pkg_base, 'share')
    if os.path.exists(share_dir):
        for root, dirs, files in os.walk(share_dir):
            for file in files:
                src = os.path.join(root, file)
                rel_path = os.path.relpath(root, pkg_base)
                if file.endswith(('.dll', '.so', '.dylib', '.exe')):
                    binaries.append((src, rel_path))
                else:
                    if not any(src == d[0] for d in datas):
                        datas.append((src, rel_path))
except Exception as e:
    # If we can't locate pyopenms, log it but don't fail
    print(f"Warning: Could not fully collect pyopenms files: {e}")

# Ensure all hidden imports for pyopenms submodules
hiddenimports += [
    'pyopenms',
    'pyopenms._pyopenms_1',
    'pyopenms.version',
]

