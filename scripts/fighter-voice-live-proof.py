"""Read-only Windows native voice registration evidence for an owned voice.

Usage: python scripts/fighter-voice-live-proof.py PID SECONDS VOICE MASK OUTPUT
MASK bits are Character/Taunts/Enviro. Only consistent snapshots containing
the requested voice count as presence-mask observations. No event or memory is
injected; correlate actual missing requests with the native run log separately.
"""
import ctypes.wintypes as wt
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    pid, seconds, voice, expected = map(int, sys.argv[1:5])
    output = Path(sys.argv[5])
    if not (0 < seconds <= 3600 and 600 <= voice < 65535 and 0 <= expected <= 7):
        raise ValueError('Invalid sample budget or owned voice/mask')
    spec = importlib.util.spec_from_file_location('peek', ROOT / 'scripts/peek-guest.py')
    peek = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(peek)
    peek.k32.OpenProcess.restype = wt.HANDLE
    handle = peek.k32.OpenProcess(0x410, False, pid)
    if not handle:
        raise ValueError('Cannot read the selected test process')
    snapshots, seen, mismatches, reads, errors = [], set(), [], 0, 0
    try:
        symbol = peek.map_symbol(ROOT / 'build/win-x64-release/defjam_recomp.map', 'g_xbox_mem_offset')
        base = int.from_bytes(peek.read(handle, symbol, 8) or bytes(8), 'little')
        if not base:
            raise ValueError('Guest mapping is not ready')

        def read(address, size):
            value = peek.read(handle, base + address, size)
            if value is None or len(value) != size:
                raise ValueError('Unreadable/transitional registration')
            return value

        def word(address):
            return int.from_bytes(read(address, 4), 'little')

        families = {0: 1, 1: 1, 16625: 2, 16626: 2, 40962: 4, 40963: 4}
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                count, table = word(0x3ADB78), word(0x3ADB6C)
                if count > 256 or (count and not table):
                    raise ValueError('Transitional registration count')
                rows = []
                for index in range(count):
                    raw = read(table + 8 * index, 8)
                    header = int.from_bytes(raw[4:], 'little')
                    keys = read(header, 4)
                    rows.append((int.from_bytes(keys[:2], 'little'), int.from_bytes(keys[2:], 'little')))
                if count != word(0x3ADB78) or table != word(0x3ADB6C):
                    raise ValueError('Registration changed during sample')
                # Re-read the keys to exclude an unload/reuse during traversal.
                for index, keys in enumerate(rows):
                    header = word(table + 8 * index + 4)
                    if read(header, 4) != keys[0].to_bytes(2, 'little') + keys[1].to_bytes(2, 'little'):
                        raise ValueError('Registration keys changed during sample')
                mask = 0
                for family, owner in rows:
                    if owner == voice:
                        if family not in families:
                            raise ValueError('Unexpected owned category family')
                        mask |= families[family]
                reads += 1
                identity = tuple(rows)
                if identity not in seen:
                    seen.add(identity)
                    snapshots.append({'time': time.time(), 'pairs': rows, 'owned_mask': mask})
                if mask and mask != expected:
                    # Loading can be incremental. A snapshot is evidence to
                    # inspect, not automatic proof of a wrong stable load.
                    mismatches.append({'time': time.time(), 'mask': mask})
            except (ValueError, OverflowError, TypeError):
                errors += 1
            time.sleep(.25)
    finally:
        peek.k32.CloseHandle(handle)
    report = {'pid': pid, 'voice': voice, 'expected_mask': expected, 'consistent_reads': reads,
              'skipped_reads': errors, 'snapshots': snapshots, 'different_nonzero_masks': mismatches,
              'memory_modified': False, 'scope': 'registered banks only; actual event requests/playback checked separately'}
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('snapshots', 'different_nonzero_masks')}))


if __name__ == '__main__':
    main()
