"""Crash-consistent native/settings/ledger/extension publication, game-free."""
from copy import deepcopy
import hashlib
import hmac
from pathlib import Path
import struct
import subprocess
import sys

import pytest

from test_fighter_unlocks import fixture
from fighter_profile_store import Store, relative, verify_container
import fighter_unlocks as unlocks

OPTIONS = 'UserData/45410049/1A3F1B2E4ADD/Options'
PROFILE = 'UserData/45410049/000000005659/VY'


def container(payload, identity=bytes(64)):
    data = bytearray(b'20CM' + struct.pack('<III', 0x8c + len(payload), 0x40, len(payload)) + bytes(60) + identity + payload)
    for start, end, at in ((0x4c, 0x8c, 0x10), (0x8c, len(data), 0x24), (0, 0x38, 0x38)):
        data[at:at + 20] = hmac.new(bytes(16), data[start:end], hashlib.sha1).digest()
    return bytes(data)


def state():
    _, baseline, ledger, payload = fixture()
    marks = {key: 0 for key in ledger['fighters']}
    native, extension = unlocks.project(payload, marks, ledger, baseline)
    return baseline, ledger, marks, {OPTIONS: container(native), PROFILE: container(bytes(0x5904))}, extension


def test_generations_publish_coherent_native_and_300_custom_marks(tmp_path):
    baseline, ledger, marks, files, extension = state()
    original = deepcopy(files)
    store = Store(tmp_path / 'isolated-fighter-profiles', baseline)
    assert store.load() is None
    first = store.publish(None, files, ledger, extension, OPTIONS)
    loaded = store.load()
    assert loaded['generation'] == first and loaded['files'] == files
    assert unlocks.restore(verify_container(loaded['files'][OPTIONS]), loaded['extension'], loaded['ledger'], baseline) == marks
    marks['alpha/fighter-17'] = unlocks.METADATA
    native, extension2 = unlocks.project(verify_container(files[OPTIONS]), marks, ledger, baseline)
    second = store.commit_batch(first, {OPTIONS: container(native)}, ledger, extension2, OPTIONS)
    assert second != first and store.load()['parent'] == first
    assert store.load()['files'][PROFILE] == files[PROFILE]
    assert files == original
    with pytest.raises(ValueError, match='changed'):
        store.publish(first, files, ledger, extension, OPTIONS)
    assert store.load()['generation'] == second


@pytest.mark.parametrize('phase', ['files', 'manifest', 'generation', 'before-head', 'head'])
def test_interruption_retains_a_complete_old_or_new_generation(tmp_path, phase):
    baseline, ledger, marks, files, extension = state()
    store = Store(tmp_path / 'isolated', baseline)
    first = store.publish(None, files, ledger, extension, OPTIONS)
    marks['alpha/fighter-299'] = unlocks.METADATA
    native, next_extension = unlocks.project(verify_container(files[OPTIONS]), marks, ledger, baseline)
    def stop(at):
        if phase == at:
            raise RuntimeError('simulated process interruption')
    with pytest.raises(RuntimeError):
        store.commit_batch(first, {OPTIONS: container(native)}, ledger, next_extension, OPTIONS, checkpoint=stop)
    recovered = Store(tmp_path / 'isolated', baseline).load()
    assert recovered['generation'] == first if phase != 'head' else recovered['generation'] != first
    restored = unlocks.restore(verify_container(recovered['files'][OPTIONS]), recovered['extension'], recovered['ledger'], baseline)
    assert restored['alpha/fighter-299'] == (unlocks.METADATA if phase == 'head' else 0)


@pytest.mark.parametrize('phase', ['files', 'manifest', 'generation', 'before-head', 'head'])
def test_process_death_recovers_coherent_profile_and_extension(tmp_path, phase):
    """Exit without finally/lock/tempdir cleanup, then reopen in another process."""
    baseline, ledger, _, files, extension = state()
    root = tmp_path / 'interrupted'
    first = Store(root, baseline).publish(None, files, ledger, extension, OPTIONS)
    script = '''
import os
from pathlib import Path
import sys
repo, root, phase = sys.argv[1:]
sys.path[:0] = [str(Path(repo) / 'setup'), str(Path(repo) / 'tests/unit')]
from test_fighter_profile_store import state, container, OPTIONS, PROFILE
from fighter_profile_store import Store, verify_container
import fighter_unlocks as unlocks
baseline, ledger, marks, files, extension = state()
store = Store(root, baseline)
previous = store.load()
marks['alpha/fighter-299'] = unlocks.METADATA
native, extension = unlocks.project(verify_container(files[OPTIONS]), marks, ledger, baseline)
profile = bytearray(verify_container(files[PROFILE]))
profile[1234] = 77
def die(at):
    if at == phase:
        os._exit(73)
store.commit_batch(previous['generation'], {OPTIONS: container(native), PROFILE: container(bytes(profile))},
                   ledger, extension, OPTIONS, checkpoint=die)
raise AssertionError('Crash checkpoint was not reached')
'''
    process = subprocess.run([sys.executable, '-c', script, str(Path(__file__).resolve().parents[2]),
                              str(root), phase], capture_output=True, text=True, timeout=20)
    assert process.returncode == 73, process.stdout + process.stderr
    recovered = Store(root, baseline).load()
    published = phase == 'head'
    assert (recovered['generation'] != first) == published
    restored = unlocks.restore(verify_container(recovered['files'][OPTIONS]), recovered['extension'],
                               recovered['ledger'], baseline)
    assert restored['alpha/fighter-299'] == (unlocks.METADATA if published else 0)
    expected_profile = bytearray(verify_container(files[PROFILE]))
    if published:
        expected_profile[1234] = 77
    assert recovered['files'][PROFILE] == container(bytes(expected_profile))
    # Recovery must also release the dead writer's lock and permit a new commit.
    following = Store(root, baseline).commit_batch(recovered['generation'], {PROFILE: recovered['files'][PROFILE]},
                                                  ledger, recovered['extension'], OPTIONS)
    assert Store(root, baseline).load()['parent'] == recovered['generation']
    assert following != recovered['generation']


def test_crossed_extension_torn_native_save_and_unknown_updates_cannot_publish(tmp_path):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'isolated', baseline)
    first = store.publish(None, files, ledger, extension, OPTIONS)
    bad_extension = dict(extension, settings_sha256='0' * 64)
    with pytest.raises(ValueError, match='different save generation'):
        store.commit_batch(first, {OPTIONS: files[OPTIONS]}, ledger, bad_extension, OPTIONS)
    torn = bytearray(files[PROFILE]); torn[-1] ^= 1
    with pytest.raises(ValueError, match='signature'):
        store.commit_batch(first, {PROFILE: bytes(torn)}, ledger, extension, OPTIONS)
    for path in ('../Options', 'UserData/45410049/000000005659/CON', 'UserData/45410049/000000005659/a:b',
                 'UserData/45410049/000000005659/VY.', 'UserData/45410049/000000005659/../VY'):
        with pytest.raises(ValueError): relative(path)
    assert store.load()['generation'] == first


def test_generation_corruption_fails_without_changing_committed_head(tmp_path):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'isolated', baseline)
    first = store.publish(None, files, ledger, extension, OPTIONS)
    path = store.generations / first / 'save' / PROFILE
    path.write_bytes(files[PROFILE][:-1])
    with pytest.raises(ValueError, match='hash mismatch'):
        store.load()
    assert store._head() == first
