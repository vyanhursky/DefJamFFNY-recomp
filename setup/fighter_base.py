"""Where the fighter compiler reads its base game files, and the hash each must have.

The compiler composes its own copies of five files from the player's verified dump:
assets/djv2.sod, screens/screens.viv, assets/entity.xml, assets/nis.viv and assets/v2ip.viv. On the
launcher's compile path every read of these five goes through path(), every pin of
config/fighter-native-baseline.json through pins(), and the game folder is passed explicitly, never
taken from the djv2.sod path (tests/unit/test_fighter_base.py keeps it that way).

This build always returns the file in the dump and the retail pin; nothing here is a setting. A fork
whose own tool patches one of the five files can change path() to return the patched copy and pins()
to give its hash, in one place. Every other check of the compiler stays as it is, so a patched file
that changes a table the compiler relies on is refused with the normal error. No compatibility with
any patched file is promised (docs/fighter-online-contract.md, section 8).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / 'config/fighter-native-baseline.json'
# The five files the compiler writes copies of, and the pin that names each one's retail hash.
FILES = {'assets/djv2.sod': 'sha256', 'screens/screens.viv': 'screens_sha256',
         'assets/entity.xml': 'entities_sha256', 'assets/nis.viv': 'nis_sha256',
         'assets/v2ip.viv': 'v2ip_sha256'}


def path(game, relative):
    """The file the compiler reads for relative, a path inside the game folder ('assets/nis.viv')."""
    return Path(game) / relative


def pins(pin_path=None):
    """The baseline pins, including the hash each of the five base files must have."""
    return json.loads(Path(pin_path or PIN_PATH).read_text(encoding='utf-8'))
