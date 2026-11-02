#!/usr/bin/env python3
"""Local fighter R&D tools: native inspection and draft semantic conflict checking.

    python scripts/fighter-registry.py inspect-native path/to/assets/djv2.sod
    python scripts/fighter-registry.py resolve-preview baseline.json pack-a.json pack-b.json

These commands never install/enable mods, change saves, or advertise runtime
support. A draft snapshot's runtime_ready=false remains an explicit gate.
Native inspection prints metadata, not binary payloads. Redirect output to an
ignored local report; original game data must not be committed.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'setup'))
from fighter_sod import Database, MAX_IMAGE, SodError
from fighter_registry import resolve, suggest_compatibility, RegistryError, MAX_PACKS

MAX_DOCUMENT = 8 * 1024**2
MAX_INPUT = 32 * 1024**2


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def non_finite(value):
    raise ValueError('Non-finite JSON number: ' + value)


def document(path, remaining=MAX_DOCUMENT):
    limit = min(MAX_DOCUMENT, remaining)
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Draft registry document exceeds budget')
    return json.loads(data, object_pairs_hook=unique, parse_constant=non_finite), len(data)


def documents(baseline_path, pack_paths):
    if len(pack_paths) > MAX_PACKS:
        raise ValueError('Enabled pack count exceeds budget')
    baseline, used = document(baseline_path)
    packs = []
    for path in pack_paths:
        pack, size = document(path, MAX_INPUT - used)
        used += size
        packs.append(pack)
    return baseline, packs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect-native')
    inspect.add_argument('sod', type=Path)
    preview = sub.add_parser('resolve-preview')
    preview.add_argument('baseline', type=Path)
    preview.add_argument('packs', type=Path, nargs='*')
    helper = sub.add_parser('suggest-compatibility')
    helper.add_argument('baseline', type=Path)
    helper.add_argument('packs', type=Path, nargs='+')
    helper.add_argument('--id', required=True)
    helper.add_argument('--choose', action='append', required=True, metavar='FIGHTER:COMPONENT=PACK')
    args = parser.parse_args()
    try:
        if args.command == 'inspect-native':
            if args.sod.stat().st_size > MAX_IMAGE:
                raise ValueError('SODB exceeds image budget')
            result = Database(args.sod.read_bytes()).character_metadata()
        elif args.command == 'resolve-preview':
            result = resolve(*documents(args.baseline, args.packs))
        else:
            baseline, packs = documents(args.baseline, args.packs)
            choices = {}
            for choice in args.choose:
                target, separator, provider = choice.partition('=')
                if not separator or target in choices:
                    raise ValueError('Invalid or duplicate compatibility choice')
                choices[target] = provider
            result = suggest_compatibility(baseline, packs, args.id, choices)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))
    except RegistryError as error:
        print(json.dumps({'ok': False, 'error': error.report()}, indent=2, sort_keys=True, ensure_ascii=True))
        return 1
    except (ValueError, OSError, SodError, UnicodeError, RecursionError) as error:
        print(json.dumps({'ok': False, 'error': {'code': 'input', 'message': str(error)}}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
