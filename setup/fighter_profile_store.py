"""Read-only access to the v1.2.0-beta.1/beta.2 fighter save store.

Since beta 3 saves stay in save/ and fighter_migrate.py moves a beta store's
head generation back there once. This module stays for that move and is
removed in the release after. Its original description follows.

Coherent, isolated fighter-save generations for guarded research runtime runs.

Native writes must first finish in a disposable working directory. Publication
uses the exact verified batch over the previous committed generation, never a
scan that could accidentally include another half-written save. A generation
contains native files, the historical identity ledger and its matching unlock
extension. The original retail save directory is never an argument to a write.
"""
from contextlib import contextmanager
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
import re
import struct
import tempfile

from fighter_registry import fingerprint
from fighter_unlocks import restore
from mods import atomic_json, durable_rename, file_lock, linked, read_json, sync_directory

SCHEMA = 'fighter-profile-generation-1'
MAX_FILES = 1024
MAX_FILE = 4 * 1024**2
MAX_BYTES = 64 * 1024**2
IDENTITY_END = 0x8c


def require(value, message):
    if not value:
        raise ValueError(message)


def relative(value):
    require(isinstance(value, str) and 0 < len(value) <= 240 and re.fullmatch(r'[ -~]+', value), 'Invalid save path')
    parts = PurePosixPath(value).parts
    require('/'.join(parts) == value and not value.startswith('/') and len(parts) == 4
            and parts[:2] == ('UserData', '45410049') and re.fullmatch('[0-9A-F]{12}', parts[2]), 'Invalid save namespace')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
    require(all(part not in ('.', '..') and not part.endswith(('.', ' '))
                and not any(char in part for char in '\\:*?"<>|') and part.split('.')[0].upper() not in reserved for part in parts),
            'Unsafe native save path')
    require(len(parts[-1]) <= 32, 'Native save filename exceeds budget')
    return parts


def verify_container(data):
    require(isinstance(data, bytes) and IDENTITY_END < len(data) <= MAX_FILE and data[:4] == b'20CM', 'Invalid native save container')
    require(struct.unpack_from('<III', data, 4) == (len(data), 0x40, len(data) - IDENTITY_END), 'Invalid native save lengths')
    for start, end, at in ((0x4c, 0x8c, 0x10), (0x8c, len(data), 0x24), (0, 0x38, 0x38)):
        expected = hmac.new(bytes(16), data[start:end], hashlib.sha1).digest()
        require(hmac.compare_digest(data[at:at + 20], expected), 'Native save signature did not verify')
    require(len(data) - IDENTITY_END in (0x1490, 0x5904), 'Unsupported native save payload')
    return data[IDENTITY_END:]


def validate_files(files):
    require(isinstance(files, dict) and 0 < len(files) <= MAX_FILES, 'Invalid save generation population')
    require(sum(len(data) for data in files.values() if isinstance(data, bytes)) <= MAX_BYTES, 'Save generation exceeds byte budget')
    folded = set()
    for name, data in files.items():
        parts = relative(name)
        require(name.casefold() not in folded, 'Case-colliding save paths')
        folded.add(name.casefold())
        require(isinstance(data, bytes) and 0 < len(data) <= MAX_FILE, 'Invalid save file byte budget')
        if parts[-1] not in ('SaveMeta.xbx', 'saveimage.xbx'):
            verify_container(data)


class Store:
    """One writer, immutable generations, one durable publication pointer."""
    def __init__(self, root, baseline):
        self.root, self.baseline = Path(root), baseline
        require(not any(linked(parent) for parent in (self.root, *self.root.parents)), 'Refusing redirected fighter profile store')
        self.root.mkdir(parents=True, exist_ok=True)
        self.generations = self.root / 'generations'
        require(not linked(self.generations), 'Refusing redirected fighter generations')
        self.generations.mkdir(exist_ok=True)

    @contextmanager
    def lock(self, shared=False):
        require(not linked(self.root) and not linked(self.generations), 'Fighter profile store was redirected')
        with file_lock(self.root / 'store.lock', shared=shared):
            yield

    def _head(self):
        value = read_json(self.root / 'head.json')
        if value is None:
            return None
        require(isinstance(value, dict) and set(value) == {'schema', 'generation'} and value['schema'] == SCHEMA
                and isinstance(value['generation'], str) and re.fullmatch('[0-9a-f]{64}', value['generation']), 'Invalid fighter save head')
        return value['generation']

    def _read(self, generation):
        folder = self.generations / generation
        require(not linked(folder), 'Redirected fighter save generation')
        manifest = read_json(folder / 'manifest.json')
        require(isinstance(manifest, dict) and set(manifest) == {'schema', 'parent', 'files', 'ledger', 'extension', 'options'}
                and manifest['schema'] == SCHEMA and fingerprint(manifest) == generation, 'Invalid fighter save manifest')
        require(isinstance(manifest['files'], dict) and len(manifest['files']) <= MAX_FILES, 'Invalid fighter save file index')
        files, total = {}, 0
        for name, digest in manifest['files'].items():
            path = folder / 'save'
            require(not linked(path), 'Redirected fighter save root')
            for part in relative(name):
                path /= part
                require(not linked(path), 'Redirected native save file')
            require(path.is_file() and path.stat().st_size <= MAX_FILE, 'Missing or oversized native save file')
            data = path.read_bytes(); total += len(data)
            require(total <= MAX_BYTES and hashlib.sha256(data).hexdigest() == digest, 'Native save generation hash mismatch')
            files[name] = data
        validate_files(files)
        require(manifest['options'] in files, 'Fighter generation lost Options')
        restore(verify_container(files[manifest['options']]), manifest['extension'], manifest['ledger'], self.baseline)
        return {**manifest, 'generation': generation, 'files': files}

    def load(self):
        with self.lock(shared=True):
            generation = self._head()
            return self._read(generation) if generation else None

    def publish(self, expected_head, files, ledger, extension, options, *, checkpoint=lambda phase: None):
        """Publish a complete verified generation; stale writers cannot win.

        checkpoint is internal fault injection, never serialized/package input.
        Native success/status/flush observation must precede this method.
        """
        validate_files(files)
        require(options in files and PurePosixPath(options).name == 'Options', 'Missing native Options save')
        restore(verify_container(files[options]), extension, ledger, self.baseline)
        manifest = {'schema': SCHEMA, 'parent': expected_head, 'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
                    'ledger': ledger, 'extension': extension, 'options': options}
        generation = fingerprint(manifest)
        with self.lock():
            require(self._head() == expected_head, 'Fighter save changed since this batch began')
            destination = self.generations / generation
            require(not linked(destination), 'Redirected fighter save destination')
            if not destination.exists():
                with tempfile.TemporaryDirectory(prefix='.pending-', dir=self.generations) as temporary:
                    stage = Path(temporary) / 'generation'; stage.mkdir()
                    directories = {stage}
                    for name, data in sorted(files.items()):
                        path = stage / 'save' / name; path.parent.mkdir(parents=True, exist_ok=True)
                        with path.open('xb') as stream:
                            stream.write(data); stream.flush(); os.fsync(stream.fileno())
                        directories.update(parent for parent in path.parents if parent == stage or stage in parent.parents)
                    checkpoint('files')
                    atomic_json(stage / 'manifest.json', manifest)
                    for folder in sorted(directories, key=lambda path: len(path.parts), reverse=True):
                        sync_directory(folder)
                    checkpoint('manifest')
                    durable_rename(stage, destination)
                    checkpoint('generation')
            self._read(generation)  # Read back all files before publishing head.
            checkpoint('before-head')
            atomic_json(self.root / 'head.json', {'schema': SCHEMA, 'generation': generation})
            checkpoint('head')
        return generation

    def commit_batch(self, expected_head, updates, ledger, extension, options, *, checkpoint=lambda phase: None):
        """Merge only explicitly completed native records over a known head."""
        with self.lock(shared=True):
            require(self._head() == expected_head, 'Fighter save changed before batch verification')
            files = self._read(expected_head)['files'] if expected_head else {}
        require(isinstance(updates, dict) and updates, 'Empty native save batch')
        files.update(updates)
        return self.publish(expected_head, files, ledger, extension, options, checkpoint=checkpoint)
