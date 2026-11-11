"""Mixed CAF/owned compilation uses invented originals, never game or pack bytes."""
from copy import deepcopy
import hashlib
import json
import struct

import pytest

from test_fighter_native import catalog, pack
from test_fighter_appearance import fixture as appearance_fixture, authored
from test_fighter_behavior import setup as behavior_fixture
from fighter_archive import Archive
from fighter_build import compile_inputs, write_preview
from fighter_native import RetailCatalog, ADAPTER
from fighter_sod import Database, SodError


def caf_pack(owner='aaa-caf'):
    result = pack(owner)
    result['resources'] = [{'id': 'recipe', 'kind': 'caf', 'compatibility': {}, 'source': {
        'format': 'caf-fighter-1', 'selection': {'path': 'recipe.json', 'sha256': 'a' * 64}}}]
    result['fighters'][0]['components']['caf'] = owner + '/recipe'
    return result


def caf_item():
    return {'core': 87, 'audio_core': 5, 'sha256': 'b' * 64, 'recipe': {
        'stats': dict.fromkeys(('upper', 'lower', 'speed', 'toughness', 'health'), 10),
        'styles': [0], 'caf_values': [0] * 38, 'caf_colors': [0] * 38}}


def inputs(tmp_path, compiler, original, packs, monkeypatch):
    # CAF source admission has separate recipe/database/archive tests. Supply its
    # validated result here so this fixture can exercise the real mixed compiler.
    import fighter_caf
    monkeypatch.setattr(fighter_caf, 'load', lambda *args: deepcopy(caf_item()))
    image = bytearray(original)
    for i, row in enumerate(compiler.rows.values()):
        struct.pack_into('<I', image, row['record_offset'] + 40, 5 + i)
    original = bytes(image)
    compiler = RetailCatalog(original, hashlib.sha256(original).hexdigest())
    sod = tmp_path / 'assets/djv2.sod'
    sod.parent.mkdir(exist_ok=True)
    sod.write_bytes(original)
    pins = {'adapter': ADAPTER}
    from pathlib import Path
    baseline = json.loads((Path(__file__).resolve().parents[2] / 'config/fighter-native-baseline.json').read_text())
    for key, relative in {
        'v2ip_sha256': 'assets/v2ip.viv', 'blingfx_sha256': 'assets/blingfx.viv',
        'entities_sha256': 'assets/entity.xml', 'nis_sha256': 'assets/nis.viv',
        'v2ta_sha256': 'assets/v2ta.viv', 'motion_sha256': 'motion/main_all.dat',
        'ai_sha256': 'assets/ai/ai.viv', 'speech_sha256': 'audio/speech2.viv',
    }.items():
        path = tmp_path / relative
        pins[key] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else baseline[key]
    if (tmp_path / 'assets/nis.viv').exists():
        pins['intro_extro_sha256'] = hashlib.sha256(Archive((tmp_path / 'assets/nis.viv').read_bytes()).read('assets/IntroExtro.xml')).hexdigest()
    pin = tmp_path / 'pins.json'; pin.write_text(json.dumps(pins))
    paths = [tmp_path / (p['id'] + '.json') for p in packs]
    return compiler, sod, paths, pin, pins


@pytest.mark.parametrize('owner', ['aaa-caf', 'zzz-caf'])
def test_caf_and_independent_owned_appearance_compile_together(tmp_path, monkeypatch, owner):
    compiler, original, _ = catalog(menu=True)
    _, source, assets, originals = appearance_fixture()
    for name, relative in {'models': 'v2ip.viv', 'shared': 'blingfx.viv', 'entities': 'entity.xml',
                           'cinematics': 'nis.viv', 'banks': 'v2ta.viv'}.items():
        path = tmp_path / 'assets' / relative; path.parent.mkdir(exist_ok=True); path.write_bytes(originals[name])
    for part, data in assets.items():
        (tmp_path / source[part]['path']).write_bytes(data)
    packs = [caf_pack(owner), authored('owned', source)]
    compiler, sod, paths, pin, _ = inputs(tmp_path, compiler, original, packs, monkeypatch)
    data, report, resources = compile_inputs(sod, paths, packs, catalog=compiler, pin_path=pin, binding_window=True)
    assert report['bindings'][owner + '/fighter-0']['core_id'] == 87
    assert report['bindings']['owned/fighter-0']['core_id'] == 5
    assert set(report['appearance_resources']) == {'owned/body'}
    assert 'fighter-caf.bin' in resources
    assert compile_inputs(sod, list(reversed(paths)), list(reversed(packs)), catalog=compiler,
                          pin_path=pin, binding_window=True) == (data, report, resources)
    write_preview(data, report, resources, cache_root=tmp_path / 'cache')


@pytest.mark.parametrize('mode', ['direct', 'logical', 'window'])
@pytest.mark.parametrize('owner', ['aaa-caf', 'zzz-caf'])
def test_caf_and_owned_voice_ai_motion_have_disjoint_cores_and_sealed_cache(tmp_path, monkeypatch, mode, owner):
    compiler, original, _, packs, _, _ = behavior_fixture(tmp_path, voice3=True)
    packs.append(caf_pack(owner))
    compiler, sod, paths, pin, _ = inputs(tmp_path, compiler, original, packs, monkeypatch)
    options = {'logical_menu': mode == 'logical', 'binding_window': mode == 'window'}
    data, report, resources = compile_inputs(sod, paths, packs, catalog=compiler, pin_path=pin, **options)
    assert report['bindings'][owner + '/fighter-0']['core_id'] == 87
    assert all(report['bindings'][key]['core_id'] >= 142 for key in
               ('alpha/fighter-0', 'alpha/fighter-1', 'beta/fighter-0'))
    assert owner + '/fighter-0' not in report['behavior_receipts']['motion']['bindings']
    assert resources['fighter-caf.bin'][:4] == b'FCA1'
    if mode != 'logical':
        write_preview(data, report, resources, cache_root=tmp_path / 'cache')
    assert compile_inputs(sod, paths[::-1], packs[::-1], catalog=compiler, pin_path=pin, **options) == (data, report, resources)


def test_native_core_maps_partition_additions_without_weakening_coverage():
    compiler, original, _ = catalog()
    rows = list(compiler.rows.values())
    additions = [{'key': 'caf/one', 'template': rows[0]['record_offset'], 'fields': {}},
                 {'key': 'owned/two', 'template': rows[1]['record_offset'], 'fields': {}}]
    data, receipt = Database(original).extend_character_records(additions,
        character_cores={'owned/two': 142}, caf_cores={'caf/one': 87})
    assert receipt['bindings']['caf/one']['inherited_core_id'] == 87
    assert receipt['bindings']['owned/two']['inherited_core_id'] == 142
    for owned, caf in [({}, {'caf/one': 87}), ({'owned/two': 142}, {}),
                       ({'owned/two': 142, 'caf/one': 143}, {'caf/one': 87}),
                       ({'owned/two': 142}, {'extra/key': 87}),
                       ({'owned/two': 142}, {'caf/one': 0})]:
        with pytest.raises(SodError):
            Database(original).extend_character_records(additions, character_cores=owned, caf_cores=caf)
    # CAF v5 explicitly selects a retail core; indexed identity is still CAF.
    _, retail = Database(original).extend_character_records(additions,
        character_cores={'owned/two': 142}, caf_cores={'caf/one': 5})
    assert retail['bindings']['caf/one']['inherited_core_id'] == 5


@pytest.mark.parametrize('component', ['appearance', 'blazin'])  # voice, AI, intro and victory are optional CAF sections
def test_owned_components_remain_forbidden_on_the_caf_itself(tmp_path, monkeypatch, component):
    compiler, original, _, packs, _, _ = behavior_fixture(tmp_path, voice3=True, blazin=True)
    caf = caf_pack()
    if component == 'appearance':
        _, spec, _, _ = appearance_fixture()
        body_pack = authored('body', spec); packs.append(body_pack)
        resource = 'body/body'
    else:
        resource = packs[0]['fighters'][0]['components'][component]
    caf['fighters'][0]['components'][component] = resource
    caf['requires'][resource.split('/')[0]] = '1.0.0'
    packs.append(caf)
    compiler, sod, paths, pin, _ = inputs(tmp_path, compiler, original, packs, monkeypatch)
    with pytest.raises(ValueError, match='CAF recipes currently support retail behavior'):
        compile_inputs(sod, paths, packs, catalog=compiler, pin_path=pin, binding_window=True)


def test_caf_graph_contexts_use_pinned_native_templates_and_palettes(tmp_path, monkeypatch):
    import fighter_caf
    from test_fighter_archive import fixture
    from test_fighter_animation_graphs import palettes, motion
    from test_fighter_rig import rig_fixture
    from fighter_motion_contexts import MotionOutputContexts
    from fighter_assets import AssetError
    model, start, _, _ = rig_fixture()
    other = bytearray(model); struct.pack_into('<f', other, start + 32, 10.)
    face = palettes().model.data
    blob = fixture({'V2CP_Template_Norm.o': bytes(model), 'V2CP_Template_Long.o': bytes(other),
                    'V2CP_532_0001_C_F.o': face, 'V2CP_532_0002_C_F.o': face})
    target = tmp_path / 'assets/v2cp_0.viv'; target.parent.mkdir(); target.write_bytes(blob)
    monkeypatch.setattr(fighter_caf, 'baseline_pins', lambda: {'archives': {'v2cp_0.viv': hashlib.sha256(blob).hexdigest()}})
    contexts = fighter_caf.output_contexts(tmp_path)
    assert len(contexts) == 4
    hands = palettes(); library = MotionOutputContexts(hands, hashlib.sha256(hands.model.data).hexdigest())
    for key, (body, palette) in contexts.items():
        library.add(key, body, palette, model_sha256=hashlib.sha256(body).hexdigest(), face_sha256=hashlib.sha256(palette).hexdigest())
    origin = 'caf-context/template-norm-face-1'
    value = motion(); value['rig_sha256'] = library.contexts[origin][0].pose_sha256
    receipt = library.join(value, origin, list(contexts))
    assert len({r['rig_sha256'] for r in receipt['targets'].values()}) == 2
    assert all(r['face_frames'] == list(hands.frame_counts) for r in receipt['targets'].values())
    target.write_bytes(blob + b'changed')
    with pytest.raises(AssetError, match='supported original'):
        fighter_caf.output_contexts(tmp_path)
