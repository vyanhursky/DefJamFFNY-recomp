"""The one file the game reads to load enabled fighter packs.

Packs are compiled when they are enabled (and when an installed pack or the
language changes), not on every launch. The result is written here once:

    mod-manager/fighter-manifest.ini
        [manifest]     schema, runtime version, language pack, sidecar folder
        [environment]  the runtime settings the native fighter modules read
        [inputs]       size and modification time of every file the build read
                       or produced, so the game can tell a stale manifest
                       without hashing gigabytes or starting Python
    mod-manager/fighter-identities.txt
        stable handle -> pack/fighter name for custom fighters, so the game
        can key its unlock sidecar by name instead of by number

The game trusts the bytes behind a manifest whose stamps still match (they
were verified when the cache was written); a mismatch makes the launcher run
``mods.py fighter-prepare`` again before Play. With no pack enabled there is
no manifest and the game's fighter code stays inert.
"""
from pathlib import Path

from mods import atomic_bytes, check, ordinary_path

SCHEMA = 1
MANIFEST = 'fighter-manifest.ini'
IDENTITIES = 'fighter-identities.txt'
STATE_DIR = 'fighter-state'
MAX_INPUTS = 200000


def _line(value):
    value = str(value)
    check('\n' not in value and '\r' not in value and len(value.encode('utf-8')) < 4000, 'Invalid fighter manifest value')
    return value


def stamp(path):
    info = Path(path).stat()
    return info.st_size, info.st_mtime_ns


def _files(folder):
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.rglob('*') if path.is_file())


def inputs(manager, ids, language, environment, ui_pack):
    """Every file whose change must make the game ask for a rebuild."""
    from fighter_cache import ORIGINALS
    paths = [manager.game / name for name in ORIGINALS if (manager.game / name).is_file()]
    for identifier in ids:
        paths += _files(manager.mods / identifier)
    if language:
        paths += _files(language)
    for key, value in environment.items():
        if key.startswith('RECOMP_FIGHTER_') and value and not key.endswith('_SHA256'):
            candidate = Path(value)
            if candidate.is_absolute() and candidate.is_file():
                paths.append(candidate)
    if ui_pack is not None:
        paths += _files(ui_pack)
    unique = sorted({str(path): path for path in paths}.items())
    check(len(unique) <= MAX_INPUTS, 'Fighter manifest input budget exceeded')
    return [(name, *stamp(path)) for name, path in unique]


def identities(ledger):
    rows = []
    for identifier, entry in sorted(ledger['fighters'].items()):
        if identifier.startswith('retail/'):
            continue
        rows.append(f"{entry['handle']:08X} {identifier}")
    return ('\n'.join(['# stable-handle pack/fighter; written by mods.py, read by the game'] + rows) + '\n').encode('ascii')


def paths(manager):
    return ordinary_path(manager.root / MANIFEST), ordinary_path(manager.root / IDENTITIES)


def remove(manager):
    for path in paths(manager):
        if path.exists():
            path.unlink()


def write(manager, state, *, language=None, built=None):
    """Compile (or reuse) the enabled packs and publish the manifest for Play."""
    from fighter_packages import build, enabled, runtime_environment
    from fighter_ui_hd import stage as stage_ui_hd
    ids = enabled(state)
    manifest, identity_path = paths(manager)
    if not ids:
        remove(manager)
        return None
    cache, report, screens, composed = built or build(manager, state, language=language)
    ui_pack = stage_ui_hd(cache, report, manager.mods)
    environment = runtime_environment(cache, report, screens, composed, **({'ui_pack': ui_pack} if ui_pack else {}))
    sidecar = ordinary_path(manager.data / STATE_DIR)
    environment['RECOMP_FIGHTER_IDENTITIES'] = str(identity_path)
    environment['RECOMP_FIGHTER_STATE'] = str(sidecar)
    atomic_bytes(identity_path, identities(report['binding_ledger']))
    lines = ['[manifest]', f'schema={SCHEMA}', 'runtime=' + _line(manager.runtime),
             'language=' + _line(language or ''), 'packs=' + _line(','.join(ids)), '[environment]']
    for key, value in sorted(environment.items()):
        check(key.startswith('RECOMP_FIGHTER_'), 'Fighter manifest may only carry fighter settings')
        lines.append(key + '=' + _line(value))
    lines.append('[inputs]')
    for index, (name, size, mtime) in enumerate(inputs(manager, ids, language, environment, ui_pack)):
        # The path goes last so it may contain any character but a line break.
        lines.append(f'{index}={size}|{mtime}|' + _line(name))
    # The manifest is published last: an interrupted write leaves the old one,
    # whose stamps no longer match, so the game asks for a rebuild.
    atomic_bytes(manifest, ('\n'.join(lines) + '\n').encode('utf-8'))
    return manifest
