"""Resolved multi-pack behavior generation, using invented game-free originals."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path

import pytest

from test_fighter_native import catalog, pack
from test_fighter_geometry import geometry_fixture
from test_fighter_archive import fixture
from test_fighter_motion import stream, table
from test_fighter_ai import source as ai_source
from test_fighter_cinematic_compile import bundle
from fighter_behavior import BehaviorPlan, targets, environment
from fighter_registry import resolve
from fighter_assets import AssetError
from fighter_sod import Database


def setup(tmp_path, blazin=False, finishers=False, voice3=False, slots=False):
    compiler, original, layout = catalog(menu=True)
    model = bytes(geometry_fixture(with_skin=True)[0])
    xml = b'<tauntslist><taunt><name>SyntheticModel</name><intro>CI_0001</intro><extro>CE_0001</extro></taunt></tauntslist>'
    files = {
        'motion/main_all.dat': (stream(table(moves=200) + table(moves=200), cores=141), 'motion_sha256'),
        'assets/v2ip.viv': (fixture({'SyntheticModel.o': model}), 'v2ip_sha256'),
        'assets/entity.xml': (b'<entitylist/>', 'entities_sha256'),
        'assets/nis.viv': (fixture({'assets/IntroExtro.xml': xml}), 'nis_sha256'),
        'assets/v2ta.viv': (fixture({'CI_0001.viv': bundle(), 'CE_0001.viv': bundle('CE_0001')}), 'v2ta_sha256'),
        'assets/ai/ai.viv': (ai_source()[0], 'ai_sha256'),
    }
    pins = {'intro_extro_sha256': hashlib.sha256(xml).hexdigest()}
    if voice3:
        from test_fighter_voice_compile import explicit_source
        voice_compiler, voice = explicit_source()
        files['audio/speech2.viv'] = (voice_compiler.archive.data, 'speech_sha256')
    if blazin:
        from test_fighter_blazin_compile import bundle as activation, TOKENS
        from fighter_archive import Archive
        data, pin = files['assets/v2ta.viv']
        files['assets/v2ta.viv'] = (Archive(data).compose(additions={
            token + '.viv': activation(token, i) for i, token in enumerate(TOKENS)}), pin)
    if finishers:
        from test_fighter_blazin_pairs import original as paired_original
        files['motion/blazin.viv'] = (paired_original()[0], 'blazin_sha256')
    for name, (data, pin) in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        pins[pin] = hashlib.sha256(data).hexdigest()
    packs = [pack('alpha', count=2), pack('beta')]
    packs[0]['resources'].append({'id': 'brain', 'kind': 'ai', 'compatibility': {}, 'source': {
        'format': 'fighter-ai-1', 'template_profile': 'char0005',
        'tendencies': {d: {str(i): {'Attack_versus_Defend': 2} for i in range(4)} for d in ('easy', 'normal', 'hard')}}})
    packs[0]['fighters'][0]['components']['ai'] = 'alpha/brain'
    if voice3:
        from test_fighter_behavior_files import wav, descriptor
        audio = {**descriptor(tmp_path, 'voice.wav', wav()), 'format': 'wav-pcm16'}
        packs[0]['resources'].append({'id': 'speech', 'kind': 'voice',
            'compatibility': {'events': 'retail/binding-test-alpha'},
            'source': {'format': 'fighter-voice-3', 'banks': voice['banks'], 'intro': audio, 'extro': audio}})
        packs[0]['fighters'][0]['components']['voice'] = 'alpha/speech'
    if blazin:
        family = 'retail/binding-test-alpha'
        # The invented baseline uses this same event/rig family.
        packs[0]['resources'].append({'id': 'activation', 'kind': 'blazin',
            'compatibility': {'skeleton': family, 'events': family}, 'source': {
                'format': 'fighter-blazin-1', 'shots': [{'template': token} for token in TOKENS]}})
        for fighter in packs[0]['fighters']:
            fighter['components']['blazin'] = 'alpha/activation'
        if finishers:
            import json
            from fighter_rig import Skeleton
            from fighter_elf import Model
            rig = Skeleton(Model(model))
            payload = json.dumps({'schema': 'fighter-quaternions-1', 'rig_sha256': rig.pose_sha256,
                'bone_count': len(rig.rows), 'poses': [[list(row[4:8]) for row in rig.rows]] * 13}).encode()
            (tmp_path / 'finisher.json').write_bytes(payload)
            spec = {'path': 'finisher.json', 'sha256': hashlib.sha256(payload).hexdigest()}
            packs[0]['resources'][-1]['source']['pairs'] = {'0': {'subject': spec, 'counterpart': spec}}
            if slots:
                source = packs[0]['resources'][-1]['source']
                del source['pairs']
                source.update(format='fighter-blazin-2', slots={str(slot): {
                    'template_choice': 2, 'subject': spec, 'counterpart': spec} for slot in (0, 3)})
    snapshot = resolve(compiler.baseline(), packs)
    roots = {p['id']: tmp_path for p in packs}
    plan = BehaviorPlan(compiler, snapshot, roots, tmp_path, pins, {}, {})
    return compiler, original, layout, packs, snapshot, plan


def test_slot_pairs_and_motion_choices_compile_as_one_generation(tmp_path):
    import struct
    from fighter_motion import MotionIndex
    compiler, _, _, packs, _, plan = setup(tmp_path, blazin=True, finishers=True, slots=True)
    compiler.compile(packs, behavior=plan)
    assert plan.files['fighter-motion.bin'][:4] == b'FMC3'
    proof = plan.files['fighter-finishers.bin']
    assert proof[:4] == b'FBP2' and struct.unpack_from('<I', proof, 8) == (4,)
    rows = [struct.unpack_from('<4I', proof, 52 + 32*i) for i in range(4)]
    assert [(r[0],r[1],r[2]) for r in rows] == [(141,0,2),(141,3,2),(142,0,2),(142,3,2)]
    assert rows[0][3] != rows[1][3] and rows[0][3] == rows[2][3]
    index = MotionIndex(plan.files['motion/main_all.dat'])
    assert index.record('core', 141).values[88:92] == (2, 0, 0, 2)


def test_voice3_category_templates_compose_through_resolved_behavior_plan(tmp_path):
    compiler, _, _, packs, _, plan = setup(tmp_path, voice3=True)
    _, report = compiler.compile(packs, binding_window=True, behavior=plan)
    receipt = plan.receipts['voice']['bindings']['alpha/speech']
    assert receipt['template_voice'] is None
    assert receipt['categories']['Taunts']['template_voice'] == 23
    assert receipt['categories']['Character']['first_key'] == 1
    assert plan.voice_ids['alpha/speech'] == 600
    assert 'fighter-voices.bin' in plan.files


def test_owned_cores_are_per_fighter_and_every_binding_agrees(tmp_path):
    compiler, original, layout, packs, snapshot, plan = setup(tmp_path)
    data, report = compiler.compile(packs, binding_window=True, behavior=plan)
    assert plan.character_cores == {'alpha/fighter-0': 142, 'alpha/fighter-1': 143, 'beta/fighter-0': 144}
    assert len(plan.receipts['ai']['bindings']) == 1
    assert len(plan.receipts['cinematic_bindings']['bindings']) == 3
    assert len(plan.receipts['cinematic']['bindings']) == 2
    for key, core in plan.character_cores.items():
        row = report['bindings'][key]
        assert row['core_id'] == core
        assert Database(data).word(row['record_offset'] + 40) == core
        # Deferred logical rows are intentionally absent from the fixed native
        # index; the participant window owns their complete core binding.
        assert not report['handle_bindings'][key]['available']
        assert report['handle_bindings'][key]['core_id'] == 0
        assert next(r for r in report['window']['fighters'] if r['record_offset'] == row['record_offset'])['core_id'] == core
    for offset in layout['records']:
        assert data[offset:offset + 104] == original[offset:offset + 104]
    assert not report['runtime_ready'] and not report['launch_allowed']
    assert compiler.compile(packs[::-1], binding_window=True, behavior=plan) == (data, report)
    assert set(plan.files) == targets(plan.receipts)
    env = environment(tmp_path, report)
    assert env['RECOMP_FIGHTER_AI_SHA256'] == plan.file_hashes['assets/ai/ai.viv']
    assert env['RECOMP_FIGHTER_RESEARCH_CINEMATICS_SHA256'] == plan.file_hashes['assets/nis.viv']
    _, direct = compiler.compile(packs, behavior=plan)
    for key, core in plan.character_cores.items():
        assert direct['handle_bindings'][key]['available']
        assert direct['handle_bindings'][key]['core_id'] == core


def test_plan_cannot_cross_snapshots_or_change_after_validation(tmp_path):
    compiler, _, _, packs, snapshot, plan = setup(tmp_path)
    changed = deepcopy(packs)
    changed[0]['fighters'][0]['name'] = 'Changed'
    with pytest.raises(AssetError, match='different resolved'):
        compiler.compile(changed, behavior=plan)
    core = plan.character_cores['alpha/fighter-0']
    plan.character_cores['alpha/fighter-0'] += 1
    with pytest.raises(AssetError, match='bindings changed'):
        compiler.compile(packs, behavior=plan)
    plan.character_cores['alpha/fighter-0'] = core
    plan.files['fighter-motion.bin'] += b'changed'
    with pytest.raises(AssetError, match='changed after composition'):
        compiler.compile(packs, behavior=plan)


def test_activation_and_cinematics_share_final_archive_with_chained_receipts(tmp_path):
    import struct
    compiler, _, _, packs, _, plan = setup(tmp_path, blazin=True)
    _, report = compiler.compile(packs, behavior=plan)
    cinematic, blazin = plan.receipts['cinematic'], plan.receipts['blazin']
    assert cinematic['source_sha256'] == blazin['sha256']
    final = hashlib.sha256(plan.files['assets/v2ta.viv']).digest()
    assert plan.files['fighter-blazin.bin'][16:48] == final
    assert plan.files['fighter-cinematics.bin'][24:56] == final
    assert struct.unpack_from('<I', plan.files['fighter-blazin.bin'], 8)[0] == 2
    assert len(blazin['bindings']) == 1
    assert set(plan.files) == targets(plan.receipts)
    assert environment(tmp_path, report)['RECOMP_FIGHTER_BLAZIN_BINDINGS'].endswith('fighter-blazin.bin')


def test_preview_writes_exact_behavior_artifacts_and_rejects_corruption(tmp_path, monkeypatch):
    compiler, _, _, packs, _, plan = setup(tmp_path / 'game')
    data, report = compiler.compile(packs, binding_window=True, behavior=plan)
    path = Path(__file__).resolve().parents[2] / 'scripts/fighter-registry.py'
    spec = importlib.util.spec_from_file_location('behavior_cli', path)
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    destination = Path(cli.write_preview(data, report, plan.files))
    assert cli.write_preview(data, report, plan.files) == str(destination)
    for path, payload in plan.files.items():
        assert (destination / path).read_bytes() == payload
    with pytest.raises(ValueError, match='targets'):
        cli.write_preview(data, report, {**plan.files, 'arbitrary.exe': b'payload'})
    (destination / 'fighter-motion.bin').write_bytes(b'changed')
    with pytest.raises(ValueError, match='corrupt'):
        cli.write_preview(data, report, plan.files)


def test_finishing_moves_share_resources_but_bind_each_owned_core(tmp_path):
    import struct
    compiler, _, _, packs, _, plan = setup(tmp_path, blazin=True, finishers=True)
    _, report = compiler.compile(packs, behavior=plan)
    receipt = plan.receipts['finishers']
    assert len(receipt['bindings']) == 1 and receipt['motion_count'] == 166
    table = plan.files['fighter-finishers.bin']
    assert struct.unpack_from('<4I', table, 4)[1:3] == (2, 166)
    assert struct.unpack_from('<III', table, 52) == (141, 0, 873)
    assert struct.unpack_from('<III', table, 80) == (142, 0, 873)
    assert set(plan.files) == targets(plan.receipts)
    assert environment(tmp_path, report)['RECOMP_FIGHTER_FINISHERS_SHA256'] == receipt['sha256']
