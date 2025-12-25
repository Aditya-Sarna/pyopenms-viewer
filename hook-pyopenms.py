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
    
    # Collect ALL files from pyopenms directory
    if os.path.exists(pkg_dir):
        for root, dirs, files in os.walk(pkg_dir):
            for file in files:
                src = os.path.join(root, file)
                # Get path relative to pyopenms package (not site-packages)
                rel_path = os.path.relpath(root, pkg_dir)
                dest_dir = os.path.join('pyopenms', rel_path) if rel_path != '.' else 'pyopenms'
                
                # Add binaries to binaries list (they go to root of frozen app)
                # Add data files to datas list (preserving structure)
                if file.endswith(('.pyd', '.dll', '.so', '.dylib', '.exe')):
                    binaries.append((src, '.'))  # Place DLLs in root for easier loading
                else:
                    # Only add data files that aren't already collected
                    if not any(src == d[0] for d in datas):
                        datas.append((src, dest_dir))
    
    # Also check for share/ directory at site-packages level (OpenMS THIRDPARTY libs)
    # These DLLs are CRITICAL for pyopenms on Windows
    share_dir = os.path.join(pkg_base, 'share')
    if os.path.exists(share_dir):
        print(f"hook-pyopenms: Collecting OpenMS libraries from {share_dir}")
        for root, dirs, files in os.walk(share_dir):
            for file in files:
                src = os.path.join(root, file)
                # For DLLs in share/, put them in root directory for easier loading
                # For data files, preserve directory structure
                if file.endswith(('.dll', '.so', '.dylib', '.exe')):
                    binaries.append((src, '.'))  # Root directory
                    print(f"hook-pyopenms: Collecting binary {file} from share/")
                else:
                    rel_path = os.path.relpath(root, pkg_base)
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

