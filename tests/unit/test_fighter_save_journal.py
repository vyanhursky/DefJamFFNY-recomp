"""Save intent is accepted only after every complete native file verifies."""
from pathlib import PurePosixPath
import struct

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
