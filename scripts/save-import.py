#!/usr/bin/env python3
"""Import Xbox or PS2 saves. Players: use launcher Help > Import saves instead.

Advanced use: python scripts/save-import.py save.zip --save-dir "<data>/save"
See docs/importing-saves.md. Standard library only; inputs are never edited.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from xbox_save_format import *  # compatibility for tools using the original signing API
from save_import import main

if __name__ == '__main__':
    sys.exit(main())
