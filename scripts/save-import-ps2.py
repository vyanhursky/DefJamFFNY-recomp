#!/usr/bin/env python3
"""Compatibility entry point. Use launcher Help > Import saves, or save-import.py.

Both entry points now use the same Xbox/PS2 importer and backup rules.
See docs/importing-saves.md.
"""
import os  # retained for callers of the original converter module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ps2_save_format import *
from save_import import main

if __name__ == '__main__':
    sys.exit(main())
