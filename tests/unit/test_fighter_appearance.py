"""Two ordinary authored resource definitions through the native research compiler."""
from copy import deepcopy
import hashlib
import struct

import pytest

from test_fighter_archive import fixture as archive
from test_fighter_geometry import geometry_fixture
from test_fighter_xsh import texture
from test_fighter_native import catalog, pack
from fighter_appearance import Appearance, AppearanceBaseline, AssetError
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_elf import Model
from fighter_geometry import Geometry
from fighter_registry import RegistryError
from fighter_sod import Database


def fixture():
    model, start, sites = geometry_fixture(with_skin=True)
    model = bytes(model)
    xml = b'<tauntslist><taunt><name>SyntheticModel</name><intro>Intro</intro><extro>Victory</extro></taunt></tauntslist>'
    files = {'models': archive({'SyntheticModel.o': model, 'SyntheticModel.xsh': texture(), 'SyntheticModel_F.o': model}),
             'shared': archive({'assets/blingtex.xsh': texture()}),
             'entities': b'<entitylist><entity><name>SyntheticModel</name></entity></entitylist>',
             'cinematics': archive({'assets/IntroExtro.xml': xml}),
             'banks': archive({'Intro.viv': b'baseline', 'Victory.viv': b'baseline'})}
    pins = {pin: hashlib.sha256(files[name]).hexdigest() for name, pin in
            [('models', 'v2ip_sha256'), ('shared', 'blingfx_sha256'), ('entities', 'entities_sha256'),
             ('cinematics', 'nis_sha256'), ('banks', 'v2ta_sha256')]}
    pins['intro_extro_sha256'] = hashlib.sha256(xml).hexdigest()
    baseline = AppearanceBaseline(files, pins)
    # Actually authored vertex positions, distinct from the baseline geometry.
    changed = bytearray(model); struct.pack_into('<f', changed, start + sites['data0-0'], 2.)
    assets = {'model': bytes(changed), 'textures': texture(), 'face': model}
    source = {'format': 'eagl-appearance-1', 'donor': 'retail/test-alpha',
              **{part: {'path': part + '.bin', 'sha256': hashlib.sha256(data).hexdigest()} for part, data in assets.items()}}
    return baseline, source, assets, files


def authored(owner, source):
    p = pack(owner)
    p['resources'] = [{'id': 'body', 'kind': 'appearance',
                      'compatibility': {'skeleton': 'retail/binding-test-alpha'}, 'source': deepcopy(source)}]
    p['fighters'][0]['components']['appearance'] = owner + '/body'
    return p


def test_two_packs_compile_to_independent_names_without_replacing_retail_data():
    baseline, source, assets, originals = fixture()
    appearances = {owner + '/body': Appearance(owner + '/body', source, assets, baseline, 'SyntheticModel')
                   for owner in ('alpha', 'beta')}
    outputs = baseline.compose(appearances)
    assert outputs == baseline.compose(dict(reversed(list(appearances.items()))))
    models = Archive(outputs['assets/v2ip.viv'])
    for entry in baseline.models.entries:
        assert models.read(entry.name) == baseline.models.read(entry.name)
    for appearance in appearances.values():
        compiled = Model(unpack(models.read(appearance.name + '.o')))
        assert Geometry(compiled).meshes == Geometry(Model(assets['model'])).meshes
        assert appearance.summary['render_control_policy'] == 'verified-retail-template'
        assert appearance.name.encode() in outputs['assets/entity.xml']
        assert appearance.name.encode() in unpack(Archive(outputs['assets/nis.viv']).read('assets/IntroExtro.xml'))
    compiler, original, layout = catalog()
    packs = [authored(owner, source) for owner in ('alpha', 'beta')]
    output, report = compiler.compile(packs, appearances=appearances)
    assert (output, report) == compiler.compile(packs[::-1], appearances=appearances)
    assert not report['runtime_ready'] and len(report['appearance_resources']) == 2
    rows = {r['name']: r for r in Database(output).character_metadata()['characters']}
    for owner in ('alpha', 'beta'):
        name = report['bindings'][owner + '/fighter-0']['native_name']
        assert rows[name]['fields']['Model']['symbol'] == appearances[owner + '/body'].name
    for offset in layout['records']:
        assert output[offset:offset + 104] == original[offset:offset + 104]


def test_source_hashes_and_semantic_resource_bindings_cannot_be_substituted():
    baseline, source, assets, _ = fixture()
    with pytest.raises(AssetError, match='hash changed'):
        Appearance('alpha/body', source, dict(assets, model=b'changed'), baseline, 'SyntheticModel')
    appearance = Appearance('alpha/body', source, assets, baseline, 'SyntheticModel')
    compiler, _, _ = catalog()
    p = authored('alpha', source)
    p['resources'][0]['source']['model']['sha256'] = '0' * 64
    with pytest.raises(RegistryError, match='resolved source'):
        compiler.compile([p], appearances={'alpha/body': appearance})
    with pytest.raises(AssetError, match='different resource'):
        baseline.compose({'beta/body': appearance})


def test_untyped_face_data_is_rejected_even_when_it_is_a_valid_model():
    baseline, source, assets, _ = fixture()
    assets['face'] = assets['model']
    source['face']['sha256'] = hashlib.sha256(assets['face']).hexdigest()
    with pytest.raises(AssetError, match='facial palette'):
        Appearance('alpha/body', source, assets, baseline, 'SyntheticModel')


def test_aggregate_budget_is_checked_before_native_composition():
    baseline, source, assets, _ = fixture()
    with pytest.raises(AssetError, match='budget'):
        Appearance('alpha/body', source, assets, baseline, 'SyntheticModel', budget=100)


def test_composed_cache_requires_complete_receipts_and_rechecks_existing_bytes(tmp_path, monkeypatch):
    from test_fighter_probe import driver
    cli = driver(tmp_path, monkeypatch).registry
    baseline, source, assets, _ = fixture()
    appearances = {'alpha/body': Appearance('alpha/body', source, assets, baseline, 'SyntheticModel')}
    resources = baseline.compose(appearances)
    compiler, _, _ = catalog()
    data, report = compiler.compile([authored('alpha', source)], appearances=appearances)
    with pytest.raises(ValueError, match='complete composed files'):
        cli.write_preview(data, report)
    report['appearance_files'] = {path: hashlib.sha256(payload).hexdigest() for path, payload in resources.items()}
    with pytest.raises(ValueError, match='targets'):
        cli.write_preview(data, report, {'assets/v2ip.viv': resources['assets/v2ip.viv']})
    with pytest.raises(ValueError, match='receipt'):
        cli.write_preview(data, report, dict(resources, **{'assets/entity.xml': b'changed'}))
    from pathlib import Path
    cache = Path(cli.write_preview(data, report, resources))
    assert cli.write_preview(data, report, resources) == str(cache)
    (cache / 'assets/entity.xml').write_bytes(b'changed')
    with pytest.raises(ValueError, match='appearance cache is corrupt'):
        cli.write_preview(data, report, resources)


def test_compiler_rejects_missing_pack_paths_before_loading_sources(tmp_path, monkeypatch):
    from test_fighter_probe import driver
    cli = driver(tmp_path, monkeypatch).registry
    with pytest.raises(ValueError, match='exactly one source'):
        cli.compile_inputs(tmp_path / 'missing.sod', [], [pack()])


def test_opaque_texture_controls_cannot_enter_the_native_loader():
    baseline, source, assets, _ = fixture()
    changed = bytearray(assets['textures'])
    changed[40] = 1  # Unknown image-header control, outside validated dimensions.
    assets['textures'] = bytes(changed)
    source['textures']['sha256'] = hashlib.sha256(changed).hexdigest()
    with pytest.raises(AssetError, match='texture controls'):
        Appearance('alpha/body', source, assets, baseline, 'SyntheticModel')


def test_conflicting_texture_shapes_fail_before_composition():
    baseline, source, assets, _ = fixture()
    changed = bytearray(assets['textures']); changed[80] ^= 1  # Valid palette color.
    assets['textures'] = bytes(changed)
    source['textures']['sha256'] = hashlib.sha256(changed).hexdigest()
    appearance = Appearance('alpha/body', source, assets, baseline, 'SyntheticModel')
    with pytest.raises(AssetError, match='Texture shape TEST conflicts between retail and alpha/body'):
        baseline.compose({'alpha/body': appearance})
