"""Fighter package inventory, composition and whole-pack activation validation."""
import hashlib
from pathlib import Path

from mods import check, ordinary_path, safe_relative, ALLOWED, MAX_FILES
from fighter_build import document, compile_inputs, retail_catalog, write_preview
from fighter_registry import validate_pack
from fighter_presentation import prepare_portraits, prepare_language_screens

MANIFEST = 'fighters.json'
CAPABILITY = 'fighters-v1'
MAX_FILE = 64 * 1024**2
MAX_PACK = 512 * 1024**2


def descriptors(value):
    if isinstance(value, dict):
        if set(value) == {'path', 'sha256'}:
            yield value
        else:
            for item in value.values():
                yield from descriptors(item)
    elif isinstance(value, list):
        for item in value:
            yield from descriptors(item)


def inventory(folder):
    """Only declared, hash-checked resource data and bounded README/LICENSE text."""
    folder = ordinary_path(folder)
    manifest, _ = document(ordinary_path(folder / MANIFEST))
    validate_pack(manifest)
    expected = {MANIFEST}
    hashes = {}
    for resource in manifest['resources']:
        for spec in descriptors(resource.get('source', {})):
            name = '/'.join(safe_relative(spec['path']))
            check(name != MANIFEST, 'Resource cannot alias the fighter manifest')
            check(name not in hashes or hashes[name] == spec['sha256'], 'Resource has conflicting hashes: ' + name)
            hashes[name] = spec['sha256']
            expected.add(name)
    used, actual, folded = 0, set(), set()
    for path in folder.rglob('*'):
        ordinary_path(path)
        if path.is_dir():
            continue
        name = path.relative_to(folder).as_posix()
        safe_relative(name)
        check(name.casefold() not in folded, 'Case-colliding fighter package file: ' + name)
        folded.add(name.casefold())
        check(len(folded) <= MAX_FILES and path.suffix.lower() in ALLOWED | {'.bin', '.xsh', '.wav', '.elf', '.o'},
              'Unsupported fighter package file name or population: ' + name)
        documentation = '/' not in name and name.lower() in ('readme.md', 'readme.txt', 'license.md', 'license.txt')
        check(name in expected or documentation, 'Undeclared fighter package file: ' + name)
        size = path.stat().st_size
        used += size
        check(0 < size <= (1024**2 if documentation else MAX_FILE) and used <= MAX_PACK, 'Fighter package exceeds byte budget')
        if name in hashes:
            check(hashlib.sha256(path.read_bytes()).hexdigest() == hashes[name], 'Fighter resource hash mismatch: ' + name)
        if documentation:
            path.read_text(encoding='utf-8')
        actual.add(name)
    check(expected <= actual, 'Fighter package is missing a declared resource')
    return manifest


def receipt(folder):
    manifest = inventory(folder)
    return {'capabilities': [CAPABILITY], 'texture_ids': [], 'wide_ids': [],
            'category': 'fighters', 'fighter_id': manifest['id'], 'fighter_version': manifest['version'],
            'fighter_count': len(manifest['fighters']), 'requires': manifest['requires']}


def enabled(state):
    value = state.get('fighters', [])
    check(isinstance(value, list) and len(value) <= 1024 and len(set(value)) == len(value), 'Invalid enabled fighter pack list')
    from fighter_registry import slug
    for identifier in value:
        slug(identifier)
    return value


def build(manager, state, *, ids=None, replacements=None, language=None):
    """Validate all inputs before writing a cache; never change settings/saves."""
    ids = enabled(state) if ids is None else ids
    replacements = replacements or {}
    paths, packs = [], []
    for identifier in sorted(ids):
        folder = replacements.get(identifier, manager.mods / identifier)
        saved = state['installed'].get(identifier)
        check(identifier in replacements or saved and CAPABILITY in saved['capabilities'],
              'Install the fighter pack before enabling it: ' + identifier)
        if identifier not in replacements:
            check(manager.unchanged(folder, saved), 'Fighter pack changed or is missing; restore or disable it: ' + identifier)
        pack = inventory(folder)
        check(pack['id'] == identifier, 'Fighter manifest identity differs from its installed folder')
        paths.append(folder / MANIFEST); packs.append(pack)
    sod = manager.game / 'assets/djv2.sod'
    data, report, resources = compile_inputs(sod, paths, packs, state.get('fighter_ledger'), binding_window=True)
    cache = Path(write_preview(data, report, resources, cache_root=manager.root / 'fighter-cache'))
    screens = manager.game / 'screens/screens.viv'
    composed = prepare_language_screens(screens, language) if language else None
    presentation = prepare_portraits(screens, report, language=composed, resource_cache=cache,
                                     cache_root=manager.root / 'fighter-ui-cache')
    return cache, report, presentation, composed


def candidate(manager, state, identifier, stage, new):
    """Validate inactive content with its dependencies; active updates also compose."""
    old = state['installed'].get(identifier, {})
    fighter = new and CAPABILITY in new.get('capabilities', [])
    if identifier in enabled(state):
        check(fighter, 'Disable this fighter pack before removing it or changing its category')
    if not fighter:
        check(CAPABILITY not in old.get('capabilities', []) or new is None,
              'Remove the fighter pack before replacing it with another mod category')
        return
    check(new['fighter_id'] == identifier and new['fighter_version'] == new['version'],
          'Fighter identity/version differs from its package receipt')
    ids, pending = set(), [identifier]
    while pending:
        item = pending.pop()
        if item in ids:
            continue
        ids.add(item)
        row = new if item == identifier else state['installed'].get(item)
        check(row and CAPABILITY in row.get('capabilities', []), 'Install required fighter dependency first: ' + item)
        pending.extend(row.get('requires', {}))
    if identifier in enabled(state):
        _, report, _, _ = build(manager, state, replacements={identifier: stage})
        state['fighter_ledger'] = report['binding_ledger']
    else:
        build(manager, state, ids=ids, replacements={identifier: stage})


def runtime_environment(cache, report, screens, language=None):
    environment = {'RECOMP_FIGHTER_NAMES': str(cache / 'fighter-names.bin'),
                   'RECOMP_FIGHTER_BINDINGS': str(cache / 'fighter-bindings.bin'),
                   'RECOMP_FIGHTER_RESEARCH_SOD': str(cache / 'assets/djv2.sod'),
                   'RECOMP_FIGHTER_RESEARCH_SCREENS': str(screens),
                   'RECOMP_FIGHTER_NAMES_PROBE': '1', 'RECOMP_FIGHTER_IMMUTABLE_REUSE': '1'}
    if report.get('binding_mode') == 'participant-window':
        environment['RECOMP_FIGHTER_WINDOW'] = str(cache / 'fighter-window.bin')
    if report.get('appearance_files'):
        for field, relative in [('MODELS', 'assets/v2ip.viv'), ('ENTITIES', 'assets/entity.xml'), ('CINEMATICS', 'assets/nis.viv')]:
            environment['RECOMP_FIGHTER_RESEARCH_' + field] = str(cache / relative)
            environment['RECOMP_FIGHTER_RESEARCH_' + field + '_SHA256'] = report['appearance_files'][relative]
    if report.get('behavior_files'):
        from fighter_behavior import environment as behavior_environment
        environment.update(behavior_environment(cache, report))
    if language:
        environment['RECOMP_FIGHTER_RESEARCH_LANGUAGE_BASE'] = language[1]['base_sha256']
        environment['RECOMP_FIGHTER_RESEARCH_SCREENS_SHA256'] = hashlib.sha256(screens.read_bytes()).hexdigest()
    return environment
