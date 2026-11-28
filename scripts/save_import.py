"""One save-import service for launcher Help and both legacy command-line tools.

Preview does not change saves. Import revalidates the preview, holds the game's
runtime lock, stages complete profile folders, and retains replacements in a
unique backup. Only standard-library modules are required in the shipped app.
"""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import zipfile
import zlib

import xbox_save_format as xbox
import ps2_save_format as ps2
import ps2_save_containers as containers
from ps2_save_containers import require, MAX_FILE, MAX_FILES, MAX_TOTAL


@dataclass
class Candidate:
    name: str
    platform: str
    raw: bytes
    data: bytes
    files: dict = field(default_factory=dict)
    title_files: dict = field(default_factory=dict)


@dataclass
class Plan:
    save: Path
    rows: list
    writes: list
    token: str



def linked(path):
    """A symbolic link, or on Windows a junction: both lead outside the folder the player chose."""
    path = Path(path)
    return path.is_symlink() or path.is_junction()

def safe_name(name):
    require(xbox.NAME_RE.fullmatch(name) and not any(c in name for c in '/\\:"<>|?*') and
            not name.endswith(('.', ' ')) and name not in ('.', '..') and
            name.split('.')[0].upper() not in {'CON', 'PRN', 'AUX', 'NUL',
                                              *(f'COM{i}' for i in range(1, 10)),
                                              *(f'LPT{i}' for i in range(1, 10))},
            'unsupported profile name')


def source_files(paths):
    """Bounded archive/folder reader. No extraction; paths retain sibling grouping."""
    total = count = 0

    def visit(data, label, member, origin, depth=0):
        nonlocal total, count
        total += len(data)
        count += 1
        require(total <= MAX_TOTAL and count <= MAX_FILES, 'input batch exceeds size/member limit')
        if data.startswith(b'PK\x03\x04'):
            require(depth < 2, 'nested ZIP limit exceeded')
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                require(len(archive.infolist()) <= MAX_FILES, 'too many ZIP members')
                for entry in archive.infolist():
                    if entry.is_dir():
                        continue
                    parts = entry.filename.replace('\\', '/').split('/')
                    # Ignore unsafe entries, matching the original Xbox reader. They
                    # are never extracted or used to form an on-disk target.
                    if entry.filename.startswith(('/', '\\')) or any(p in ('.', '..') or ':' in p for p in parts):
                        continue
                    require(not entry.flag_bits & 1 and entry.file_size <= MAX_FILE,
                            'encrypted/oversized ZIP member')
                    require((entry.external_attr >> 16) & 0o170000 != 0o120000, 'linked ZIP member')
                    yield from visit(archive.read(entry), label + ':' + entry.filename,
                                     member + '/' + '/'.join(parts), origin, depth + 1)
            return
        suffix = Path(member).suffix.lower()
        if data.startswith((b'Ps2PowerSave', b'CFU\0', b'\x0d\0\0\0SharkPortSave', b'\0VSP')) or suffix in {'.psu', '.max', '.cbs', '.sps', '.xps', '.psv'}:
            for inner, raw in containers.unpack(data):
                total += len(raw)
                count += 1
                require(total <= MAX_TOTAL and count <= MAX_FILES, 'expanded input batch exceeds size/member limit')
                if raw.startswith(b'20CM'):
                    yield label, member + '/' + inner, raw, origin
        elif data.startswith(b'Sony PS2 Memory Card Format') or suffix in {'.ps2', '.p2s'}:
            raise ValueError('Export the FFNY save from the PCSX2 card as .psu with mymc; whole cards and save states cannot be imported')
        else:
            yield label, member, data, origin

    for item in paths:
        source = Path(item)
        require(not linked(source), 'source must not be a symbolic link')
        require(source.exists(), 'source does not exist: %s' % source)
        files = source.rglob('*') if source.is_dir() else [source]
        seen = 0
        for file in files:
            seen += 1
            require(seen <= MAX_FILES, 'source folder has too many entries; select just the FFNY saves')
            require(not linked(file), 'linked source paths are not supported')
            if file.is_dir():
                continue
            with file.open('rb') as stream:
                data = stream.read(MAX_FILE + 1)
            require(len(data) <= MAX_FILE, 'source exceeds 4 MiB; export individual saves from the memory card')
            yield from visit(data, str(file), str(file), file.resolve())


def read_candidates(paths, key=xbox.PORT_KEY):
    files = list(source_files(paths))
    groups, found = {}, {}
    for label, member, raw, origin in files:
        siblings = groups.setdefault(str(Path(member).parent), {})
        filename = Path(member).name
        require(filename not in siblings or siblings[filename] == raw, 'conflicting duplicate archive member')
        siblings[filename] = raw
    title_files = {}
    for group, entries in groups.items():
        if Path(group).name.upper() == xbox.TITLE_ID:
            for name, raw in entries.items():
                if name.lower() in ('titlemeta.xbx', 'titleimage.xbx'):
                    canonical = 'TitleMeta.xbx' if name.lower() == 'titlemeta.xbx' else 'TitleImage.xbx'
                    require(canonical not in title_files or title_files[canonical] == raw, 'conflicting Xbox title metadata')
                    title_files[canonical] = raw
    def add(candidate):
        safe_name(candidate.name)
        prior = found.get(candidate.name.casefold())
        require(prior is None or (prior.name == candidate.name and prior.raw == candidate.raw),
                'conflicting saves for %s; import one at a time' % candidate.name)
        if prior is None:
            found[candidate.name.casefold()] = candidate

    for label, member, raw, origin in files:
        if not raw.startswith(b'20CM'):
            continue
        require(len(raw) >= 16, 'truncated FFNY save header')
        payload_size = struct.unpack_from('<I', raw, 12)[0]
        if len(raw) == ps2.IDENTITY_END + payload_size:
            name, payload = ps2.parse_profile(raw)
            data = payload if name == 'Options' else ps2.convert_story(payload)
            ps2.check_unlock_lists(payload if name == 'Options' else data[xbox.IDENTITY_END:], name == 'Options')
            add(Candidate(name, 'PS2', raw, data))
        else:
            require(xbox.header_fault(raw) is None, 'damaged Xbox profile: %s' % xbox.header_fault(raw))
            siblings = groups[str(Path(member).parent)]
            lower = {n.lower(): n for n in siblings}
            require('savemeta.xbx' in lower, 'Xbox saves need SaveMeta.xbx beside the profile; select its folder or ZIP')
            meta = siblings[lower['savemeta.xbx']]
            name = xbox.parse_save_meta(meta)
            require(name is not None, 'Xbox SaveMeta.xbx has no usable profile name')
            if name != Path(member).name:
                continue  # Xbox folders may retain an older, unreferenced profile file
            identity = raw[xbox.HEADER:xbox.IDENTITY_END]
            require(identity.startswith(b'DJFFNY::Global 17 ' if name == 'Options' else b'DJFFNY::User 17 '),
                    'unsupported Xbox save identity')
            if identity.split(b'\0', 1)[0] == ('DJFFNY::%s 17 %d' % ('Global' if name == 'Options' else 'User', ps2.XBOX_BUILD)).encode():
                require(payload_size == (ps2.XBOX_OPTIONS if name == 'Options' else ps2.XBOX_PROFILE), 'unsupported Xbox save layout')
                ps2.check_unlock_lists(raw[xbox.IDENTITY_END:], name == 'Options')
            extra = {'SaveMeta.xbx': meta}
            if 'saveimage.xbx' in lower:
                extra['saveimage.xbx'] = siblings[lower['saveimage.xbx']]
            add(Candidate(name, 'Xbox', raw, xbox.resign(raw, key), extra, title_files))
    require(found, 'no FFNY profiles found; choose a save export, FFNY save folder or ZIP')
    return sorted(found.values(), key=lambda c: c.name.casefold()), {origin for _, _, _, origin in files}


def ordinary(path):
    require(not linked(path), 'save target contains a symbolic link')


def target_for(title, name):
    canonical = xbox.folder_name(name)
    value = int(canonical, 16)
    legacy = canonical[:-1] + '%X' % ((value | (value >> 32)) & 15)
    matches = [p for p in title.glob('*') if p.name.upper() in {canonical, legacy}]
    require(len(matches) <= 1, 'ambiguous native profile folders for %s' % name)
    target = matches[0] if matches else title / canonical
    ordinary(target)
    require(not target.exists() or target.is_dir(), 'profile target is not a folder')
    return target


def tree_digest(target):
    digest = hashlib.sha256()
    if not target.exists():
        return 'absent'
    total = 0
    for i, p in enumerate(sorted(target.rglob('*'))):
        ordinary(p)
        require(i < MAX_FILES, 'native profile folder has too many entries')
        digest.update(str(p.relative_to(target)).encode('utf-8'))
        if p.is_file():
            require(p.stat().st_size <= MAX_FILE, 'native profile file is too large')
            raw = p.read_bytes()
            total += len(raw)
            require(total <= MAX_TOTAL, 'native profile folder is too large')
            digest.update(hashlib.sha256(raw).digest())
    return digest.hexdigest()


def make_plan(sources, save_dir, include_options=False, force=False, key=xbox.PORT_KEY):
    candidates, origins = read_candidates(sources, key)
    ordinary(save_dir)
    save = save_dir.resolve()
    title = save / 'UserData' / xbox.TITLE_ID
    for p in (save / 'UserData', title):
        ordinary(p)
    rows, writes = [], []
    targets = set()
    digest = hashlib.sha256(str((str(save), include_options, force, key.hex())).encode())
    for candidate in candidates:
        name = candidate.name
        target = target_for(title, name)
        require(str(target).casefold() not in targets, 'profile folder hash collision; import these sources separately')
        targets.add(str(target).casefold())
        require(all(target not in p.parents and target != p for p in origins),
                'source is inside the profile being replaced; select a copy outside the save area')
        digest.update(candidate.raw)
        for filename, raw in sorted({**candidate.files, **candidate.title_files}.items()):
            digest.update(filename.encode())
            digest.update(hashlib.sha256(raw).digest())
        digest.update(str(target).encode('utf-8'))
        digest.update(tree_digest(target).encode())
        action = 'Replace (backup first)' if target.exists() and force else 'Import'
        if name == 'Options' and not include_options:
            action = 'Skip shared unlocks'
        elif target.exists() and not force:
            action = 'Keep existing'
        else:
            data = candidate.data
            if name == 'Options':
                require((target / 'Options').is_file(), 'Shared unlocks need a native Options save; start the game once first')
                native = (target / 'Options').read_bytes()
                payload = candidate.data if candidate.platform == 'PS2' else candidate.data[xbox.IDENTITY_END:]
                # Same shared unlock block on Xbox and PS2; keep native preferences.
                data = ps2.merge_unlocks(payload, native)
            writes.append((candidate, target, data))
        rows.append((name, candidate.platform, action))
        digest.update(action.encode())
    return Plan(save, rows, writes, digest.hexdigest())


@contextmanager
def runtime_lock(save):
    """Same cross-process lock as pc_mods_game_lock; never race a playing game."""
    root = save.parent / 'mod-manager'
    ordinary(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'runtime.lock'
    ordinary(path)
    with path.open('a+b') as stream:
        try:
            if os.name == 'nt':
                import ctypes
                import msvcrt
                from ctypes import wintypes
                class Overlapped(ctypes.Structure):
                    _fields_ = [('internal', ctypes.c_size_t), ('internal_high', ctypes.c_size_t),
                                ('offset', wintypes.DWORD), ('offset_high', wintypes.DWORD), ('event', wintypes.HANDLE)]
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.LockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                                             wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(Overlapped)]
                kernel.LockFileEx.restype = wintypes.BOOL
                handle = msvcrt.get_osfhandle(stream.fileno())
                overlapped = Overlapped()
                require(kernel.LockFileEx(handle, 3, 0, 1, 0, ctypes.byref(overlapped)),
                        'Close the game and wait for other save or mod operations before importing')
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('Close the game and wait for other save or mod operations before importing') from error
        yield  # closing the file releases the OS lock, including on process exit


def apply_plan(plan):
    """Stage the batch first. A failed publish restores every replaced profile."""
    title = plan.save / 'UserData' / xbox.TITLE_ID
    title.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.save-import-', dir=title))
    backup = None
    published = []
    title_published = []
    moved = []
    try:
        for index, (candidate, target, data) in enumerate(plan.writes):
            staged = staging / str(index)
            if candidate.name == 'Options':
                shutil.copytree(target, staged)
            else:
                staged.mkdir()
            if candidate.name != 'Options':
                for filename, raw in candidate.files.items():
                    (staged / filename).write_bytes(raw)
            (staged / candidate.name).write_bytes(data)
            if not (staged / 'SaveMeta.xbx').exists():
                (staged / 'SaveMeta.xbx').write_bytes(b'\xff\xfe' + ('Name=%s\r\n' % candidate.name).encode('utf-16le'))
        for index, (_, target, _) in enumerate(plan.writes):
            if target.exists():
                if backup is None:
                    backup = Path(tempfile.mkdtemp(prefix='import-backup-', dir=plan.save))
                saved = backup / target.name
                shutil.move(str(target), str(saved))
                moved.append((saved, target))
            os.replace(staging / str(index), target)
            published.append(target)
        for candidate, _, _ in plan.writes:
            for filename, raw in candidate.title_files.items():
                dest = title / filename
                ordinary(dest)
                if not dest.exists():
                    pending = staging / filename
                    pending.write_bytes(raw)
                    os.replace(pending, dest)
                    title_published.append(dest)
    except BaseException:
        for dest in title_published:
            dest.unlink()
        for target in reversed(published):
            shutil.rmtree(target)
        for saved, target in reversed(moved):
            shutil.move(str(saved), str(target))
        raise
    finally:
        shutil.rmtree(staging)
    return backup


def write_report(path, status, message, plan=None):
    """Small UTF-8 INI projection for the native launcher, never any save bytes."""
    def line(value):
        return str(value).replace('\r', ' ').replace('\n', ' ')
    text = '[import]\nstatus=%s\nmessage=%s\n' % (status, line(message))
    if plan:
        text += 'token=%s\ncount=%d\n' % (plan.token, len(plan.writes))
        for i, (name, platform, action) in enumerate(plan.rows):
            text += '[profile.%d]\nname=%s\nplatform=%s\naction=%s\n' % (i, line(name), platform, action)
    # Caller supplies a fresh private job directory, not a save/profile path.
    path = Path(path)
    ordinary(path)
    temporary = path.with_suffix('.tmp')
    ordinary(temporary)
    temporary.write_text(text, encoding='utf-8')
    os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Import Xbox or PS2 FFNY saves. Easier: launcher Help > Import saves.')
    parser.add_argument('source', nargs='+', help='Xbox/PS2 save exports, folders or ZIPs')
    parser.add_argument('--save-dir', help='save area containing UserData')
    parser.add_argument('--install', help='installation folder with installed.json')
    parser.add_argument('--check', action='store_true', help='validate sources; write nothing')
    parser.add_argument('--dry-run', action='store_true', help='preview import; write no saves')
    parser.add_argument('--force', action='store_true', help='back up and replace existing profiles')
    parser.add_argument('--include-options', action='store_true', help='transfer shared unlocks into native Options (keeps preferences)')
    parser.add_argument('--key', help='advanced: 32 hexadecimal digits for the Xbox signing key')
    parser.add_argument('--report', help=argparse.SUPPRESS)
    parser.add_argument('--expect', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.key and not re.fullmatch(r'[0-9a-fA-F]{32}', args.key):
        parser.error('--key must be 32 hex digits')
    try:
        require(not args.key or re.fullmatch(r'[0-9a-fA-F]{32}', args.key), '--key must be 32 hex digits')
        key = bytes.fromhex(args.key) if args.key else xbox.PORT_KEY
        if args.check:
            candidates, _ = read_candidates(args.source, key)
            for c in candidates:
                print('found  %s (%s)' % (c.name, c.platform))
            return 0
        save = xbox.resolve_save_dir(args)
        require(save is not None, 'pass --save-dir "<data folder>/save"')
        def preview():
            plan = make_plan(args.source, save, args.include_options, args.force, key)
            require(not args.expect or plan.token == args.expect, 'The source or destination changed. Check saves again before importing.')
            return plan
        backup = None
        if args.dry_run:
            plan = preview()
        else:
            with runtime_lock(save):
                plan = preview()
                if plan.writes:
                    backup = apply_plan(plan)
        for name, platform, action in plan.rows:
            print('%s: %s (%s)' % (action, name, platform))
        message = ('Ready to import %d profile(s).' if args.dry_run else 'Imported %d profile(s). Choose the imported ID when you start Story.') % len(plan.writes)
        if not plan.writes:
            message = 'Nothing selected for import. Review the preview and the import options.'
        if backup:
            message += ' Backup: %s' % backup
        print(message)
        if args.report:
            write_report(args.report, 'preview' if args.dry_run else 'done', message, plan)
        return 0 if plan.writes or args.report else 1
    except (OSError, ValueError, UnicodeError, struct.error, zipfile.BadZipFile, zlib.error,
            StopIteration, IndexError, ArithmeticError) as error:
        message = str(error)
        print('error: %s' % message, file=sys.stderr)
        if args.report:
            write_report(args.report, 'error', message)
        return 2
