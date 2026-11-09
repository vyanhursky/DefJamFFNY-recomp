#!/usr/bin/env python3
"""Inspect the player's APT movies; shared format reader lives in setup/."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'setup'))
from fighter_apt import *  # keep the existing inspection API and command line

if __name__ == '__main__':
    main()
