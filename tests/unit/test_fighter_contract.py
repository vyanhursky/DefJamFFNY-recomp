"""Creator validation uses the native compiler and pins exactly the read bytes."""
import importlib.util
import json
from pathlib import Path

import pytest
from test_fighter_native import catalog, pack

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('fighter_contract', ROOT / 'scripts/fighter-contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    baseline, _, _ = catalog(menu=True)
    compile_native = contract.compile_inputs
    monkeypatch.setattr(contract, 'compile_inputs', lambda sod, paths, packs, **kw:
                        compile_native(sod, paths, packs, catalog=baseline, **kw))
    monkeypatch.setattr(contract, 'prepare_portraits', lambda *args, **kw: tmp_path / 'screens.viv')
    folder = tmp_path / 'alpha'; folder.mkdir()
    (folder / 'fighters.json').write_text(json.dumps(pack(count=2)))
    return tmp_path, folder


def test_contract_compiles_complete_pack_without_installing_or_modifying_input(workspace):
    root, folder = workspace
    before = (folder / 'fighters.json').read_bytes()
    report = contract.validate(root / 'game', [folder])
    assert report['native_compilation'] and not report['native_playtest']
    assert report['added_fighters'] == 2
    assert report['binding_mode'] == 'participant-window'
    assert set(report['packs'][0]['files']) == {'fighters.json'}
    assert (folder / 'fighters.json').read_bytes() == before
    assert sorted(p.name for p in root.iterdir()) == ['alpha']


def test_contract_rejects_mid_compile_edits(workspace, monkeypatch):
    root, folder = workspace
    def changed(*args, **kw):
        (folder / 'fighters.json').write_text('{}')
    monkeypatch.setattr(contract, 'prepare_portraits', changed)
    with pytest.raises(ValueError, match='changed during validation'):
        contract.validate(root / 'game', [folder])


def test_contract_rejects_unrelated_files_before_compilation(workspace):
    root, folder = workspace
    (folder / 'payload.py').write_text('raise RuntimeError()')
    with pytest.raises(ValueError, match='Unsupported|Undeclared'):
        contract.validate(root / 'game', [folder])


def voice_workspace(tmp_path, monkeypatch, data):
    import hashlib
    from test_fighter_voice_compile import explicit_source
    compiler, _ = explicit_source()
    monkeypatch.setattr(contract, 'ROOT', tmp_path)
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/fighter-native-baseline.json').write_text(json.dumps({'speech_sha256': compiler.source_hash}))
    game = tmp_path / 'game'; (game / 'audio').mkdir(parents=True)
    (game / 'audio/speech2.viv').write_bytes(compiler.archive.data)
    folder = tmp_path / 'export'; folder.mkdir()
    (folder / 'clip.bin').write_bytes(data)
    audio = {'path': 'clip.bin', 'sha256': hashlib.sha256(data).hexdigest(), 'format': 'ea-adpcm-r2'}
    source = {'format': 'fighter-voice-4', 'banks': {
        'Character': {'state': 'present', 'template_voice': 22, 'family': 1, 'samples': {'0': audio}},
        'Taunts': {'state': 'absent'}, 'Enviro': {'state': 'absent'}}, 'intro': audio, 'extro': audio}
    path = folder / 'voice-source.json'; path.write_text(json.dumps(source))
    return game, path


def test_voice_staging_api_uses_shared_compiler_without_installing(tmp_path, monkeypatch):
    import hashlib
    from test_fighter_voice_r2 import source
    game, path = voice_workspace(tmp_path, monkeypatch, source())
    before = path.read_bytes()
    report = contract.validate_voice(game, path)
    assert report['component_compilation'] and not report['native_playtest']
    assert report['source_sha256'] == hashlib.sha256(before).hexdigest()
    assert path.read_bytes() == before
    assert sorted(p.name for p in path.parent.iterdir()) == ['clip.bin', 'voice-source.json']


def test_voice_staging_rejects_predictors_and_native_per_bank_expansion(tmp_path, monkeypatch):
    from test_fighter_voice_r2 import source
    from fighter_assets import AssetError
    game, path = voice_workspace(tmp_path, monkeypatch, source((28,), [b'\x40' + bytes(14)]))
    with pytest.raises(AssetError, match='predictor'):
        contract.validate_voice(game, path)
    # A valid source fits its physical bank but rebuilding logical entries at
    # native256-byte alignment exceeds the smaller invented category budget.
    import fighter_voice_bank
    import hashlib
    literal = b'\xee' + bytes(60)
    data = source((140,), [literal * 5])
    (path.parent / 'clip.bin').write_bytes(data)
    doc = json.loads(path.read_text())
    for spec in (doc['intro'], doc['extro'], doc['banks']['Character']['samples']['0']):
        spec['sha256'] = hashlib.sha256(data).hexdigest()
    path.write_text(json.dumps(doc))
    monkeypatch.setattr(fighter_voice_bank, 'MAX_BANK_BYTES', 900)
    with pytest.raises(AssetError, match='Composed voice bank exceeds budget'):
        contract.validate_voice(game, path)
