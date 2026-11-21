#!/usr/bin/env python3
"""Convert FFNY PS2 save exports to Recomp profiles (standard library only).

Close the game. Export FFNY from a PCSX2 memory card as .psu with mymc, or use
.max/.cbs/.sps/.xps/.psv, a raw FFNY save, a save folder, or a ZIP of exports.

    python scripts/save-import-ps2.py player.psu --check
    python scripts/save-import-ps2.py player.max --save-dir "<data>/save" --dry-run
    python scripts/save-import-ps2.py player.max --save-dir "<data>/save"

Options are skipped unless --include-options; their unlocks are copied into an
existing native Options file, keeping native preferences and leaderboards.
--force backs up an existing profile before replacing it. Inputs are never edited.
See docs/importing-ps2-saves.md for tested layouts and limitations.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import zipfile
import zlib

from ps2_save_containers import read_sources, require

_spec = importlib.util.spec_from_file_location('xbox_save_import', Path(__file__).with_name('save-import.py'))
xbox = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xbox)
PS2_HEADER = 28
IDENTITY_END = 92
PS2_PROFILE = 0x590C
XBOX_PROFILE = 0x5904
PS2_OPTIONS = 0x1494
XBOX_OPTIONS = 0x1490
PS2_BUILD = -2048007603
XBOX_BUILD = -2030886228
NAME = re.compile(r'[A-Za-z0-9 _-]{1,11}\Z')


def _crc_table():
    table = []
    for i in range(256):
        value = i << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04C11DB7 if value & 0x80000000 else 0)) & 0xFFFFFFFF
        table.append(value)
    return table


CRC_TABLE = _crc_table()


def mc02_checksum(data):
    """EA's non-reflected CRC: seed with complemented first big-endian dword.

    This is not zlib.crc32. Feed subsequent bytes into the low byte, advancing
    the polynomial from the high byte; complement the final accumulator.
    """
    require(len(data) >= 4, 'MC02 checksum block is too short')
    value = int.from_bytes(data[:4], 'big') ^ 0xFFFFFFFF
    for byte in data[4:]:
        value = (((value << 8) | byte) ^ CRC_TABLE[value >> 24]) & 0xFFFFFFFF
    return value ^ 0xFFFFFFFF


def parse_profile(raw):
    require(len(raw) >= IDENTITY_END, 'truncated PS2 MC02 header')
    magic, size, identity_size, payload_size, c0, c1, c2 = struct.unpack_from('<7I', raw)
    require(magic == 0x4D433032 and size == len(raw) and identity_size == 64 and
            payload_size == len(raw) - IDENTITY_END, 'PS2 MC02 header/size mismatch')
    identity, payload = raw[PS2_HEADER:IDENTITY_END], raw[IDENTITY_END:]
    require((c0, c1, c2) == tuple(mc02_checksum(b) for b in (identity, payload, raw[:24])),
            'PS2 MC02 checksum mismatch (damaged source)')
    tag = identity.split(b'\0', 1)[0]
    if tag == ('DJFFNY::User 17 %d' % PS2_BUILD).encode('ascii'):
        require(len(payload) == PS2_PROFILE, 'unsupported PS2 Story layout')
        field = payload[:16]
        require(b'\0' in field, 'unterminated profile name')
        name = field.split(b'\0', 1)[0].decode('ascii')
        require(NAME.fullmatch(name) is not None and name != 'Options', 'unsupported profile name')
        require(payload[0x17E:0x184] == bytes(6) and payload[0x4D8E:0x4D90] == bytes(2),
                'unsupported PS2 profile padding/layout')
        return name, payload
    require(tag == ('DJFFNY::Global 17 %d' % PS2_BUILD).encode('ascii') and
            len(payload) == PS2_OPTIONS, 'unsupported FFNY version or save kind')
    return 'Options', payload


def signed_profile(kind, payload):
    identity = ('DJFFNY::%s 17 %d' % (kind, XBOX_BUILD)).encode('ascii').ljust(64, b'\0')
    header = struct.pack('<4I', 0x4D433032, xbox.IDENTITY_END + len(payload), 64, len(payload)) + bytes(60)
    return xbox.resign(header + identity + payload, xbox.PORT_KEY)


def convert_story(payload):
    # Observed retail PS2 saves have six zero bytes before the embedded arrays
    # and two after the flags/counter at 0x4D8D. Refuse nonzero spans rather
    # than treating unknown platform fields as padding. Keep that counter.
    require(len(payload) == PS2_PROFILE and payload[0x17E:0x184] == bytes(6) and
            payload[0x4D8E:0x4D90] == bytes(2), 'unsupported PS2 profile layout')
    out = payload[:0x17E] + payload[0x184:0x4D8E] + payload[0x4D90:]
    require(len(out) == XBOX_PROFILE, 'converted profile length mismatch')
    return signed_profile('User', out)


def convert_options(payload, native):
    require(len(payload) == PS2_OPTIONS, 'unsupported PS2 Options layout')
    require(xbox.header_fault(native) is None and all(xbox.signatures_ok(native, xbox.PORT_KEY)) and
            len(native) == xbox.IDENTITY_END + XBOX_OPTIONS and
            native[xbox.HEADER:xbox.IDENTITY_END].startswith(b'DJFFNY::Global 17 '),
            'Options target must be a valid native Options save; start the game once first')
    out = bytearray(native[xbox.IDENTITY_END:])
    # Count/backing arrays: venues, fighters, song order and song count. Retain
    # native settings, leaderboard records and the final platform-specific flags.
    out[0x1214:0x148C] = payload[0x1214:0x148C]
    return signed_profile('Global', bytes(out))


def check_unlock_lists(payload, options=False):
    """Check the fixed capacities the native loader trusts before giving it data."""
    if options:
        venue_count, fighter_count = struct.unpack_from('<II', payload, 0x1214)
        require(venue_count <= 30 and fighter_count <= 80, 'Options unlock count exceeds capacity')
        lists = [(0x121C, venue_count, 23, 24), (0x1294, fighter_count, 7, 75)]
        songs = struct.unpack_from('<I', payload, 0x1488)[0]
        require(songs <= 39, 'Options song count exceeds capacity')
        require(all(v < 32 for v in struct.unpack_from('<%dI' % songs, payload, 0x13F8)),
                'Options contains unsupported song references')
    else:
        # Profile points to two inline story-event lists, after removing padding.
        lists = []
        for count_at, values_at, capacity, table, rows in ((0x51A0, 0x51A4, 140, 21, 95),
                                                         (0x53D4, 0x53D8, 96, 2, 81)):
            count = struct.unpack_from('<I', payload, count_at)[0]
            require(count <= capacity, 'Story event count exceeds capacity')
            lists.append((values_at, count, table, rows))
    for offset, count, table, rows in lists:
        values = struct.unpack_from('<%dI' % count, payload, offset)
        require(all(v >> 24 == table and (v & 0xFFFF) < rows for v in values),
                'unsupported saved database reference')


def options_target(title):
    candidates = [p for p in title.glob('*/Options') if p.parent.name.upper() in
                  {xbox.folder_name('Options'), '1A3F1B2E4ADF'}]
    require(len(candidates) == 1, '--include-options needs one native Options file in the save area; start the game once first')
    return candidates[0].parent


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', nargs='+', help='PS2 export(s), ZIP, raw profile, or save folder')
    ap.add_argument('--save-dir', help='native save area containing UserData')
    ap.add_argument('--install', help='install folder with installed.json')
    ap.add_argument('--check', action='store_true', help='validate and report sources without writing')
    ap.add_argument('--dry-run', action='store_true', help='preview import without writing')
    ap.add_argument('--force', action='store_true', help='back up and replace existing profiles')
    ap.add_argument('--include-options', action='store_true', help='also transfer global unlocks into existing native Options')
    args = ap.parse_args(argv)
    try:
        found = {}
        for label, inner_name, raw in read_sources(args.source):
            name, payload = parse_profile(raw)
            if name == 'Options':
                check_unlock_lists(payload, options=True)
            else:
                check_unlock_lists(convert_story(payload)[xbox.IDENTITY_END:])
            digest = hashlib.sha256(raw).hexdigest()
            if name in found:
                require(found[name][0] == raw, 'conflicting saves for %s; import one at a time' % name)
                print('same   %s: duplicate source skipped' % name)
                continue
            print('found  %s (%s, %d bytes) sha256 %s' % (name, label, len(raw), digest))
            found[name] = raw, payload
        require(found, 'no FFNY PS2 profiles found')
        if args.check:
            return 0
        resolved = xbox.resolve_save_dir(args)
        require(resolved is not None, 'pass --save-dir "<data folder>/save"')
        # Reject user-selected links, while permitting system aliases such as /tmp.
        require(not resolved.is_symlink(), 'save area must not be a symbolic link')
        save = resolved.resolve()
        title = save / 'UserData' / xbox.TITLE_ID
        for p in (save / 'UserData', title):
            require(not p.is_symlink(), 'save target contains a symbolic link')
        plans = []
        for name, (_, payload) in found.items():
            if name == 'Options':
                if not args.include_options:
                    print('skip   Options: pass --include-options to transfer global unlocks')
                    continue
                target = options_target(title)
                require(not target.is_symlink() and not (target / name).is_symlink(), 'linked Options target')
                data = convert_options(payload, (target / name).read_bytes())
            else:
                canonical = xbox.folder_name(name)
                value = int(canonical, 16)
                legacy = canonical[:-1] + '%X' % ((value | (value >> 32)) & 15)
                candidates = [p for p in title.glob('*') if p.name.upper() in {canonical, legacy}]
                require(len(candidates) <= 1, 'ambiguous native profile folders for %s' % name)
                target = candidates[0] if candidates else title / canonical
                data = convert_story(payload)
            require(not target.is_symlink(), 'profile target is a symbolic link')
            for source in args.source:
                source_path = Path(source).resolve()
                if source_path.is_file():
                    require(target not in source_path.parents, 'source is inside the profile being replaced')
            if target.exists() and not args.force:
                print('keep   %s: already exists; --force backs it up before replacement' % name)
                continue
            plans.append((name, target, data))
        if not plans:
            return 1
        # Everything, including conflicts and checksums, has passed before writing.
        for name, target, data in plans:
            print('%s %s -> %s' % ('would import' if args.dry_run else 'import', name, target))
            if args.dry_run:
                continue
            title.mkdir(parents=True, exist_ok=True)
            staged = Path(tempfile.mkdtemp(prefix='.ps2-import-', dir=title))
            backup = None
            try:
                if name == 'Options':
                    # Keep the existing native image/metadata too; never copy PS2 icons.
                    require(not any(p.is_symlink() for p in target.rglob('*')), 'linked Options content')
                    shutil.copytree(target, staged, dirs_exist_ok=True)
                (staged / name).write_bytes(data)
                (staged / 'SaveMeta.xbx').write_bytes(b'\xff\xfe' + ('Name=%s\r\n' % name).encode('utf-16le'))
                if target.exists():
                    backup = Path(tempfile.mkdtemp(prefix='import-backup-', dir=save)) / target.name
                    shutil.move(str(target), str(backup))
                    print('backup %s' % backup)
                try:
                    os.replace(staged, target)
                except OSError:
                    if backup is not None:
                        shutil.move(str(backup), str(target))
                    raise
            finally:
                if staged.exists():
                    shutil.rmtree(staged)
        print('%s %d profile(s)' % ('would import' if args.dry_run else 'imported', len(plans)))
        return 0
    except (OSError, ValueError, UnicodeError, struct.error, zipfile.BadZipFile,
            zlib.error, StopIteration, IndexError, ArithmeticError) as error:
        print('error: %s' % error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
