"""Whole-pack semantic resolution; all fighters/resources here are synthetic."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('registry',
    Path(__file__).resolve().parents[2] / 'setup/fighter_registry.py')
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)


def pack(owner):
    return {'schema': registry.SCHEMA, 'id': owner, 'version': '1.0.0',
            'requires': {}, 'resources': [], 'fighters': [], 'overrides': []}


def resource(name, kind, **compatibility):
    return {'id': name, 'kind': kind, 'compatibility': compatibility}


def baseline():
    result = pack('retail')
    result['resources'] = [
        resource('body', 'appearance', skeleton='retail/joints'),
        resource('moves', 'moveset', skeleton='retail/joints', events='retail/events'),
        resource('voice', 'voice', events='retail/events'), resource('portrait', 'portrait')]
    result['fighters'] = [{'id': 'donor', 'name': 'Synthetic Donor', 'components': {
        'appearance': 'retail/body', 'moveset': 'retail/moves', 'voice': 'retail/voice',
        'portrait': 'retail/portrait', 'stats': {'health': 50, 'speed': 40}}}]
    return result


def addition(owner='alpha', count=1):
    result = pack(owner)
    result['fighters'] = [{'id': f'fighter-{i}', 'name': 'Same Display Name',
                           'inherits': 'retail/donor', 'components': {'stats': {'health': 60 + i}}}
                          for i in range(count)]
    return result


def edit(owner, **groups):
    result = pack(owner)
    result['overrides'] = [{'target': 'retail/donor', 'components': groups, 'supersedes': []}]
    return result


def fails(code, base, packs):
    with pytest.raises(registry.RegistryError) as caught:
        registry.resolve(base, packs)
    assert caught.value.code == code
    return caught.value


def test_single_multiple_independent_and_inputs_immutable():
    base, a, b = baseline(), addition('alpha', 2), addition('beta')
    original = deepcopy([base, a, b])
    snapshot = registry.resolve(base, [a, b])
    assert set(snapshot['fighters']) == {'retail/donor', 'alpha/fighter-0', 'alpha/fighter-1', 'beta/fighter-0'}
    assert snapshot['fighters']['alpha/fighter-0']['components']['stats'] == {'health': 60, 'speed': 40}
    assert snapshot['fighters']['retail/donor']['components']['stats']['health'] == 50
    assert not snapshot['runtime_ready']
    assert [base, a, b] == original
    assert snapshot == registry.resolve(base, [b, a])


def test_independent_component_edits_compose():
    a = edit('picture', portrait='picture/new-picture')
    a['resources'] = [resource('new-picture', 'portrait')]
    b = edit('speech', voice='speech/new-voice')
    b['resources'] = [resource('new-voice', 'voice', events='retail/events')]
    snapshot = registry.resolve(baseline(), [b, a])
    assert snapshot['fighters']['retail/donor']['components']['portrait'] == 'picture/new-picture'
    assert snapshot['fighters']['retail/donor']['components']['voice'] == 'speech/new-voice'


def test_conflict_report_is_actionable_and_deterministic():
    a, b = edit('alpha', stats={'health': 80}), edit('beta', stats={'health': 90})
    error = fails('component-conflict', baseline(), [a, b])
    conflict = error.details['conflicts'][0]
    assert conflict['fighter'] == 'retail/donor'
    assert conflict['component'] == 'stats'
    assert conflict['providers'] == ['alpha', 'beta']
    assert len(conflict['choices']) == 2
    assert error.report() == fails('component-conflict', baseline(), [b, a]).report()


def test_explicit_compatibility_patch_resolves_without_rewriting_inputs():
    a, b = edit('alpha', stats={'health': 80}), edit('beta', stats={'health': 90})
    patch = edit('compat', stats={'health': 85})
    patch['requires'] = {'alpha': '1.0.0', 'beta': '1.0.0'}
    patch['overrides'][0]['supersedes'] = ['alpha', 'beta']
    result = registry.resolve(baseline(), [patch, b, a])
    assert result['fighters']['retail/donor']['components']['stats']['health'] == 85
    assert result['overrides']['retail/donor:stats'] == ['compat']


def test_same_value_claims_are_compatible():
    result = registry.resolve(baseline(), [edit('alpha', stats={'health': 80}), edit('beta', stats={'health': 80})])
    assert result['fighters']['retail/donor']['components']['stats']['health'] == 80


def test_skeleton_and_event_mismatch_across_distinct_components():
    a = edit('model', appearance='model/other')
    a['resources'] = [resource('other', 'appearance', skeleton='model/other-joints')]
    fails('skeleton-conflict', baseline(), [a])
    b = edit('voice', voice='voice/other')
    b['resources'] = [resource('other', 'voice', events='voice/other-events')]
    fails('event-conflict', baseline(), [b])


def test_dependency_version_identity_and_cycles():
    a = addition('alpha')
    a['requires'] = {'beta': '1.0.0'}
    fails('missing-dependency', baseline(), [a])
    b = addition('beta')
    b['version'] = '2.0.0'
    fails('dependency-version', baseline(), [a, b])
    b['version'] = '1.0.0'
    b['requires'] = {'alpha': '1.0.0'}
    fails('dependency-cycle', baseline(), [a, b])
    fails('duplicate-pack', baseline(), [addition(), addition()])
    fails('identity', baseline(), [pack('retail')])


def test_foreign_resources_require_explicit_dependency():
    a = edit('alpha', portrait='beta/portrait')
    b = pack('beta')
    b['resources'] = [resource('portrait', 'portrait')]
    fails('undeclared-dependency', baseline(), [a, b])
    a['requires'] = {'beta': '1.0.0'}
    assert registry.resolve(baseline(), [a, b])


def test_inheritance_copy_is_not_donor_override_alias():
    result = registry.resolve(baseline(), [addition(), edit('balance', stats={'health': 80})])
    assert result['fighters']['alpha/fighter-0']['components']['stats']['health'] == 60
    assert result['fighters']['retail/donor']['components']['stats']['health'] == 80


def test_inheritance_cycles_and_missing_targets():
    a = addition()
    a['fighters'][0]['inherits'] = 'alpha/fighter-0'
    fails('inheritance-cycle', baseline(), [a])
    a['fighters'][0]['inherits'] = 'retail/missing'
    fails('missing-fighter', baseline(), [a])


@pytest.mark.parametrize('mutation,code', [
    (lambda p: p.update(native_hooks=[]), 'schema'),
    (lambda p: p['fighters'][0].update(core_id=177), 'schema'),
    (lambda p: p['fighters'][0]['components'].update(code='arbitrary'), 'component'),
    (lambda p: p['fighters'][0]['components'].update(stats={'health': True}), 'stats'),
    (lambda p: p['fighters'][0]['components'].update(stats={'health': 101}), 'stats'),
    (lambda p: p['fighters'][0].update(id='../escape'), 'identity'),
    (lambda p: p['fighters'][0].update(name='bad\0name'), 'name'),
])
def test_strict_draft_contract(mutation, code):
    p = addition()
    mutation(p)
    fails(code, baseline(), [p])


def test_native_255_does_not_limit_logical_registry():
    p = pack('large')
    p['fighters'] = [{'id': f'fighter-{i}', 'name': f'Synthetic {i}', 'inherits': 'retail/donor', 'components': {}}
                     for i in range(300)]
    result = registry.resolve(baseline(), [p])
    assert len(result['fighters']) == 301
    assert 'large/fighter-257' in result['fighters']
    assert not result['runtime_ready']  # This is not proof of native high-ID playability.


def test_resource_kind_and_unknown_reference():
    p = edit('alpha', portrait='retail/moves')
    fails('resource-kind', baseline(), [p])
    p['overrides'][0]['components']['portrait'] = 'alpha/missing'
    fails('missing-resource', baseline(), [p])


CLI = Path(__file__).resolve().parents[2] / 'scripts/fighter-registry.py'


def run_cli(*paths):
    return subprocess.run([sys.executable, str(CLI), 'resolve-preview', *map(str, paths)],
                          capture_output=True, text=True, timeout=10)


def test_cli_deterministic_nested_output_and_actionable_conflict(tmp_path):
    base, first, second = [tmp_path / name for name in ('retail.json', 'alpha.json', 'beta.json')]
    base.write_text(json.dumps(baseline()), encoding='utf-8')
    first.write_text(json.dumps(addition()), encoding='utf-8')
    before = run_cli(base, first)
    assert before.returncode == 0, before.stdout + before.stderr
    # Reorder nested JSON object members without changing any values or arrays.
    def reverse(value):
        if isinstance(value, dict):
            return {k: reverse(v) for k, v in reversed(list(value.items()))}
        if isinstance(value, list):
            return [reverse(v) for v in value]
        return value
    base.write_text(json.dumps(reverse(baseline())), encoding='utf-8')
    first.write_text(json.dumps(reverse(addition())), encoding='utf-8')
    assert run_cli(base, first).stdout == before.stdout
    first.write_text(json.dumps(edit('alpha', stats={'health': 80})), encoding='utf-8')
    second.write_text(json.dumps(edit('beta', stats={'health': 90})), encoding='utf-8')
    a, b = run_cli(base, first, second), run_cli(base, second, first)
    assert a.returncode == b.returncode == 1
    assert a.stdout == b.stdout
    error = json.loads(a.stdout)['error']
    assert error['code'] == 'component-conflict'
    assert error['details']['conflicts'][0]['providers'] == ['alpha', 'beta']


@pytest.mark.parametrize('data', ['{"schema":1,"schema":2}', '{"value":NaN}', '{"value":Infinity}'])
def test_cli_rejects_ambiguous_and_nonfinite_json(tmp_path, data):
    path = tmp_path / 'bad.json'
    path.write_text(data, encoding='utf-8')
    result = run_cli(path)
    assert result.returncode == 1
    assert json.loads(result.stdout)['error']['code'] == 'input'
    assert not result.stderr


def test_cli_intake_budgets_precede_resolution(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('fighter_cli', CLI)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    missing = tmp_path / 'missing.json'
    with pytest.raises(ValueError, match='count exceeds'):
        cli.documents(missing, [missing] * (registry.MAX_PACKS + 1))
    path = tmp_path / 'small.json'
    path.write_bytes(b'{}')
    monkeypatch.setattr(cli, 'MAX_INPUT', 3)
    with pytest.raises(ValueError, match='budget'):
        cli.documents(path, [path])
    assert path.read_bytes() == b'{}'


def test_compatibility_helper_uses_explicit_choices_and_revalidates():
    base = baseline()
    packs = [edit('alpha', stats={'health': 80}), edit('beta', stats={'health': 90})]
    before = deepcopy(packs)
    result = registry.suggest_compatibility(base, packs, 'compat', {'retail/donor:stats': 'alpha'})
    assert result['patch']['requires'] == {'alpha': '1.0.0', 'beta': '1.0.0'}
    snapshot = registry.resolve(base, packs + [result['patch']])
    assert snapshot['fighters']['retail/donor']['components']['stats'] == {'health': 80, 'speed': 40}
    assert snapshot['sha256'] == result['preview_sha256']
    assert not result['runtime_ready']
    assert packs == before
    for choices in ({}, {'retail/donor:stats': 'missing'}, {'wrong': 'alpha'}):
        with pytest.raises(registry.RegistryError, match='Choose|Choice'):
            registry.suggest_compatibility(base, packs, 'compat', choices)
    with pytest.raises(registry.RegistryError, match='do not need'):
        registry.suggest_compatibility(base, [addition()], 'compat', {})
    with pytest.raises(registry.RegistryError, match='new identity'):
        registry.suggest_compatibility(base, packs, 'alpha', {'retail/donor:stats': 'alpha'})


def test_compatibility_helper_cannot_bypass_event_compatibility():
    a = edit('alpha', voice='alpha/new-voice')
    a['resources'] = [resource('new-voice', 'voice', events='alpha/new-events')]
    b = edit('beta', voice='retail/voice')
    with pytest.raises(registry.RegistryError) as caught:
        registry.suggest_compatibility(baseline(), [a, b], 'compat', {'retail/donor:voice': 'alpha'})
    assert caught.value.code == 'event-conflict'
    with pytest.raises(registry.RegistryError) as caught:
        registry.suggest_compatibility(baseline(), [1], 'compat', {})
    assert caught.value.code == 'schema'


def test_compatibility_helper_cli_prints_validated_draft(tmp_path):
    paths = [tmp_path / name for name in ('base.json', 'alpha.json', 'beta.json')]
    for path, value in zip(paths, [baseline(), edit('alpha', stats={'health': 80}),
                                 edit('beta', stats={'health': 90})]):
        path.write_text(json.dumps(value), encoding='utf-8')
    result = subprocess.run([sys.executable, str(CLI), 'suggest-compatibility', *map(str, paths),
                             '--id', 'compat', '--choose', 'retail/donor:stats=beta'],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    patch = json.loads(result.stdout)['patch']
    assert patch['overrides'][0]['components']['stats'] == {'health': 90}
