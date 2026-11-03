#!/usr/bin/env python3
"""Local fighter R&D tools: native inspection and draft semantic conflict checking.

    python scripts/fighter-registry.py inspect-native path/to/assets/djv2.sod
    python scripts/fighter-registry.py resolve-preview baseline.json pack-a.json pack-b.json
    python scripts/fighter-registry.py export-retail path/to/assets/djv2.sod
    python scripts/fighter-registry.py compile-native-preview path/to/assets/djv2.sod pack-a.json --write-cache

These commands never install/enable mods, change saves, or advertise runtime
support. A draft snapshot's runtime_ready=false remains an explicit gate.
Native inspection prints metadata, not binary payloads. Redirect output to an
ignored local report; original game data must not be committed.
"""
import argparse
import json
import hashlib
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'setup'))
from fighter_sod import Database, MAX_IMAGE, SodError
from fighter_registry import resolve, suggest_compatibility, RegistryError, MAX_PACKS
from fighter_native import RetailCatalog, ADAPTER
from fighter_names import encode_names
from fighter_bindings import encode_bindings
from fighter_window import encode_window
from fighter_assets import unpack as unpack_asset, MAX_ASSET
from fighter_elf import Model

MAX_DOCUMENT = 8 * 1024**2
MAX_INPUT = 32 * 1024**2
MAX_REPORT = 32 * 1024**2
ROOT = Path(__file__).resolve().parents[1]


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


def retail_catalog(path):
    pin = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text(encoding='utf-8'))
    if pin['adapter'] != ADAPTER:
        raise ValueError('Native adapter/baseline pin mismatch')
    with path.open('rb') as stream:
        data = stream.read(MAX_IMAGE + 1)
    if len(data) > MAX_IMAGE:
        raise ValueError('SODB exceeds image budget')
    return RetailCatalog(data, pin['sha256'])


def write_preview(data, report):
    """Write only an ignored, content-addressed research cache; never install."""
    serialized = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    if len(serialized) > MAX_REPORT:
        raise ValueError('Generated preview report exceeds budget')
    root = ROOT / 'logs/fighter-native-preview'
    root.mkdir(parents=True, exist_ok=True)
    destination = root / report['cache_key']
    if not destination.exists():
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            stage = Path(temporary) / 'cache'
            (stage / 'assets').mkdir(parents=True)
            (stage / 'assets/djv2.sod').write_bytes(data)
            (stage / 'fighter-names.bin').write_bytes(encode_names(report['localization_entries']))
            (stage / 'fighter-bindings.bin').write_bytes(encode_bindings(report['handle_bindings']))
            if 'window' in report:
                (stage / 'fighter-window.bin').write_bytes(encode_window(report['window']))
            (stage / 'fighter-ledger.json').write_text(json.dumps(report['binding_ledger'], sort_keys=True, indent=2) + '\n', encoding='utf-8')
            (stage / 'report.json').write_bytes(serialized)
            try:
                os.rename(stage, destination)
            except OSError:
                if not destination.is_dir():
                    raise
    cached = destination / 'assets/djv2.sod'
    with cached.open('rb') as stream:
        actual = stream.read(MAX_IMAGE + 1)
    if len(actual) != len(data) or hashlib.sha256(actual).hexdigest() != report['cache_sha256']:
        raise ValueError('Existing preview cache is corrupt; original data was not changed')
    with (destination / 'fighter-names.bin').open('rb') as stream:
        names = stream.read(2 * 1024**2)
    if names != encode_names(report['localization_entries']):
        raise ValueError('Existing preview name bindings are corrupt; original data was not changed')
    with (destination / 'fighter-bindings.bin').open('rb') as stream:
        bindings = stream.read(1024**2)
    if bindings != encode_bindings(report['handle_bindings']):
        raise ValueError('Existing preview fighter bindings are corrupt; original data was not changed')
    if 'window' in report:
        with (destination / 'fighter-window.bin').open('rb') as stream:
            window = stream.read(1024**2)
        if window != encode_window(report['window']):
            raise ValueError('Existing preview fighter window is corrupt; original data was not changed')
    with (destination / 'fighter-ledger.json').open('rb') as stream:
        ledger = stream.read(MAX_REPORT + 1)
    if len(ledger) > MAX_REPORT or json.loads(ledger, object_pairs_hook=unique) != report['binding_ledger']:
        raise ValueError('Existing preview identity ledger is corrupt; original data was not changed')
    with (destination / 'report.json').open('rb') as stream:
        saved = stream.read(MAX_REPORT + 1)
    if len(saved) > MAX_REPORT or json.loads(saved, object_pairs_hook=unique) != json.loads(serialized):
        raise ValueError('Existing preview report is corrupt; original data was not changed')
    return str(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect-native')
    inspect.add_argument('sod', type=Path)
    inspect_model = sub.add_parser('inspect-model', help='Inspect data-only ELF envelope; no runtime activation')
    inspect_model.add_argument('model', type=Path)
    inspect_textures = sub.add_parser('inspect-textures', help='Validate supported SHPX data and references; no runtime activation')
    inspect_textures.add_argument('textures', type=Path)
    export = sub.add_parser('export-retail')
    export.add_argument('sod', type=Path)
    compile_preview = sub.add_parser('compile-native-preview')
    compile_preview.add_argument('sod', type=Path)
    compile_preview.add_argument('packs', type=Path, nargs='*')
    compile_preview.add_argument('--write-cache', action='store_true')
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
        if args.command == 'inspect-textures':
            from fighter_xsh import Textures
            with args.textures.open('rb') as stream:
                data = stream.read(MAX_ASSET + 1)
            result = Textures(unpack_asset(data)).metadata()
        elif args.command == 'inspect-model':
            with args.model.open('rb') as stream:
                data = stream.read(MAX_ASSET + 1)
            result = Model(unpack_asset(data)).metadata()
        elif args.command == 'inspect-native':
            if args.sod.stat().st_size > MAX_IMAGE:
                raise ValueError('SODB exceeds image budget')
            result = Database(args.sod.read_bytes()).character_metadata()
        elif args.command == 'export-retail':
            result = retail_catalog(args.sod).baseline()
        elif args.command == 'compile-native-preview':
            if len(args.packs) > MAX_PACKS:
                raise ValueError('Enabled pack count exceeds budget')
            packs, used = [], 0
            for path in args.packs:
                pack, size = document(path, MAX_INPUT - used)
                used += size
                packs.append(pack)
            data, result = retail_catalog(args.sod).compile(packs)
            if args.write_cache:
                result['preview_directory'] = write_preview(data, result)
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
