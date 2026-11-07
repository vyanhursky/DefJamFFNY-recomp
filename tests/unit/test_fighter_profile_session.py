"""Shared launch preparation must preserve native profiles across restarts."""
import pytest

from test_fighter_profile_store import OPTIONS, PROFILE, state
from test_fighter_save_journal import batch, put_acks, put_files
from fighter_profile_store import Store
from fighter_profile_session import prepare


def test_session_imports_once_and_recovers_committed_bytes_not_abandoned_work(tmp_path):
    baseline, ledger, _, files, _ = state()
    source = tmp_path / 'original'
    put_files(source, files)
    original = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    store = Store(tmp_path / 'store', baseline)
    first = prepare(store, ledger, tmp_path / 'sessions', source=source)
    head = store.load()
    (first.data_root / 'save' / PROFILE).write_bytes(b'torn write')
    (first.journal / '000001.batch').write_bytes(batch({PROFILE: files[PROFILE]}, {}))
    second = prepare(store, ledger, tmp_path / 'sessions')
    assert second.root != first.root
    assert second.monitor.expected_head == head['generation']
    assert (second.data_root / 'save' / PROFILE).read_bytes() == files[PROFILE]
    assert not (second.journal / '000001.batch').exists()
    assert second.unlock_state.read_bytes() == first.unlock_state.read_bytes()
    assert store.load()['generation'] == head['generation']
    assert {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()} == original


def test_session_commit_and_restart_preserves_extension_without_active_roster(tmp_path):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'store', baseline)
    store.publish(None, files, ledger, extension, OPTIONS)
    session = prepare(store, ledger, tmp_path / 'sessions')
    put_files(session.data_root / 'save', files)  # Native metadata accompanies a completed write.
    session.monitor.start()
    # Native input to the backend contains only a completed Options batch;
    # every custom definition can be inactive while its historical marks remain.
    (session.journal / '000001.batch').write_bytes(batch({OPTIONS: files[OPTIONS]}, {}))
    put_acks(session.journal, {OPTIONS: files[OPTIONS]})
    # Let the background verifier own polling, just as the native driver does.
    import time
    deadline = time.monotonic() + 5
    while not session.monitor.committed and time.monotonic() < deadline:
        time.sleep(.01)
    session.finish(require_complete=True)
    assert len(session.monitor.committed) == 1
    resumed = prepare(store, ledger, tmp_path / 'sessions')
    assert resumed.generation['extension'] == extension
    assert resumed.generation['files'][PROFILE] == files[PROFILE]
    assert resumed.monitor.expected_head == session.monitor.committed[-1][1]
    assert resumed.environment['DEFJAM_DATA'] == str(resumed.data_root)


@pytest.mark.parametrize('overlap', ['source-store', 'source-sessions', 'store-sessions'])
def test_session_refuses_overlapping_native_and_durable_roots(tmp_path, overlap):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'store', baseline)
    store.publish(None, files, ledger, extension, OPTIONS)
    source, sessions = tmp_path / 'original', tmp_path / 'sessions'
    if overlap == 'source-store':
        source = store.root / 'save'
    elif overlap == 'source-sessions':
        sessions = source / 'sessions'
    else:
        sessions = store.root / 'sessions'
    with pytest.raises(ValueError, match='separate'):
        prepare(store, ledger, sessions, source=source)


def test_fresh_session_cannot_discard_adopted_profiles(tmp_path):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'store', baseline)
    head = store.publish(None, files, ledger, extension, OPTIONS)
    with pytest.raises(ValueError, match='empty Store'):
        prepare(store, ledger, tmp_path / 'sessions', fresh=True)
    assert store.load()['generation'] == head


def test_clean_exit_refuses_unfinished_native_batch(tmp_path):
    baseline, ledger, _, files, extension = state()
    store = Store(tmp_path / 'store', baseline)
    store.publish(None, files, ledger, extension, OPTIONS)
    session = prepare(store, ledger, tmp_path / 'sessions')
    session.monitor.start()
    (session.journal / '000001.batch').write_bytes(batch({OPTIONS: files[OPTIONS]}, {}))
    with pytest.raises(ValueError, match='unverified'):
        session.finish(require_complete=True)
    assert not session.monitor.committed
