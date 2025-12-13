"""PyInstaller hook for pyOpenMS.

Ensures all pyOpenMS binaries and data files are collected.
"""

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

datas, binaries, hiddenimports = collect_all('pyopenms')

# Collect dynamic libraries explicitly
binaries += collect_dynamic_libs('pyopenms')

# Add hidden imports for all pyopenms submodules
hiddenimports += [
    'pyopenms._pyopenms_1',
    'pyopenms._pyopenms_2',
    'pyopenms._pyopenms_3',
    'pyopenms._pyopenms_4',
    'pyopenms._pyopenms_5',
    'pyopenms._all_modules',
]
