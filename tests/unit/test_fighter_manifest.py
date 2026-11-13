"""Saves stay in save/: the fighter manifest and the one-time move from the beta store."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_fighter_profile_store import OPTIONS, PROFILE, container, state  # puts setup/ on the path
import fighter_manifest
import fighter_migrate
import fighter_unlocks as unlocks
from fighter_profile_store import Store, verify_container


def manager(tmp_path, runtime='1.2.0-beta.3'):
    data = tmp_path / 'data'
    (data / 'mod-manager').mkdir(parents=True)
    (data / 'mods').mkdir()
    game = tmp_path / 'game'
    (game / 'assets').mkdir(parents=True)
    (game / 'assets/djv2.sod').write_bytes(b'sod')
    messages = []
    return SimpleNamespace(data=data, root=data / 'mod-manager', mods=data / 'mods', game=game, runtime=runtime,
                           messages=messages, progress=lambda text, *rest: messages.append(text))


def parse(path):
    sections, section = {}, None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('[') and line.endswith(']'):
            section = sections.setdefault(line[1:-1], {})
        elif '=' in line:
            key, value = line.split('=', 1)
            section[key] = value
    return sections


def fake_build(monkeypatch, tmp_path, ledger):
    import fighter_packages
    import fighter_ui_hd
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'fighter-names.bin').write_bytes(b'names')
    calls = []

    def build(mgr, state, *, language=None, **_):
        calls.append(language)
        return cache, {'binding_ledger': ledger}, tmp_path / 'screens.viv', None
    monkeypatch.setattr(fighter_packages, 'build', build)
    monkeypatch.setattr(fighter_packages, 'runtime_environment',
                        lambda cache, report, screens, language=None, **_: {'RECOMP_FIGHTER_NAMES': str(cache / 'fighter-names.bin'),
                                                                           'RECOMP_FIGHTER_NAMES_SHA256': 'ab' * 32})
    monkeypatch.setattr(fighter_ui_hd, 'stage', lambda cache, report, mods: None)
    return calls


def test_manifest_lists_every_input_stamp_and_names_custom_identities(tmp_path, monkeypatch):
    _, ledger, _, _, _ = state()
    mgr = manager(tmp_path)
    (mgr.mods / 'alpha').mkdir()
    (mgr.mods / 'alpha/fighters.json').write_text('{}')
    calls = fake_build(monkeypatch, tmp_path, ledger)
    language = tmp_path / 'mods-lang'
    language.mkdir()
    (language / 'manifest.ini').write_text('[pack]\n')
    path = fighter_manifest.write(mgr, {'fighters': ['alpha']}, language=language)
    assert calls == [language]
    manifest = parse(path)
    assert manifest['manifest'] == {'schema': '1', 'runtime': '1.2.0-beta.3', 'language': str(language), 'packs': 'alpha'}
    environment = manifest['environment']
    assert environment['RECOMP_FIGHTER_STATE'] == str(mgr.data / 'fighter-state')
    assert environment['RECOMP_FIGHTER_IDENTITIES'] == str(mgr.root / 'fighter-identities.txt')
    stamped = {value.split('|', 2)[2]: value for value in manifest['inputs'].values()}
    for expected in (mgr.game / 'assets/djv2.sod', mgr.mods / 'alpha/fighters.json', language / 'manifest.ini',
                     tmp_path / 'cache/fighter-names.bin', mgr.root / 'fighter-identities.txt'):
        info = expected.stat()
        assert stamped[str(expected)] == f'{info.st_size}|{info.st_mtime_ns}|{expected}'
    names = (mgr.root / 'fighter-identities.txt').read_text().splitlines()[1:]
    custom = {key: entry for key, entry in ledger['fighters'].items() if not key.startswith('retail/')}
    assert names == [f"{entry['handle']:08X} {key}" for key, entry in sorted(custom.items())]


def test_disabling_the_last_pack_removes_the_manifest(tmp_path, monkeypatch):
    _, ledger, _, _, _ = state()
    mgr = manager(tmp_path)
    fake_build(monkeypatch, tmp_path, ledger)
    fighter_manifest.write(mgr, {'fighters': ['alpha']})
    assert (mgr.root / 'fighter-manifest.ini').exists()
    assert fighter_manifest.write(mgr, {'fighters': []}) is None
    assert not (mgr.root / 'fighter-manifest.ini').exists()
    assert not (mgr.root / 'fighter-identities.txt').exists()


def beta_store(tmp_path, monkeypatch, *, marks=None):
    """A beta.2 data folder: newest saves in the store, a stale save/ from adoption day."""
    import fighter_build
    import fighter_bindings
    baseline, ledger, all_marks, files, extension = state()
    if marks is not None:
        native, extension = unlocks.project(verify_container(files[OPTIONS]), marks, ledger, baseline)
        files = {**files, OPTIONS: container(native)}
    mgr = manager(tmp_path)
    monkeypatch.setattr(fighter_build, 'retail_catalog', lambda path: SimpleNamespace(db=None, source_sha256='', rows=None))
    monkeypatch.setattr(fighter_bindings, 'seed', lambda *args: baseline)
    store = Store(mgr.root / 'fighter-profiles', baseline)
    generation = store.publish(None, files, ledger, extension, OPTIONS)
    stale = mgr.data / 'save/UserData/45410049/OLDPROFILE00'
    stale.mkdir(parents=True)
    (stale / 'Stale').write_bytes(b'adoption-day profile')
    return mgr, files, generation


def test_store_head_moves_back_into_save_with_a_backup_and_named_sidecar(tmp_path, monkeypatch):
    _, ledger, _, _, _ = state()
    custom = sorted(key for key in ledger['fighters'] if not key.startswith('retail/'))
    marks = {key: 0 for key in ledger['fighters']}
    marks[custom[0]] = unlocks.METADATA
    mgr, files, generation = beta_store(tmp_path, monkeypatch, marks=marks)
    assert fighter_migrate.pending(mgr.data)
    backup = fighter_migrate.migrate(mgr, now=__import__('datetime').datetime(2026, 11, 12, 21, 30, 0))
    assert backup == mgr.data / 'save-backup-20261112-213000'
    assert (backup / 'UserData/45410049/OLDPROFILE00/Stale').read_bytes() == b'adoption-day profile'
    title = mgr.data / 'save/UserData/45410049'
    written = {path.relative_to(mgr.data / 'save').as_posix(): path.read_bytes() for path in title.rglob('*') if path.is_file()}
    assert written == files
    sidecar = (mgr.data / 'fighter-state/unlocks.ini').read_text().splitlines()
    assert sidecar[2:4] == ['[fighter-unlocks]', 'schema=1']
    entries = dict(line.split('=') for line in sidecar[4:])
    assert entries[custom[0]] == '1' and set(entries) == set(custom)
    assert 'save-backup-20261112-213000' in (mgr.data / 'fighter-state/notice.txt').read_text()
    assert not fighter_migrate.pending(mgr.data)
    # The store is left as it was, read-only, for one release.
    assert Store(mgr.root / 'fighter-profiles', None).generations.is_dir()
    assert fighter_migrate.migrate(mgr) is None


def test_retail_options_in_save_needs_no_python_to_load(tmp_path, monkeypatch):
    """After the move the Options file in save/ holds retail marks only (v1.1.1 reads it)."""
    mgr, files, _ = beta_store(tmp_path, monkeypatch)
    fighter_migrate.migrate(mgr)
    options = (mgr.data / 'save' / OPTIONS).read_bytes()
    keys = unlocks.settings_keys(verify_container(options))
    assert keys == unlocks.settings_keys(verify_container(files[OPTIONS]))
    assert (mgr.data / 'save' / PROFILE).read_bytes() == files[PROFILE]


def test_no_store_means_nothing_to_move(tmp_path):
    mgr = manager(tmp_path)
    assert not fighter_migrate.pending(mgr.data)
    assert fighter_migrate.migrate(mgr) is None
    assert not (mgr.data / 'fighter-state').exists()


def test_interrupted_title_swap_is_finished_on_the_next_try(tmp_path, monkeypatch):
    mgr, files, _ = beta_store(tmp_path, monkeypatch)
    title = mgr.data / 'save/UserData/45410049'
    (title.parent / '45410049.migrating').mkdir()
    (title.parent / '45410049.migrating/half').write_bytes(b'x')
    fighter_migrate.migrate(mgr)
    assert not (title.parent / '45410049.migrating').exists()
    assert not (title / 'OLDPROFILE00').exists()


def test_sidecar_text_matches_the_game_format():
    text = fighter_migrate.sidecar_text({'beta/two': 0, 'alpha/one': unlocks.METADATA}).decode()
    assert text.splitlines()[2:] == ['[fighter-unlocks]', 'schema=1', 'alpha/one=1', 'beta/two=0']
    with pytest.raises(ValueError):
        fighter_migrate.sidecar_text({'no-slash': 0})
