"""Managed Play adopts once; original saves and abandoned sessions never win."""
from test_fighter_profile_store import state, OPTIONS, PROFILE
from test_fighter_save_journal import put_files
from test_fighter_native import catalog
import pytest
import fighter_launch as launch
from fighter_profile_store import Store
from mods import Manager, atomic_json


@pytest.fixture
def context(tmp_path, monkeypatch):
    baseline, ledger, _, files, extension = state()
    manager = Manager(tmp_path / 'data', capabilities=['fighters-v1'])
    put_files(manager.data / 'save', files)
    atomic_json(manager.root / 'state.json', {'schema': 1, 'installed': {}, 'fighters': ['alpha']})
    monkeypatch.setattr(launch, 'parent_watch', lambda pid: (lambda: True, lambda: None))
    monkeypatch.setattr(launch, 'retail_catalog', lambda path: catalog()[0])
    monkeypatch.setattr(launch, 'build', lambda *a, **k: (tmp_path, {'binding_ledger': ledger}, tmp_path, None))
    monkeypatch.setattr(launch, 'runtime_environment', lambda *a: {})
    # Stop after native startup. Native I/O/publication has its own focused suite.
    monkeypatch.setattr(launch.time, 'sleep', lambda _: (manager.root / 'fighter-session-123.stop').write_text('complete'))
    return manager, baseline, ledger, files, extension


def test_managed_adoption_then_zero_pack_launch_uses_committed_store(context):
    manager, baseline, ledger, files, extension = context
    launch.supervise(manager, 123)
    store = Store(manager.root / 'fighter-profiles', baseline)
    before = store.load()
    assert (manager.root / 'fighter-adoption.json').exists()
    assert (manager.data / 'save' / PROFILE).read_bytes() == files[PROFILE]
    # A later external edit in the original source must never silently replace
    # the adopted career, including after the last pack is disabled.
    (manager.data / 'save' / PROFILE).write_bytes(b'changed outside managed play')
    atomic_json(manager.root / 'state.json', {'schema': 1, 'installed': {}, 'fighters': []})
    launch.supervise(manager, 123)
    assert store.load()['generation'] == before['generation']
    assert store.load()['files'][PROFILE] == files[PROFILE]
    sessions = list((manager.root / 'fighter-sessions').iterdir())
    assert len(sessions) == 2
    assert all((session / 'fighter-runtime-probe/save' / PROFILE).read_bytes() == files[PROFILE] for session in sessions)


def test_missing_adopted_head_never_reimports_source(context):
    manager, baseline, ledger, files, extension = context
    launch.supervise(manager, 123)
    (manager.root / 'fighter-profiles/head.json').unlink()
    with pytest.raises(ValueError, match='backup'):
        launch.supervise(manager, 123)
    assert (manager.data / 'save' / PROFILE).read_bytes() == files[PROFILE]
    assert 'state=failed' in (manager.root / 'fighter-session-123.ini').read_text()


def test_failed_composition_does_not_adopt_profiles(context, monkeypatch):
    manager, _, _, files, _ = context
    def fail(*args, **kwargs):
        raise ValueError('Incompatible fighter skeleton')
    monkeypatch.setattr(launch, 'build', fail)
    with pytest.raises(ValueError, match='skeleton'):
        launch.supervise(manager, 123)
    assert not (manager.root / 'fighter-adoption.json').exists()
    assert (manager.data / 'save' / PROFILE).read_bytes() == files[PROFILE]


def test_texture_only_install_does_not_adopt_profiles(context, monkeypatch):
    manager, _, _, _, _ = context
    atomic_json(manager.root / 'state.json', {'schema': 1, 'installed': {}})
    monkeypatch.setattr(launch, 'build', lambda *a, **k: pytest.fail('Stock launch compiled a roster'))
    launch.supervise(manager, 123)
    assert 'state=unused' in (manager.root / 'fighter-session-123.ini').read_text()
    assert not (manager.root / 'fighter-adoption.json').exists()


def test_initially_empty_adoption_never_imports_later_source_files(context):
    import shutil
    manager, baseline, _, files, _ = context
    shutil.rmtree(manager.data / 'save')
    launch.supervise(manager, 123)
    assert Store(manager.root / 'fighter-profiles', baseline).load() is None
    put_files(manager.data / 'save', files)
    launch.supervise(manager, 123)
    assert Store(manager.root / 'fighter-profiles', baseline).load() is None
    assert all(not list(path.glob('fighter-runtime-probe/save/**/*.*'))
               for path in (manager.root / 'fighter-sessions').iterdir())


def test_pending_install_refuses_launch_before_profile_adoption(context):
    manager, _, _, _, _ = context
    atomic_json(manager.root / 'journal.json', {'incomplete': True})
    with pytest.raises(ValueError, match='Recover the interrupted mod transaction'):
        launch.supervise(manager, 123)
    assert not (manager.root / 'fighter-adoption.json').exists()


def test_parent_loss_keeps_committed_profiles_and_records_recovery(context, monkeypatch):
    manager, baseline, _, _, _ = context
    watches = iter([True, False])
    monkeypatch.setattr(launch, 'parent_watch', lambda pid: (lambda: next(watches), lambda: None))
    launch.supervise(manager, 123)
    assert Store(manager.root / 'fighter-profiles', baseline).load() is not None
    assert 'Recovered last committed profiles' in (manager.root / 'fighter-session-123.ini').read_text()
