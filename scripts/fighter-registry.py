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
from fighter_registry import resolve, suggest_compatibility, RegistryError, MAX_PACKS, fingerprint
from fighter_native import RetailCatalog, ADAPTER
from fighter_names import encode_names
from fighter_bindings import encode_bindings
from fighter_window import encode_window
from fighter_assets import unpack as unpack_asset, MAX_ASSET
from fighter_elf import Model
from mods import ordinary_path
from fighter_archive import MAX_ARCHIVE

MAX_DOCUMENT = 8 * 1024**2
MAX_INPUT = 32 * 1024**2
MAX_REPORT = 32 * 1024**2
ROOT = Path(__file__).resolve().parents[1]


from fighter_build import unique, non_finite, document, documents
import fighter_build as build


def retail_catalog(path):
    return build.retail_catalog(path, pin_path=ROOT / 'config/fighter-native-baseline.json')


def compile_inputs(sod, paths, packs, ledger=None, **options):
    return build.compile_inputs(sod, paths, packs, ledger, catalog=retail_catalog(sod),
                                pin_path=ROOT / 'config/fighter-native-baseline.json', **options)


def write_preview(data, report, resources=None):
    return build.write_preview(data, report, resources,
                               cache_root=ROOT / 'logs/fighter-native-preview', max_report=MAX_REPORT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect-native')
    inspect.add_argument('sod', type=Path)
    inspect_model = sub.add_parser('inspect-model', help='Inspect data-only ELF envelope; no runtime activation')
    inspect_model.add_argument('model', type=Path)
    inspect_skin = sub.add_parser('inspect-skin', help='Check skin palette and selector bounds; no runtime activation')
    inspect_skin.add_argument('model', type=Path)
    inspect_geometry = sub.add_parser('inspect-geometry', help='Check observed stream/index/material structures; no runtime activation')
    inspect_geometry.add_argument('model', type=Path)
    inspect_geometry.add_argument('--textures', type=Path, help='Also require every model shape in this validated SHPX file')
    inspect_textures = sub.add_parser('inspect-textures', help='Validate supported SHPX data and references; no runtime activation')
    inspect_textures.add_argument('textures', type=Path)
    inspect_motion = sub.add_parser('inspect-motion-index', help='Inspect native motion table partitions; no runtime activation')
    inspect_motion.add_argument('motion', type=Path)
    inspect_motion.add_argument('--check-links', action='store_true', help='Validate established move/parameter index namespaces; no runtime activation')
    inspect_record = sub.add_parser('inspect-motion-record', help='Inspect raw typed fields; semantic links remain unvalidated')
    inspect_record.add_argument('motion', type=Path)
    inspect_record.add_argument('--kind', choices=('move', 'core', 'parameter'), required=True)
    inspect_record.add_argument('--index', type=int, required=True, help='Zero-based row index')
    inspect_record.add_argument('--partition', type=int, choices=(0, 1), default=0)
    inspect_animation = sub.add_parser('inspect-animation-envelope', help='Inspect split animation ELF/name envelopes; no runtime activation')
    inspect_animation.add_argument('data', type=Path, help='Native .ord resource')
    inspect_animation.add_argument('links', type=Path, help='Matching native .orl resource')
    inspect_animation.add_argument('--names', type=Path, help='Optional separately validated native .mnl list')
    inspect_animation.add_argument('--check-links', action='store_true', help='Check bank name lookup and established child edges; curves remain unvalidated')
    inspect_animation.add_argument('--check-curves', action='store_true', help='Also inspect supported curve ranges; numerical/output-context validation remains required')
    inspect_complete = sub.add_parser('inspect-animation-model', help='Repack/inspect a complete animation ELF; no runtime activation')
    inspect_complete.add_argument('data', type=Path)
    inspect_complete.add_argument('--names', type=Path)
    inspect_complete.add_argument('--check-links', action='store_true')
    inspect_complete.add_argument('--check-curves', action='store_true')
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
        if args.command in ('inspect-animation-envelope', 'inspect-animation-model'):
            from fighter_animation import AnimationEnvelope
            parts = []
            paths = (args.data, args.links) if args.command == 'inspect-animation-envelope' else (args.data,)
            for path in paths + ((args.names,) if args.names is not None else ()):
                with path.open('rb') as stream:
                    parts.append(unpack_asset(stream.read(MAX_ASSET + 1)))
            envelope = (AnimationEnvelope(*parts) if args.command == 'inspect-animation-envelope'
                        else AnimationEnvelope.from_model(*parts))
            result = envelope.metadata()
            if args.check_links or args.check_curves:
                from fighter_animation import AnimationIndex
                index = AnimationIndex(envelope)
                result['index_links'] = index.metadata()
                if args.check_curves:
                    from fighter_animation_curves import CurveLayouts
                    result['curve_layouts'] = CurveLayouts(index).metadata()
        elif args.command in ('inspect-motion-index', 'inspect-motion-record'):
            from fighter_motion import MotionIndex
            with args.motion.open('rb') as stream:
                data = stream.read(MAX_ASSET + 1)
            motion = MotionIndex(data)
            result = (motion.record(args.kind, args.index, args.partition).metadata()
                      if args.command == 'inspect-motion-record' else motion.metadata())
            if args.command == 'inspect-motion-index' and args.check_links:
                from fighter_motion_links import MotionLinks
                result['index_links'] = MotionLinks(motion).metadata()
        elif args.command == 'inspect-textures':
            from fighter_xsh import Textures
            with args.textures.open('rb') as stream:
                data = stream.read(MAX_ASSET + 1)
            result = Textures(unpack_asset(data)).metadata()
        elif args.command in ('inspect-model', 'inspect-geometry', 'inspect-skin'):
            with args.model.open('rb') as stream:
                data = stream.read(MAX_ASSET + 1)
            model = Model(unpack_asset(data))
            result = model.metadata()
            if args.command == 'inspect-skin':
                from fighter_skin import Skin
                result['skin'] = Skin(model).metadata()
            if args.command == 'inspect-geometry':
                from fighter_geometry import Geometry
                geometry = Geometry(model)
                result['geometry'] = geometry.metadata()
                if args.textures:
                    from fighter_xsh import Textures
                    with args.textures.open('rb') as stream:
                        texture_data = stream.read(MAX_ASSET + 1)
                    textures = Textures(unpack_asset(texture_data))
                    geometry.require_textures(textures)
                    result['textures'] = textures.metadata()
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
            data, result, resources = compile_inputs(args.sod, args.packs, packs)
            if args.write_cache:
                result['preview_directory'] = write_preview(data, result, resources)
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
