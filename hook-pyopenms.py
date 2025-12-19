# PyInstaller hook for pyopenms
# Collects all dynamic libraries that pyopenms depends on

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# Collect all .dylib files from pyopenms
datas = collect_data_files('pyopenms', include_py_files=False)
binaries = collect_dynamic_libs('pyopenms')
