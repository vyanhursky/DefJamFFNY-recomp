#!/usr/bin/env python3
"""Read-only authoring bridge to the recomp's actual Fighter package contract.

Creator commands live in DefJam-Modding-Tools. This API keeps validation and
native format admission in the runtime repository, without installing a pack
or writing settings/profiles. Generated resources exist only in a temporary
validation workspace. Success is compilation evidence, not an in-game test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_build import retail_catalog, compile_inputs, write_preview, MAX_INPUT, MAX_PACKS
from fighter_packages import inventory
from fighter_presentation import prepare_portraits, prepare_language_screens
from mods import ordinary_path

PROTOCOL = 'fighter-authoring-api-1'


def validate(game, folders, language=None):
    folders = [ordinary_path(Path(folder)) for folder in folders]
    if not 0 < len(folders) <= MAX_PACKS or sum((folder / 'fighters.json').stat().st_size for folder in folders) > MAX_INPUT:
        raise ValueError('Pack manifests exceed the combined validation budget')
    packs = [inventory(folder) for folder in folders]
    paths = [folder / 'fighters.json' for folder in folders]
    if len({pack['id'] for pack in packs}) != len(packs):
        raise ValueError('Duplicate pack ID in validation set')
    before = [{p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in folder.rglob('*') if p.is_file()} for folder in folders]
    data, report, resources = compile_inputs(game / 'assets/djv2.sod', paths, packs, binding_window=True)
    with tempfile.TemporaryDirectory(prefix='fighter-validation-') as temporary:
        cache = Path(write_preview(data, report, resources, cache_root=Path(temporary) / 'native'))
        screens = game / 'screens/screens.viv'
        composed = prepare_language_screens(screens, language) if language else None
        prepare_portraits(screens, report, language=composed, resource_cache=cache,
                         cache_root=Path(temporary) / 'menus')
    for folder, files in zip(folders, before):
        after = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in folder.rglob('*') if p.is_file()}
        if after != files:
            raise ValueError('Pack changed during validation; retry from a stable workspace')
    return {'protocol': PROTOCOL, 'ok': True, 'native_compilation': True,
            'native_playtest': False, 'schema': 'fighter-registry-draft-1',
            'cache_key': report['cache_key'], 'added_fighters': report['added_count'],
            'binding_mode': report['binding_mode'],
            'packs': [{'id': pack['id'], 'version': pack['version'], 'files': files}
                      for pack, files in zip(packs, before)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('catalog', 'validate'))
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--pack', type=Path, action='append', default=[])
    parser.add_argument('--language', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'catalog':
            result = {'protocol': PROTOCOL, 'ok': True,
                      'baseline': retail_catalog(args.game / 'assets/djv2.sod').baseline()}
        else:
            if not args.pack:
                raise ValueError('Choose at least one pack folder')
            result = validate(args.game, args.pack, args.language)
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as error:
        print(json.dumps({'protocol': PROTOCOL, 'ok': False, 'error': str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
