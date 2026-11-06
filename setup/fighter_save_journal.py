"""Verify completed native save batches before publishing isolated generations.

FSB1 is runtime-owned intent, not evidence that a write succeeded. FSA1 receipts
require successful full synchronous writes and native close. Every named native
file, identity block, payload and signature must match that attempt. Only that exact
batch is merged over the previous generation; unrelated working files cannot
leak into a committed save. Used by the disposable research supervisor for now.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import struct
import threading
import time

from fighter_bindings import allocate
from fighter_profile_store import MAX_FILE, relative, require, verify_container
from fighter_registry import fingerprint
import fighter_unlocks as unlocks
from mods import atomic_bytes, atomic_json, linked, sync_directory

MAX_BATCH = 24 + 16 * (104 + 0x5904) + 16384 * 8


def decode(data):
    if isinstance(data, bytes) and data[:4] == b'FSD1':
        require(len(data) == 52, 'Invalid native profile deletion receipt')
        version, number, length, reserved = struct.unpack_from('<4I', data, 4)
        require(version == 1 and 1 <= number <= 10000 and 1 <= length <= 32 and not reserved,
                'Invalid native profile deletion header')
        raw = data[20:]
        require(all(32 <= c <= 126 for c in raw[:length]) and not any(raw[length:]), 'Invalid deleted profile name')
        name = raw[:length].decode('ascii')
        relative('UserData/45410049/000000000000/' + name)
        require(name.casefold() not in ('options', 'savemeta.xbx', 'saveimage.xbx'), 'Cannot delete native Options or metadata as a profile')
        return {'number': number, 'deleted': name, 'records': [], 'marks': {}}
    require(isinstance(data, bytes) and 24 <= len(data) <= MAX_BATCH and data[:4] == b'FSB1', 'Invalid fighter save batch')
    version, number, count, total, reserved = struct.unpack_from('<5I', data, 4)
    require(version == 1 and 1 <= number <= 10000 and 1 <= count <= 16 and total <= 16384 and not reserved,
            'Invalid fighter save batch header')
    offset, records, names = 24, [], set()
    for _ in range(count):
        require(offset + 104 <= len(data), 'Truncated fighter save record')
        length, size = struct.unpack_from('<II', data, offset)
        require(1 <= length <= 32 and size in (0x1490, 0x5904) and offset + 104 + size <= len(data), 'Invalid fighter save record lengths')
        raw = data[offset + 72:offset + 104]
        require(all(32 <= c <= 126 for c in raw[:length]) and not any(raw[length:]), 'Invalid native save name')
        name = raw[:length].decode('ascii')
        relative('UserData/45410049/000000000000/' + name)
        require(name.casefold() not in names and (name == 'Options') == (size == 0x1490), 'Ambiguous native save record')
        names.add(name.casefold())
        records.append({'name': name, 'identity': data[offset + 8:offset + 72], 'payload': data[offset + 104:offset + 104 + size]})
        offset += 104 + size
    require(len(data) == offset + total * 8, 'Fighter save batch has trailing or missing marks')
    marks = dict(struct.iter_unpack('<II', data[offset:]))
    require(len(marks) == total and all(value in (0, unlocks.METADATA) for value in marks.values()), 'Invalid fighter save marks')
    return {'number': number, 'records': records, 'marks': marks}


def bounded(path):
    require(not linked(path) and path.is_file() and path.stat().st_size <= MAX_FILE, 'Unsafe native save file')
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE + 1)
    require(len(data) <= MAX_FILE, 'Native save grew beyond budget')
    return data


def closed_record(journal, batch, index, record):
    root = Path(journal)
    require(not any(linked(path) for path in (root, *root.parents)), 'Redirected native save receipt directory')
    path = root / f'{batch:06}-{index:02}.closed'
    if not path.exists():
        return None
    data = bounded(path)
    require(20 <= len(data) <= 20 + 0x8c + 0x5904 and data[:4] == b'FSA1', 'Invalid native save receipt')
    require(struct.unpack_from('<4I', data, 4) == (1, batch, index, len(data) - 20), 'Crossed native save receipt')
    native = data[20:]
    require(verify_container(native) == record['payload'] and native[0x4c:0x8c] == record['identity'],
            'Native save receipt differs from its staged record')
    return native


def completed_records(batch, save, journal):
    root = Path(save)
    require(not any(linked(path) for path in (root, *root.parents)), 'Redirected native save workspace')
    title = root / 'UserData' / '45410049'
    require(not linked(root / 'UserData') and not linked(title), 'Redirected native save namespace')
    if not title.is_dir():
        return None
    folders = list(title.iterdir())
    require(len(folders) <= 1024, 'Native save folder count exceeds budget')
    updates = {}
    for index, record in enumerate(batch['records']):
        receipt = closed_record(journal, batch['number'], index, record)
        if receipt is None:
            return None
        matches = []
        for folder in folders:
            if not re.fullmatch('[0-9A-F]{12}', folder.name):
                continue
            require(not linked(folder), 'Redirected native profile folder')
            path = folder / record['name']
            if not path.exists():
                continue
            try:
                data = bounded(path)
                if data != receipt or verify_container(data) != record['payload'] or data[0x4c:0x8c] != record['identity']:
                    continue
                metadata = bounded(folder / 'SaveMeta.xbx')
                text = metadata.decode('utf-16')
                if re.match(r'Name=([^\r\n]*)', text).group(1) != record['name']:
                    continue
                image = bounded(folder / 'saveimage.xbx')
            except (OSError, ValueError, AttributeError, UnicodeError):
                continue  # Incomplete/locked files are never a successful batch.
            prefix = 'UserData/45410049/' + folder.name + '/'
            matches.append({prefix + record['name']: data, prefix + 'SaveMeta.xbx': metadata, prefix + 'saveimage.xbx': image})
        require(len(matches) <= 1, 'Native batch matches multiple profile folders')
        if not matches:
            return None
        updates.update(matches[0])
    return updates


def replace_payload(container, payload):
    verify_container(container)
    require(len(payload) == len(container) - 0x8c, 'Native payload size changed')
    result = bytearray(container[:0x8c] + payload)
    for start, end, at in ((0x4c, 0x8c, 0x10), (0x8c, len(result), 0x24), (0, 0x38, 0x38)):
        result[at:at + 20] = hmac.new(bytes(16), result[start:end], hashlib.sha1).digest()
    return bytes(result)


class Monitor:
    def __init__(self, store, save, journal, ledger, *, expected_head):
        # Pin the generation used to materialize this session, not whatever
        # happens to be current when its first completed batch arrives.
        require(expected_head is None or isinstance(expected_head, str)
                and re.fullmatch('[0-9a-f]{64}', expected_head), 'Invalid session save generation')
        self.store, self.save, self.journal, self.ledger = store, Path(save), Path(journal), ledger
        self.expected_head = expected_head
        require(not any(linked(path) for path in (self.journal, *self.journal.parents))
                and self.journal.is_dir(), 'Unsafe fighter save session directory')
        require(next(self.journal.iterdir(), None) is None,
                'Fighter save journal was already used; recover the committed profile into a fresh session')
        # Never resume numbered intents in an old working directory. A crash
        # restarts from Store.load() in a fresh session, preserving the old
        # journal for diagnosis rather than replaying stale native progress.
        session = {'schema': 'fighter-save-session-1', 'parent': expected_head,
                   'ledger_sha256': fingerprint(ledger)}
        with (self.journal / 'session.json').open('x', encoding='utf-8') as stream:
            json.dump(session, stream, sort_keys=True)
            stream.flush(); os.fsync(stream.fileno())
        sync_directory(self.journal)
        self.stop_event, self.error, self.committed, self.next = threading.Event(), None, [], 1
        self.thread = threading.Thread(target=self._run, name='fighter-save-verifier', daemon=True)

    def status(self, state, detail=''):
        atomic_json(self.journal / 'supervisor.json', {'schema': 'fighter-save-supervisor-1',
            'state': state, 'heartbeat': time.monotonic(), 'detail': str(detail)[:256]})

    def poll(self):
        path = self.journal / f'{self.next:06}.batch'
        if not path.exists():
            return False
        require(not linked(path) and path.stat().st_size <= MAX_BATCH, 'Unsafe fighter save journal')
        with path.open('rb') as stream:
            batch = decode(stream.read(MAX_BATCH + 1))
        require(batch['number'] == self.next, 'Out-of-order fighter save journal')
        if 'deleted' in batch:
            return self.delete_profile(batch)
        updates = completed_records(batch, self.save, self.journal)
        if updates is None:
            return False
        previous = self.store.load()
        require((previous['generation'] if previous else None) == self.expected_head,
                'Fighter save changed since this session was loaded; reload the latest committed profile')
        old_ledger = previous['ledger'] if previous else self.ledger
        # A caller cannot substitute a ledger that reassigns any old identity.
        checked = allocate(self.store.baseline, (), self.ledger)['fighters']
        require(all(checked.get(key) == value for key, value in old_ledger['fighters'].items()),
                'Fighter journal lost historical identity bindings')
        options = next((name for name in updates if name.endswith('/Options')), previous['options'] if previous else None)
        require(options is not None, 'The first fighter save batch must include native Options')
        data = updates[options] if options in updates else previous['files'][options]
        marks = unlocks.restore(verify_container(previous['files'][previous['options']]), previous['extension'], old_ledger, self.store.baseline) if previous else {}
        # Retail unlock changes belong to the freshly saved native Options;
        # absent custom content stays dormant in the prior extension.
        marks = {key: value for key, value in marks.items() if not key.startswith('retail/')}
        marks.update(unlocks.read(verify_container(data), self.ledger, self.store.baseline))
        known = {entry['handle']: key for key, entry in self.ledger['fighters'].items()}
        for handle, metadata in batch['marks'].items():
            require(handle in known and not known[handle].startswith('retail/'), 'Journal contains an unknown custom fighter identity')
            marks[known[handle]] = metadata
        projected, extension = unlocks.project(verify_container(data), marks, self.ledger, self.store.baseline)
        require(projected == verify_container(data), 'Native batch did not use the canonical retail-only projection')
        generation = self.store.commit_batch(self.expected_head, updates, self.ledger, extension, options)
        self.acknowledge(generation)
        return True

    def acknowledge(self, generation):
        # The native side may only start another operation after publication.
        # Losing this acknowledgement on a crash is safe: recovery uses head,
        # never the old session's working directory or journal.
        atomic_bytes(self.journal / f'{self.next:06}.committed', b'FSC1' + struct.pack('<I', self.next))
        self.expected_head = generation
        self.committed.append((self.next, generation))
        self.next += 1

    def delete_profile(self, batch):
        """A native completion witness AND absent exact folder are required.

        This removes a Battle ID/Story profile, not the global Options unlocks.
        Historical fighter identities and dormant custom progression survive.
        """
        previous = self.store.load()
        require(previous is not None and previous['generation'] == self.expected_head,
                'Fighter save changed since this session was loaded; reload the latest committed profile')
        require(previous['ledger'] == self.ledger, 'Deletion requires the session identity ledger')
        matches = [name for name in previous['files'] if name.rsplit('/', 1)[-1] == batch['deleted']]
        require(len(matches) == 1, 'Deleted native profile has no unique committed identity')
        profile = matches[0]
        require(len(verify_container(previous['files'][profile])) == 0x5904,
                'Deletion does not identify a native profile')
        prefix = profile.rsplit('/', 1)[0] + '/'
        removed = {name for name in previous['files'] if name.startswith(prefix)}
        require(removed <= {profile, prefix + 'SaveMeta.xbx', prefix + 'saveimage.xbx'},
                'Deleted profile folder contains unrelated committed records')
        title = self.save / 'UserData/45410049'
        require(not any(linked(path) for path in (title, *title.parents)) and title.is_dir(),
                'Deleted profile workspace is absent or redirected')
        folder = self.save / prefix
        require(not linked(folder), 'Deleted profile folder was redirected')
        try:
            folder.lstat()
        except FileNotFoundError:
            pass
        else:
            return False  # Cancelled/partial/failed deletion is not a commit.
        files = {name: data for name, data in previous['files'].items() if name not in removed}
        generation = self.store.publish(self.expected_head, files, self.ledger,
                                        previous['extension'], previous['options'])
        self.acknowledge(generation)
        return True

    def _run(self):
        try:
            heartbeat = time.monotonic()
            while not self.stop_event.is_set():
                if time.monotonic() - heartbeat >= 1:
                    self.status('active'); heartbeat = time.monotonic()
                if not self.poll():
                    self.stop_event.wait(0.1)
        except Exception as error:
            self.error = error
            try:
                self.status('failed', error)
            except (OSError, ValueError):
                pass  # A stale heartbeat still makes the harness stop safely.

    def start(self):
        self.status('active')
        self.thread.start()

    def stop(self):
        self.stop_event.set(); self.thread.join(timeout=10)
        require(not self.thread.is_alive(), 'Fighter save verifier did not stop')
        if self.error:
            raise ValueError('Fighter save verification failed: ' + str(self.error)) from self.error
        self.status('stopped')


def initialize(store, source, ledger):
    """Import verified fixture files once, then migrate append-only identities.

    Research caller supplies a read-only fixture root; this never writes there.
    Original retail progression and opaque native profile bytes are preserved.
    """
    previous = store.load()
    if previous is None:
        title = Path(source) / 'UserData/45410049'
        require(title.is_dir() and not linked(title), 'A verified Options fixture is required for fighter profile research')
        files = {}
        folders = list(title.iterdir())
        require(len(folders) <= 1024, 'Native import exceeds folder budget')
        for folder in folders:
            require(not linked(folder), 'Redirected native import folder')
            if not re.fullmatch('[0-9A-F]{12}', folder.name) or not folder.is_dir():
                continue
            metadata = bounded(folder / 'SaveMeta.xbx')
            match = re.match(r'Name=([^\r\n]*)', metadata.decode('utf-16'))
            require(match is not None, 'Native import has no profile name')
            name = match[1]
            relative('UserData/45410049/' + folder.name + '/' + name)
            data = bounded(folder / name)
            verify_container(data)
            prefix = 'UserData/45410049/' + folder.name + '/'
            files.update({prefix + name: data, prefix + 'SaveMeta.xbx': metadata,
                          prefix + 'saveimage.xbx': bounded(folder / 'saveimage.xbx')})
        options = [name for name in files if name.endswith('/Options')]
        require(len(options) == 1, 'Fighter profile import needs exactly one Options record')
        options = options[0]
        marks = unlocks.read(verify_container(files[options]), ledger, store.baseline)
        native, extension = unlocks.project(verify_container(files[options]), marks, ledger, store.baseline)
        files[options] = replace_payload(files[options], native)
        store.publish(None, files, ledger, extension, options)
        previous = store.load()
    checked = allocate(store.baseline, (), ledger)['fighters']
    require(all(checked.get(key) == value for key, value in previous['ledger']['fighters'].items()), 'Fighter profile migration reassigned historical identity')
    if previous['ledger'] != ledger:
        options = previous['options']
        marks = unlocks.restore(verify_container(previous['files'][options]), previous['extension'], previous['ledger'], store.baseline)
        native, extension = unlocks.project(verify_container(previous['files'][options]), marks, ledger, store.baseline)
        store.commit_batch(previous['generation'], {options: replace_payload(previous['files'][options], native)}, ledger, extension, options)
        previous = store.load()
    return previous


def encode_unlock_state(generation, baseline):
    if generation is None:
        return b'FUM1' + struct.pack('<III', 1, 0, 0)
    ledger = generation['ledger']
    marks = unlocks.restore(verify_container(generation['files'][generation['options']]), generation['extension'], ledger, baseline)
    values = sorted((ledger['fighters'][key]['handle'], metadata) for key, metadata in marks.items() if not key.startswith('retail/'))
    return b'FUM1' + struct.pack('<III', 1, len(values), 0) + b''.join(struct.pack('<II', *value) for value in values)
