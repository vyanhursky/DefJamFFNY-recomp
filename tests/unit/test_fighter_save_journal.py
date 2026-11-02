"""Save intent is accepted only after every complete native file verifies."""
from pathlib import PurePosixPath
import struct
import json

import pytest

from test_fighter_profile_store import OPTIONS, PROFILE, container, state
from fighter_profile_store import Store, verify_container
from fighter_save_journal import Monitor, completed_records, decode, encode_unlock_state, initialize
import fighter_unlocks as unlocks


def batch(files, marks, number=1):
    output = bytearray(b'FSB1' + struct.pack('<5I', 1, number, len(files), len(marks), 0))
    for path, data in files.items():
        name = PurePosixPath(path).name.encode()
        payload = verify_container(data)
        output += struct.pack('<II', len(name), len(payload)) + data[0x4c:0x8c] + name.ljust(32, b'\0') + payload
    for handle, metadata in marks.items():
        output += struct.pack('<II', handle, metadata)
    return bytes(output)


def put_files(root, files):
    for name, data in files.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        path.with_name('SaveMeta.xbx').write_bytes(('Name=' + path.name + '\r\n').encode('utf-16'))
        path.with_name('saveimage.xbx').write_bytes(b'synthetic image')


def put_acks(journal, files, number=1):
    for index, data in enumerate(files.values()):
        (journal / f'{number:06}-{index:02}.closed').write_bytes(b'FSA1' + struct.pack('<4I', 1, number, index, len(data)) + data)


def test_torn_partial_batch_cannot_publish_and_unstaged_files_are_excluded(tmp_path):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'store', baseline)
    first = store.publish(None, files, ledger, extension, OPTIONS)
    save = tmp_path / 'working'; put_files(save, files)
    native = bytearray(verify_container(files[OPTIONS])); native[40] ^= 1
    profile = bytearray(verify_container(files[PROFILE])); profile[41] ^= 1
    updated = {OPTIONS: container(bytes(native)), PROFILE: container(bytes(profile))}
    handle = ledger['fighters']['alpha/fighter-299']['handle']
    journal = tmp_path / 'journal'; journal.mkdir()
    (journal / '000001.batch').write_bytes(batch(updated, {handle: unlocks.METADATA}))
    put_acks(journal, updated)
    monitor = Monitor(store, save, journal, ledger)
    assert not monitor.poll() and store.load()['generation'] == first
    put_files(save, {OPTIONS: updated[OPTIONS]})
    assert not monitor.poll() and store.load()['generation'] == first
    (save / PROFILE).write_bytes(updated[PROFILE][:-1])
    assert not monitor.poll() and store.load()['generation'] == first
    alien = 'UserData/45410049/000000000999/Unstaged'
    put_files(save, {alien: container(bytes(0x5904))})
    put_files(save, {PROFILE: updated[PROFILE]})
    assert monitor.poll() and not monitor.poll()
    current = store.load()
    assert current['generation'] != first and alien not in current['files']
    assert current['files'][PROFILE] == updated[PROFILE]
    assert current['extension']['marks']['alpha/fighter-299'] == unlocks.METADATA
    assert len(current['extension']['marks']) == 300


def test_initial_import_is_read_only_and_fum_retains_all_custom_progress(tmp_path):
    baseline, ledger, _, files, _ = state()
    source = tmp_path / 'original'; put_files(source, files)
    before = {path.relative_to(source).as_posix(): path.read_bytes() for path in source.rglob('*') if path.is_file()}
    store = Store(tmp_path / 'isolated', baseline)
    initial = initialize(store, source, ledger)
    assert initial['extension']['marks'] == {}
    assert {path.relative_to(source).as_posix(): path.read_bytes() for path in source.rglob('*') if path.is_file()} == before
    marks = {key: 0 for key in ledger['fighters']}
    native, extension = unlocks.project(verify_container(files[OPTIONS]), marks, ledger, baseline)
    assert native == verify_container(files[OPTIONS])
    store.commit_batch(initial['generation'], {OPTIONS: files[OPTIONS]}, ledger, extension, OPTIONS)
    encoded = encode_unlock_state(store.load(), baseline)
    assert encoded[:4] == b'FUM1' and struct.unpack_from('<III', encoded, 4) == (1, 300, 0)
    assert len(encoded) == 16 + 300 * 8


def test_fresh_namespace_bootstraps_only_from_a_complete_native_options_batch(tmp_path):
    baseline, ledger, _, files, _ = state()
    store = Store(tmp_path / 'fresh', baseline)
    save = tmp_path / 'working'; put_files(save, files)
    journal = tmp_path / 'journal'; journal.mkdir()
    (journal / '000001.batch').write_bytes(batch(files, {}))
    monitor = Monitor(store, save, journal, ledger)
    assert encode_unlock_state(None, baseline) == b'FUM1' + struct.pack('<III', 1, 0, 0)
    assert not monitor.poll() and store.load() is None
    put_acks(journal, files)
    assert monitor.poll()
    assert store.load()['files'][OPTIONS] == files[OPTIONS]
    assert store.load()['parent'] is None and store.load()['extension']['marks'] == {}


def test_native_compiler_save_migration_retains_removed_pack_and_updated_identities(tmp_path):
    from test_fighter_native import catalog, pack
    from fighter_bindings import seed
    source, _, _ = catalog(menu=True)
    alpha, beta = pack(count=2), pack('beta', 'retail/test-beta')
    _, first = source.compile([alpha, beta], binding_window=True)
    baseline = seed(source.db, source.source_sha256, source.rows)
    payload = bytearray(unlocks.SIZE)
    struct.pack_into('<I', payload, unlocks.SENTINEL, 0xffffffff)
    marks = {'alpha/fighter-0': unlocks.METADATA, 'beta/fighter-0': 0}
    native, extension = unlocks.project(bytes(payload), marks, first['binding_ledger'], baseline)
    files = {OPTIONS: container(native), PROFILE: container(bytes(0x5904))}
    store = Store(tmp_path / 'isolated', baseline)
    store.publish(None, files, first['binding_ledger'], extension, OPTIONS)

    # Removing Alpha affects the active roster, never historical ownership.
    _, removed = source.compile([beta], store.load()['ledger'], binding_window=True)
    assert 'alpha/fighter-0' not in removed['menu_roster']
    generation = initialize(store, tmp_path / 'unused-source', removed['binding_ledger'])
    assert generation['extension']['marks'] == marks
    encoded = encode_unlock_state(generation, baseline)
    assert dict(struct.iter_unpack('<II', encoded[16:])) == {
        first['binding_ledger']['fighters'][key]['handle']: value for key, value in marks.items()}

    # An update changes content, while a newly added pack gets fresh identities.
    alpha['version'] = '2.0.0'
    alpha['fighters'][0]['name'] = 'Updated Alpha'
    alpha['fighters'][0]['components']['stats']['health'] = 90
    gamma = pack('gamma')
    _, updated = source.compile([gamma, beta, alpha], generation['ledger'], binding_window=True)
    migrated = initialize(store, tmp_path / 'unused-source', updated['binding_ledger'])
    for key, entry in first['binding_ledger']['fighters'].items():
        assert migrated['ledger']['fighters'][key] == entry
    assert migrated['files'] == generation['files']
    assert migrated['extension']['marks'] == marks
    assert updated['cache_key'] != first['cache_key']

    # A subsequent real save batch adds Gamma without discarding dormant history.
    working, journal = tmp_path / 'working', tmp_path / 'journal'
    put_files(working, files); journal.mkdir()
    handle = updated['binding_ledger']['fighters']['gamma/fighter-0']['handle']
    (journal / '000001.batch').write_bytes(batch({OPTIONS: files[OPTIONS]}, {handle: 0}))
    put_acks(journal, {OPTIONS: files[OPTIONS]})
    monitor = Monitor(store, working, journal, updated['binding_ledger'])
    assert monitor.poll()
    restored = store.load()
    assert restored['extension']['marks'] == dict(marks, **{'gamma/fighter-0': 0})
    assert restored['files'][PROFILE] == files[PROFILE]


@pytest.mark.parametrize('mutation', ['missing', 'old-batch', 'other-record', 'truncated', 'trailing', 'wrong-payload', 'failed-signature'])
def test_identical_old_files_cannot_acknowledge_a_new_native_save(tmp_path, mutation):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'store', baseline)
    first = store.publish(None, files, ledger, extension, OPTIONS)
    save, journal = tmp_path / 'working', tmp_path / 'journal'
    put_files(save, files); journal.mkdir()
    (journal / '000001.batch').write_bytes(batch(files, {}))
    monitor = Monitor(store, save, journal, ledger)
    if mutation == 'missing':
        assert not monitor.poll()
    else:
        put_acks(journal, files)
        path = journal / '000001-00.closed'
        data = bytearray(path.read_bytes())
        if mutation == 'old-batch': struct.pack_into('<I', data, 8, 2)
        elif mutation == 'other-record': struct.pack_into('<I', data, 12, 1)
        elif mutation == 'truncated': data.pop()
        elif mutation == 'trailing': data += b'x'
        elif mutation == 'failed-signature': data[-1] ^= 1
        elif mutation == 'wrong-payload':
            payload = bytearray(verify_container(files[OPTIONS])); payload[40] ^= 1
            data[20:] = container(bytes(payload))
        path.write_bytes(data)
        with pytest.raises(ValueError): monitor.poll()
    assert store.load()['generation'] == first


def test_supervisor_reports_verifier_failure_without_replacing_committed_progress(tmp_path):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'store', baseline)
    first = store.publish(None, files, ledger, extension, OPTIONS)
    journal = tmp_path / 'journal'; journal.mkdir()
    (journal / '000001.batch').write_bytes(b'invalid intent')
    monitor = Monitor(store, tmp_path / 'working', journal, ledger)
    monitor.start(); monitor.thread.join(timeout=3)
    assert not monitor.thread.is_alive()
    with pytest.raises(ValueError, match='verification failed'):
        monitor.stop()
    assert json.loads((journal / 'supervisor.json').read_bytes())['state'] == 'failed'
    assert store.load()['generation'] == first


@pytest.mark.parametrize('mutation', ['header', 'version', 'count', 'records', 'reserved', 'name-length', 'payload-length', 'name', 'truncated', 'trailing', 'metadata'])
def test_journal_decoder_rejects_invalid_intent(mutation):
    _, ledger, _, files, _ = state()
    data = bytearray(batch({OPTIONS: files[OPTIONS]}, {ledger['fighters']['alpha/fighter-0']['handle']: 0}))
    if mutation == 'header': data[:4] = b'code'
    elif mutation == 'truncated': data.pop()
    elif mutation == 'trailing': data += b'x'
    elif mutation == 'name': data[96] = ord('/')
    elif mutation == 'metadata': struct.pack_into('<I', data, len(data) - 4, 1)
    else:
        offset, value = {'version': (4, 2), 'count': (16, 16385), 'records': (12, 17), 'reserved': (20, 1),
                         'name-length': (24, 33), 'payload-length': (28, 0xffffffff)}[mutation]
        struct.pack_into('<I', data, offset, value)
    with pytest.raises(ValueError): decode(bytes(data))
