"""Compose native fighter menus and portraits over a verified language base."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from fighter_archive import MAX_ARCHIVE, portrait_aliases, Archive, store
from fighter_assets import unpack
from fighter_composition import language_base, MAX_DELTA_BYTES
from fighter_registry import fingerprint
from fighter_menu import compile_menu
from fighter_results import compile_results
from mods import ordinary_path, language_manifest, validate_textures, durable_rename
ROOT = Path(__file__).resolve().parents[1]


def original_screens(screens, *, pin_path=None):
    pin = json.loads((pin_path or ROOT / 'config/fighter-native-baseline.json').read_text(encoding='utf-8'))
    with screens.open('rb') as stream:
        source = stream.read(MAX_ARCHIVE + 1)
    if len(source) > MAX_ARCHIVE or hashlib.sha256(source).hexdigest() != pin['screens_sha256']:
        raise ValueError('Portrait adapter requires the supported original screens archive')
    return source


def pack_folder(folder):
    folder = ordinary_path(folder)
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,63}', folder.name) or '..' in folder.name:
        raise ValueError('Composition needs an ordinary supported pack folder')
    return folder


def texture_environment(folders, language=None):
    """Use the native pack order/root; never copy installed packs into the probe."""
    folders = [pack_folder(folder) for folder in folders]
    language = pack_folder(language) if language is not None else None
    roots = {folder.parent for folder in [*folders, *([language] if language else [])]}
    if len(roots) > 1:
        raise ValueError('Native language/texture composition needs one shared pack root')
    names = [folder.name for folder in folders]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError('Texture composition lists a pack twice')
    for folder in folders:
        validate_textures(folder)
    if language is not None and (language / 'manifest.ini').exists() and language not in folders:
        validate_textures(language)
    # pc_language may prepend its own image layer. Account for that before the
    # native texture loader's 1024-byte list would silently drop a trailing pack.
    total = list(names)
    if language is not None and (language / 'manifest.ini').exists() and language.name not in total:
        total.insert(0, language.name)
    if len(';'.join(total).encode('ascii')) >= 1024:
        raise ValueError('Texture composition exceeds the native pack-list budget')
    environment = {'RECOMP_TEXTURE_ROOT': str(next(iter(roots)))} if roots else {}
    if names:
        environment.update(RECOMP_TEXTURE_PACKS=';'.join(names), RECOMP_TEXTURE_TRACE='1')
    if language is not None:
        environment['RECOMP_LANGUAGE_PACK'] = language.name
    return environment


def prepare_language_screens(screens, folder, *, original_loader=original_screens, max_delta=MAX_DELTA_BYTES):
    folder = pack_folder(folder)
    parser = language_manifest(folder)
    edits, used = [], 0
    for target, delta in parser['files'].items():
        parts = tuple(part.strip() for part in target.split('|'))
        if parts[0].lower() == 'assets/djv2.sod':
            raise ValueError('Language changes to the fighter database need a semantic composition adapter')
        if parts[0].lower() != 'screens/screens.viv':
            continue  # The native language loader retains its other files and data-only XBE patch.
        path = folder / delta.strip()
        with path.open('rb') as stream:
            data = stream.read(max_delta - used + 1)
        used += len(data)
        if used > max_delta:
            raise ValueError('Language composition deltas exceed byte budget')
        edits.append((parts[1:], data))
    if not edits:
        return None
    source = original_loader(screens)
    return language_base(source, edits, hashlib.sha256(source).hexdigest())


def prepare_portraits(screens, report, *, language=None, resource_cache=None, cache_root=None, original_loader=original_screens):
    root = ordinary_path(cache_root or ROOT / 'logs/fighter-ui-preview')
    source = original_loader(screens)
    original = source
    if language is not None:
        composed, receipt = language
        if set(receipt) != {'schema', 'source_sha256', 'base_sha256', 'edits', 'cache_key'} \
                or receipt['schema'] != 'fighter-language-base-1' \
                or receipt['source_sha256'] != hashlib.sha256(source).hexdigest() \
                or receipt['base_sha256'] != hashlib.sha256(composed).hexdigest() \
                or receipt['cache_key'] != fingerprint({key: value for key, value in receipt.items() if key != 'cache_key'}):
            raise ValueError('Language screens provenance does not match its composed bytes')
        source = composed
    pairs = {report['bindings'][key]['selection_key']: report['bindings'][donor]['selection_key']
             for key, donor in report['portrait_donors'].items()}
    extended={report['bindings'][key]['selection_key'] for key,identifier in report.get('portrait_bindings',{}).items()
              if 'result_logo_2p' in report['portrait_resources'][identifier]['variants']}
    result = portrait_aliases(source, pairs, results=True,extended=extended)
    artwork = {}
    if report.get('portrait_resources'):
        from fighter_portrait import apply_portraits
        if resource_cache is None:
            raise ValueError('Authored portraits require their compiled cache')
        resources = {}
        for relative in report['portrait_files']:
            from mods import safe_relative
            path = ordinary_path(resource_cache.joinpath(*safe_relative(relative)))
            with path.open('rb') as stream:
                data = stream.read(16 * 1024**2 + 1)
            if len(data) > 16 * 1024**2:
                raise ValueError('Compiled portrait exceeds its budget')
            resources[relative] = data
        bindings = {report['bindings'][key]['selection_key']: (identifier, report['portrait_files'])
                    for key, identifier in report['portrait_bindings'].items()}
        if not set(bindings) <= set(pairs):
            raise ValueError('Authored portrait binding is not an owned custom alias')
        result = apply_portraits(result, bindings, resources)
        if bindings:
            from fighter_grid import compose_grid
            from fighter_portrait import PortraitBaseline
            result, artwork = compose_grid(result, report, PortraitBaseline(original, hashlib.sha256(original).hexdigest()))
    archive, replacements = Archive(result), {}
    names = {report['bindings'][key]['selection_key']: report['localization_entries'][report['bindings'][key]['native_name']]
             for key in report['portrait_donors']}
    for count in (() if report.get('binding_mode') == 'retail-only' else (2, 3, 4)):
        stem = f'chooseF{count}'
        path = 'screens/battle/' + stem + '.big'
        inner = Archive(unpack(archive.read(path)))
        records = list(report['menu_roster'].values()) if report.get('binding_mode') in ('logical-menu-only', 'participant-window') else None
        movie, constants, _ = compile_menu(inner.read(stem + '.apt'), inner.read(stem + '.const'), pairs, names, records, participants=count, artwork=artwork,logos=extended)
        replacements[path] = store(inner.compose(replacements={stem + '.apt': movie, stem + '.const': constants}))
        stem = f'matchSm{count}'
        path = 'screens/battle/' + stem + '.big'
        inner = Archive(unpack(archive.read(path)))
        movie, constants, _ = compile_results(inner.read(stem + '.apt'), inner.read(stem + '.const'), names, participants=count,logos=extended)
        replacements[path] = store(inner.compose(replacements={stem + '.apt': movie, stem + '.const': constants}))
    result = archive.compose(replacements=replacements)
    digest = hashlib.sha256(result).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    destination = ordinary_path(root / digest)
    if not destination.exists():
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            stage = Path(temporary) / 'cache'
            (stage / 'screens').mkdir(parents=True)
            (stage / 'screens/screens.viv').write_bytes(result)
            try:
                durable_rename(stage, destination)
            except OSError:
                if not ordinary_path(destination).is_dir():
                    raise
    path = ordinary_path(destination / 'screens/screens.viv')
    with path.open('rb') as stream:
        actual = stream.read(MAX_ARCHIVE + 1)
    if len(actual) != len(result) or hashlib.sha256(actual).hexdigest() != digest:
        raise ValueError('Existing portrait cache is corrupt')
    return path
