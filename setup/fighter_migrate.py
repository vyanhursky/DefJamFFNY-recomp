"""One-time move of v1.2.0-beta.1/beta.2 fighter-era saves back into save/.

Those betas played every launch after "adoption" from a private copy and
published each verified save as a generation in mod-manager/fighter-profiles;
save/ was never written again. From beta 3 the game saves straight into
save/ and keeps custom unlocks in its own sidecar. On the first prepare of
the new build:

1. copy the stale save/UserData to save-backup-<date>/ beside save/;
2. write the head generation's files into save/UserData/45410049, replacing
   the stale profiles (the store is the newer career);
3. write the sidecar fighter-state/unlocks.ini from that generation's marks,
   keyed by pack/fighter name;
4. leave the store untouched (read-only) and record the move, with a notice
   the launcher shows once.

A data folder that never adopted a store has nothing to move.
"""
import datetime as dt
import json
import re
from pathlib import Path
import shutil

from mods import atomic_bytes, check, ordinary_path, read_json

TITLE = 'UserData/45410049'
MARKER = 'migrated.json'
NOTICE = 'notice.txt'


def sidecar_text(marks):
    """The unlock sidecar format the game reads and writes (fighter_runtime.c)."""
    lines = ['# Custom fighter unlocks. Written by the game; keys are pack/fighter names.',
             '# 1 = the unlock carries the game\'s extra flag bit. Unknown names are kept.',
             '[fighter-unlocks]', 'schema=1']
    for key, metadata in sorted(marks.items()):
        check('=' not in key and '\n' not in key and key.count('/') == 1, 'Invalid fighter unlock name')
        lines.append(f'{key}={1 if metadata else 0}')
    return ('\n'.join(lines) + '\n').encode('ascii')


def pending(data):
    data = Path(data)
    return (data / 'mod-manager/fighter-profiles/head.json').is_file() and not (data / 'fighter-state' / MARKER).is_file()


def _profile_label(folder):
    """The name the game shows for a profile folder, or the folder's id."""
    try:
        match = re.search(r'Name=([^\r\n]*)', (folder / 'SaveMeta.xbx').read_bytes().decode('utf-16'))
        if match and match[1].strip():
            return match[1].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return folder.name


def _replace_title(save, files):
    """Write the generation's title folder beside the old one, then swap.

    Returns the profiles that existed only in the old folder (for example made on
    v1.1.1 after adoption). They are not carried over: the store is the newer
    career. They stay in the backup copy, and the notice names them."""
    title = ordinary_path(save / TITLE)
    fresh = ordinary_path(title.parent / (title.name + '.migrating'))
    old = ordinary_path(title.parent / (title.name + '.replaced'))
    for leftover in (fresh, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    fresh.mkdir(parents=True)
    for name, data in files.items():
        parts = Path(name).parts
        check(len(parts) == 4 and '/'.join(parts[:2]) == TITLE, 'Fighter generation file outside the title folder')
        path = fresh.joinpath(*parts[2:])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    # Title-level files (TitleMeta.xbx, TitleImage.xbx) are not profiles and
    # were never in the store: keep them.
    dropped = []
    if title.is_dir():
        for item in sorted(title.iterdir()):
            if item.is_file() and not (fresh / item.name).exists():
                shutil.copy2(item, fresh / item.name)
            elif item.is_dir() and not (fresh / item.name).exists():
                dropped.append(_profile_label(item))
    if title.exists():
        title.rename(old)
    fresh.rename(title)
    if old.exists():
        shutil.rmtree(old)
    return dropped


def migrate(manager, *, now=None):
    """Return the backup folder when saves were moved, else None."""
    data = manager.data
    if not pending(data):
        return None
    from fighter_build import retail_catalog
    from fighter_bindings import seed
    from fighter_profile_store import Store, verify_container
    import fighter_unlocks as unlocks
    state_dir = ordinary_path(data / 'fighter-state')
    state_dir.mkdir(exist_ok=True)
    catalog = retail_catalog(manager.game / 'assets/djv2.sod')
    store = Store(ordinary_path(data / 'mod-manager/fighter-profiles'), seed(catalog.db, catalog.source_sha256, catalog.rows))
    generation = store.load()
    stamp = (now or dt.datetime.now()).strftime('%Y%m%d-%H%M%S')
    save = ordinary_path(data / 'save')
    backup = None
    if generation is not None:
        manager.progress('Moving your fighter-era saves back into the save folder')
        if (save / 'UserData').is_dir():
            backup = ordinary_path(data / f'save-backup-{stamp}')
            check(not backup.exists(), 'Save backup folder already exists; try again in a second')
            shutil.copytree(save / 'UserData', backup / 'UserData')
        dropped = _replace_title(save, generation['files'])
        marks = unlocks.restore(verify_container(generation['files'][generation['options']]),
                                generation['extension'], generation['ledger'], store.baseline)
        custom = {key: value for key, value in marks.items() if not key.startswith('retail/')}
        atomic_bytes(state_dir / 'unlocks.ini', sidecar_text(custom))
        text = ('Your fighter-mod saves were moved back into the normal save folder. '
                'The old save folder was copied to ' + str(backup) + '.' if backup else
                'Your fighter-mod saves were moved back into the normal save folder.')
        if dropped:
            text += (' These profiles were only in the old save folder and were not carried over; they are in the '
                     'backup copy: ' + ', '.join(dropped) + '.')
        atomic_bytes(state_dir / NOTICE, (text + '\n').encode('utf-8'))
    atomic_bytes(state_dir / MARKER, json.dumps({
        'schema': 1, 'generation': generation['generation'] if generation else None,
        'backup': str(backup) if backup else None, 'date': stamp}, indent=1).encode('utf-8'))
    return backup
