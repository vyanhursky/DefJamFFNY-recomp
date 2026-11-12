"""Whole-pack installs/activation fail atomically and preserve historical IDs."""
import json
from pathlib import Path
import zipfile

import pytest
from test_fighter_native import catalog, pack
import fighter_packages as fighters
from mods import Manager


def archive(tmp_path, manifest, extras=None):
    path = tmp_path / (manifest['id'] + '-' + manifest['version'] + '.zip')
    with zipfile.ZipFile(path, 'w') as bundle:
        bundle.writestr(manifest['id'] + '/fighters.json', json.dumps(manifest))
        for name, content in (extras or {}).items():
            bundle.writestr(manifest['id'] + '/' + name, content)
    return path


def test_typed_audio_inventory_checks_hash_and_accounts_for_file(tmp_path):
    from test_fighter_voice_r2 import source as r2_source
    import hashlib
    data = r2_source()
    spec = {'format': 'ea-adpcm-r2', 'path': 'speech.bin', 'sha256': hashlib.sha256(data).hexdigest()}
    definition = pack()
    definition['resources'] = [{'id': 'voice', 'kind': 'voice',
        'compatibility': {'events': 'retail/binding-test-alpha'},
        'source': {'format': 'fighter-voice-2', 'template_voice': 22,
                   'samples': {}, 'intro': spec, 'extro': spec}}]
    (tmp_path / 'fighters.json').write_text(json.dumps(definition), encoding='utf-8')
    (tmp_path / 'speech.bin').write_bytes(data)
    assert fighters.inventory(tmp_path)['id'] == 'alpha'
    (tmp_path / 'speech.bin').write_bytes(data[:-1])
    with pytest.raises(ValueError, match='hash mismatch'):
        fighters.inventory(tmp_path)


@pytest.fixture
def manager(tmp_path, monkeypatch):
    source, _, _ = catalog(menu=True)
    real = fighters.compile_inputs
    monkeypatch.setattr(fighters, 'compile_inputs', lambda sod, paths, packs, ledger, **kw:
                        real(sod, paths, packs, ledger, catalog=source, **kw))
    monkeypatch.setattr(fighters, 'prepare_portraits', lambda *args, **kwargs: tmp_path / 'screens.viv')
    return Manager(tmp_path / 'data', capabilities=['textures-v1', 'fighters-v1'])


def test_local_install_reports_bytes_for_the_launcher_progress_bar(manager, tmp_path, monkeypatch):
    """The launcher draws a real bar from done/total while files are unpacked, then goes indeterminate."""
    calls = []
    real = manager.progress
    monkeypatch.setattr(manager, 'progress', lambda text, done=0, total=0: (calls.append((text, done, total)), real(text, done, total))[1])
    manager.install_local(archive(tmp_path, pack()))
    unpacking = [(done, total) for text, done, total in calls if text == 'Unpacking the Fighter ZIP']
    assert unpacking and unpacking[-1][0] == unpacking[-1][1] > 0
    assert [done for done, _ in unpacking] == sorted(done for done, _ in unpacking)
    assert calls[-1][0].startswith('Fighter package installed')


def test_whole_pack_install_enable_update_rollback_disable_remove(manager, tmp_path):
    definition = pack(count=2)
    manager.install_local(archive(tmp_path, definition))
    assert not manager.state().get('fighters')
    manager.activate_fighter('alpha', True)
    state = manager.state()
    assert state['fighters'] == ['alpha']
    assert {'alpha/fighter-0', 'alpha/fighter-1'} <= state['fighter_ledger']['fighters'].keys()
    definition['version'] = '1.1.0'
    definition['fighters'][0]['name'] = 'Updated'
    manager.install_local(archive(tmp_path, definition))
    assert manager.state()['fighter_ledger'] == state['fighter_ledger']
    manager.rollback('alpha')
    assert manager.state()['installed']['alpha']['version'] == '1.0.0'
    with pytest.raises(ValueError, match='Disable'):
        manager.remove('alpha')
    manager.activate_fighter('alpha', False)
    manager.remove('alpha')
    assert manager.state()['fighter_ledger'] == state['fighter_ledger']
    assert manager.state()['fighters'] == []
    assert not (manager.data / 'save').exists()  # Activation never adopts/mutates profiles.


def test_failed_update_keeps_enabled_roster_and_download(manager, tmp_path):
    definition = pack()
    manager.install_local(archive(tmp_path, definition)); manager.activate_fighter('alpha', True)
    before = manager.state()
    definition['version'] = '1.1.0'; definition['fighters'][0]['inherits'] = 'missing/fighter'
    with pytest.raises(ValueError):
        manager.install_local(archive(tmp_path, definition))
    assert manager.state() == before
    assert manager.unchanged(manager.mods / 'alpha', before['installed']['alpha'])
    assert not (manager.root / 'journal.json').exists()


def test_dependencies_cannot_be_disabled_while_required(manager, tmp_path):
    alpha, beta = pack(), pack('beta')
    beta['requires'] = {'alpha': '1.0.0'}
    manager.install_local(archive(tmp_path, alpha)); manager.install_local(archive(tmp_path, beta))
    with pytest.raises(ValueError):
        manager.activate_fighter('beta', True)
    manager.activate_fighter('alpha', True); manager.activate_fighter('beta', True)
    before = manager.state()
    with pytest.raises(ValueError):
        manager.activate_fighter('alpha', False)
    assert manager.state() == before
    alpha['version'] = '1.1.0'
    with pytest.raises(ValueError):
        manager.install_local(archive(tmp_path, alpha))
    assert manager.state() == before


@pytest.mark.parametrize('extra', ['run.exe', 'payload.bin', 'extra.json', '../escape.json'])
def test_package_does_not_admit_undeclared_or_executable_files(manager, tmp_path, extra):
    with pytest.raises(ValueError):
        manager.install_local(archive(tmp_path, pack(), {extra: b'not resource data'}))
    assert manager.state()['installed'] == {}


def test_missing_enabled_pack_refuses_composition_but_can_be_disabled(manager, tmp_path):
    manager.install_local(archive(tmp_path, pack())); manager.activate_fighter('alpha', True)
    (manager.mods / 'alpha/fighters.json').unlink()
    with pytest.raises(ValueError, match='restore or disable'):
        fighters.build(manager, manager.state())
    manager.activate_fighter('alpha', False)
    assert manager.state()['fighters'] == []


def test_thunderstore_fighter_zip_imports_without_storefront_files(manager, tmp_path):
    from test_mod_thunderstore import icon
    definition = pack(count=1)
    path = archive(tmp_path, definition)
    with zipfile.ZipFile(path, 'a') as bundle:
        bundle.writestr('manifest.json', json.dumps(dict(name='Alpha', version_number='1.0.0', website_url='',
                                                         description='Synthetic', dependencies=[])))
        bundle.writestr('README.md', '# Alpha\n')
        bundle.writestr('icon.png', icon())
    manager.install_local(path)
    assert sorted(p.name for p in (manager.mods / 'alpha').iterdir()) == ['fighters.json']
    with zipfile.ZipFile(path, 'a') as bundle:
        bundle.writestr('stray.txt', 'not storefront metadata')
    with pytest.raises(ValueError, match='one pack-id root'):
        manager.install_local(path)
