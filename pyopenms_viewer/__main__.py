"""Entry point for running pyopenms-viewer as a module.

Usage:
    python -m pyopenms_viewer [options] [files...]
"""

from multiprocessing import freeze_support

from pyopenms_viewer.cli import main

if __name__ == "__main__":
    freeze_support()
    main()
