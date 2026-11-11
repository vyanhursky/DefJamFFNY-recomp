"""Reuse only locally authenticated results of a complete fighter composition.

Packs never supply this receipt or its key. Inputs are freshly checked, output
bytes are rehashed, and the existing native-cache validator still runs on hits.
No size/mtime-only trust and no fallback from a damaged authenticated entry.
"""
import hashlib
import hmac
import importlib.metadata
import json
import os
from pathlib import Path
import re
import secrets
import sys

from fighter_build import MAX_REPORT, non_finite, unique, write_preview
from fighter_registry import fingerprint
from mods import atomic_bytes, check, ordinary_path, safe_dir, safe_relative, sync_directory, MAX_FILES

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'fighter-verified-cache-1'
MAX_OUTPUT = 2 * 1024**3
# Every external original consumed by the current composition/CAF/presentation
# adapters. Embedded members are covered by the hash of their containing file.
# A missing unused input is recorded too, so adding it invalidates the request.
ORIGINALS = ('assets/djv2.sod', 'screens/screens.viv', 'assets/entity.xml',
             'assets/nis.viv', 'assets/v2ip.viv', 'assets/blingfx.viv', 'assets/v2ta.viv',
             'motion/main_all.dat', 'motion/wres_all.viv', 'audio/speech2.viv',
             'assets/ai/ai.viv', 'motion/blazin.viv', 'assets/misc.viv',
             'audio/animtags.dat', 'motion/camera.xml',
             *(f'assets/v2cp_{i}.viv' for i in range(4)))
BASE_FILES = {'assets/djv2.sod', 'fighter-names.bin', 'fighter-bindings.bin',
              'fighter-window.bin', 'fighter-ledger.json', 'report.json'}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def file_hash(path, maximum=MAX_OUTPUT):
    path = ordinary_path(path)
    check(path.is_file() and 0 <= path.stat().st_size <= maximum, 'Invalid Fighter cache input/output: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    """Hash exact ordinary leaves; reject redirection before descending."""
    root = ordinary_path(root)
    check(root.is_dir(), 'Missing Fighter cache directory: ' + str(root))
    files, used = {}, 0
    for parent, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            check(ordinary_path(Path(parent) / name).is_dir(), 'Invalid Fighter cache directory')
        for name in names:
            path = ordinary_path(Path(parent) / name)
            relative = path.relative_to(root).as_posix()
            safe_relative(relative)
            used += path.stat().st_size
            check(len(files) < MAX_FILES and used <= MAX_OUTPUT, 'Fighter cache file/byte budget exceeded')
            files[relative] = file_hash(path)
    return files


def compiler_identity():
    files = set()
    for directory in ('setup', 'config', 'scripts'):
        for path in (ROOT / directory).rglob('*'):
            if path.suffix in ('.py', '.json') and not {'__pycache__', 'logs', 'build'} & set(path.relative_to(ROOT).parts):
                files.add(path)
    files.update((ROOT / 'src/patches').glob('fighter_*.[ch]'))
    files.update((ROOT / 'src/hooks').glob('fighter_*.[ch]'))
    files.update(ROOT / name for name in ('src/recomp_manual.c', 'CMakeLists.txt', '.gitmodules'))
    versions = {}
    for name in ('Pillow', 'numpy'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return fingerprint({'files': {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(files)},
                        'python': [sys.implementation.name, list(sys.version_info[:3]), sys.byteorder],
                        'libraries': versions})


def request(game, sources, packs, ledger, language, composed):
    originals = {}
    for name in ORIGINALS:
        path = ordinary_path(game / name)
        originals[name] = file_hash(path) if path.exists() else None
    return fingerprint({'schema': SCHEMA, 'compiler': compiler_identity(),
                        'originals': originals, 'packs': packs, 'sources': sources,
                        'ledger': ledger, 'mode': 'participant-window',
                        'language': inventory(language) if language else None,
                        'language_base': composed[1] if composed else None})


class VerifiedCache:
    def __init__(self, manager_root):
        self.root = safe_dir(ordinary_path(manager_root) / 'fighter-verified-cache')
        self.native = ordinary_path(manager_root / 'fighter-cache')
        self.ui = ordinary_path(manager_root / 'fighter-ui-cache')
        # Separate compiler-owned state, outside pack installation and cache
        # entries. The ordinary local-user boundary is unchanged; this is not
        # protection against an attacker who can replace the running compiler.
        path = ordinary_path(manager_root / 'fighter-cache-auth.key')
        if not path.exists():
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(path, flags, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(secrets.token_bytes(32)); stream.flush(); os.fsync(stream.fileno())
            sync_directory(path.parent)
        check(path.is_file() and path.stat().st_size == 32, 'Invalid Fighter cache authentication key')
        self.key = path.read_bytes()

    def path(self, key):
        check(type(key) is str and re.fullmatch('[0-9a-f]{64}', key), 'Invalid Fighter cache request')
        return ordinary_path(self.root / (key + '.json'))

    def read(self, key, snapshot, ledger):
        path = self.path(key)
        if not path.exists():
            return None
        with path.open('rb') as stream:
            raw = stream.read(MAX_REPORT + 1)
        check(len(raw) <= MAX_REPORT, 'Fighter cache receipt exceeds budget')
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=non_finite)
        check(type(value) is dict and set(value) == {'receipt', 'mac'}, 'Invalid Fighter cache receipt')
        receipt = value['receipt']
        check(type(value['mac']) is str and re.fullmatch('[0-9a-f]{64}', value['mac'])
              and hmac.compare_digest(value['mac'], hmac.new(self.key, encoded(receipt), 'sha256').hexdigest()),
              'Fighter cache receipt authentication failed')
        check(type(receipt) is dict and set(receipt) == {'schema', 'request', 'cache', 'screens', 'native_files', 'ui_files'}
              and receipt['schema'] == SCHEMA and receipt['request'] == key, 'Fighter cache request differs')
        for name in ('cache', 'screens'):
            check(type(receipt[name]) is str and re.fullmatch('[0-9a-f]{64}', receipt[name]), 'Invalid Fighter cache directory identity')
        native, ui = ordinary_path(self.native / receipt['cache']), ordinary_path(self.ui / receipt['screens'])
        # Entirely removed caches can be reconstructed by the normal compiler.
        # Partial/tampered results remain hard errors, just as write_preview.
        if not native.exists() or not ui.exists():
            return None
        check(inventory(native) == receipt['native_files'] and inventory(ui) == receipt['ui_files'],
              'Verified Fighter cache output is corrupt or changed')
        with (native / 'report.json').open('rb') as stream:
            raw = stream.read(MAX_REPORT + 1)
        check(len(raw) <= MAX_REPORT, 'Fighter cache report exceeds budget')
        report = json.loads(raw, object_pairs_hook=unique, parse_constant=non_finite)
        check(report['snapshot_sha256'] == snapshot and report['binding_ledger'] == ledger
              and report['cache_key'] == receipt['cache'], 'Fighter cache bindings differ from current inputs')
        resources = {name: (native / name).read_bytes() for name in receipt['native_files'] if name not in BASE_FILES}
        # Retain the existing exact resource/receipt/ledger/name/window checks.
        checked = write_preview((native / 'assets/djv2.sod').read_bytes(), report, resources, cache_root=self.native)
        check(Path(checked) == native, 'Fighter cache validator selected another result')
        screens = ordinary_path(ui / 'screens/screens.viv')
        check(set(receipt['ui_files']) == {'screens/screens.viv'}, 'Invalid Fighter presentation cache')
        return native, report, screens

    def write(self, key, native, report, screens):
        native, screens = ordinary_path(native), ordinary_path(screens)
        check(native.parent == self.native and native.name == report['cache_key']
              and re.fullmatch('[0-9a-f]{64}', native.name) and re.fullmatch('[0-9a-f]{64}', screens.parent.parent.name)
              and screens == self.ui / screens.parent.parent.name / 'screens/screens.viv',
              'Fighter cache outputs must belong to this manager')
        receipt = {'schema': SCHEMA, 'request': key, 'cache': native.name, 'screens': screens.parent.parent.name,
                   'native_files': inventory(native), 'ui_files': inventory(screens.parent.parent)}
        mac = hmac.new(self.key, encoded(receipt), 'sha256').hexdigest()
        raw = encoded({'receipt': receipt, 'mac': mac})
        check(len(raw) <= MAX_REPORT, 'Fighter cache receipt exceeds budget')
        atomic_bytes(self.path(key), raw)
