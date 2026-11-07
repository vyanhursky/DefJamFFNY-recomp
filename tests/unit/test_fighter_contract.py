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
