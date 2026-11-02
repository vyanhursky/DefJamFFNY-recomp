"""Crash-consistent native/settings/ledger/extension publication, game-free."""
from copy import deepcopy
import hashlib
import hmac
import struct

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
