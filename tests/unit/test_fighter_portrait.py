"""UI names are scoped and authored bytes cannot replace native UI controls."""
import hashlib
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_assets import AssetError
from fighter_portrait import PortraitTextureTemplate, UITextures, Portrait, PortraitBaseline, variant_path, apply_portraits
from fighter_resource_files import PORTRAIT_PARTS, read_portrait
from fighter_archive import Archive, portrait_aliases, store
from fighter_assets import unpack
from fighter_xsh import Textures
from test_fighter_xsh import texture
from test_fighter_archive import fixture


def ui():
    data = bytearray(texture(kind=0x7d).replace(b'TEST', b'1   '))
    data[-12:-8] = b'1\0\0\0'
    return bytes(data)


def test_ui_template_replaces_only_pixels_and_keeps_model_names_strict():
    data = ui()
    with pytest.raises(AssetError, match='four portable'):
        Textures(data)
    template = PortraitTextureTemplate(data, hashlib.sha256(data).hexdigest())
    authored = bytearray(data)
    image, = UITextures(data).images
    start, size = image['pixels_offset'], image['pixels_bytes']
    authored[start:start + size] = b'\x19' * size
    authored[24:28] = b'EDIT'  # ignored directory padding is not copied
    result = template.compile(bytes(authored))
    assert result[start:start + size] == b'\x19' * size
    assert result[:start] == data[:start] and result[start + size:] == data[start + size:]
    assert not template.metadata()['runtime_ready']


def test_portrait_template_rejects_wrong_hash_names_dimensions_and_palettes():
    data = ui(); template = PortraitTextureTemplate(data, hashlib.sha256(data).hexdigest())
    with pytest.raises(AssetError, match='verified original'):
        PortraitTextureTemplate(data, '0' * 64)
    for name in (b'0   ', b'01  ', b'A001', b'  1 '):
        with pytest.raises(AssetError, match='canonical'):
            UITextures(data.replace(b'1   ', name))
    with pytest.raises(AssetError, match='tiles differ'):
        template.compile(data.replace(b'1   ', b'2   ').replace(b'1\0\0\0', b'2\0\0\0'))
    changed = bytearray(data); struct.pack_into('<HH', changed, 36, 2, 8)
    with pytest.raises(AssetError, match='dimensions differ'):
        template.compile(bytes(changed))
    changed = bytearray(data); changed[12:16] = b'EDIT'
    with pytest.raises(AssetError, match='crop/material controls'):
        template.compile(bytes(changed))
    palette = texture().replace(b'TEST', b'1   ')
    palette = palette[:-12] + b'1\0\0\0' + palette[-8:]
    with pytest.raises(AssetError, match='palette adapter'):
        PortraitTextureTemplate(palette, hashlib.sha256(palette).hexdigest())


def portrait_fixture(selection=1, donor='retail/test-alpha'):
    entries, files = {}, {}
    source = {'format': 'eagl-portrait-1', 'donor': donor}
    for part in PORTRAIT_PARTS:
        path, stem = variant_path(part, selection)
        entries[path] = store(fixture({stem + '.apt': b'original movie', stem + '.const': b'original constants',
                                      stem + '.o': b'original geometry', stem + '.xsh': ui()}))
        data = bytearray(ui()); image, = UITextures(bytes(data)).images
        start, size = image['pixels_offset'], image['pixels_bytes']
        data[start:start + size] = b'\x29' * size
        files[part] = store(bytes(data))
        source[part] = {'path': part + '.xsh', 'sha256': hashlib.sha256(files[part]).hexdigest()}
    entries['screens/trans/empty2.big'] = store(fixture({'empty2.apt': b'blank movie', 'empty2.const': b'blank constants'}))
    screens = fixture(entries)
    baseline = PortraitBaseline(screens, hashlib.sha256(screens).hexdigest())
    return source, files, baseline, screens


def test_portrait_six_variants_keep_original_ui_and_replace_only_owned_aliases():
    source, files, baseline, screens = portrait_fixture()
    portrait = Portrait('alpha/portrait', source, files, baseline, 1)
    assert len(portrait.files) == 6 and not portrait.summary['runtime_ready']
    aliased = portrait_aliases(screens, {100: 1}, results=True)
    receipts = {path: hashlib.sha256(data).hexdigest() for path, data in portrait.files.items()}
    result = Archive(apply_portraits(aliased, {100: ('alpha/portrait', receipts)}, portrait.files))
    original = Archive(screens)
    for part in PORTRAIT_PARTS:
        path, stem = variant_path(part, 100)
        inner = Archive(unpack(result.read(path)))
        assert inner.read(stem + '.apt') == b'original movie'
        assert inner.read(stem + '.o') == b'original geometry'
        assert inner.read(stem + '.xsh') == unpack(files[part])
        old, _ = variant_path(part, 1)
        assert result.read(old) == original.read(old)
    with pytest.raises(AssetError, match='owned selection alias'):
        apply_portraits(screens, {100: ('alpha/portrait', receipts)}, portrait.files)
    receipts[next(iter(receipts))] = '0' * 64
    with pytest.raises(AssetError, match='receipt differs'):
        apply_portraits(aliased, {100: ('alpha/portrait', receipts)}, portrait.files)


def test_portrait_files_hashes_budget_and_whole_pack_validation(tmp_path):
    from copy import deepcopy
    source, files, baseline, _ = portrait_fixture()
    for part, data in files.items():
        (tmp_path / source[part]['path']).write_bytes(data)
    assert read_portrait(tmp_path, source) == files
    with pytest.raises(AssetError, match='byte budget'):
        read_portrait(tmp_path, source, 1)
    with pytest.raises(AssetError, match='budget'):
        Portrait('alpha/portrait', source, files, baseline, 1, 1)
    changed = deepcopy(source); changed['selector_2p']['sha256'] = '0' * 64
    with pytest.raises(AssetError, match='hash mismatch'):
        read_portrait(tmp_path, changed)
    with pytest.raises(AssetError, match='hash changed'):
        Portrait('alpha/portrait', changed, files, baseline, 1)
    changed = deepcopy(source); changed['selector_2p']['path'] = '../escape'
    with pytest.raises(ValueError):
        read_portrait(tmp_path, changed)
    with pytest.raises(AssetError, match='six texture variants'):
        Portrait('alpha/portrait', source, {}, baseline, 1)


def test_matching_layouts_checks_every_variant_and_preserves_authored_pixels():
    _, files, baseline, _ = portrait_fixture()
    before = dict(files)
    candidates = {'retail/unavailable': 2, 'retail/test-alpha': 1, 'retail/same-layout': 1}
    assert baseline.matching_layouts(files, candidates) == ['retail/same-layout', 'retail/test-alpha']
    assert files == before
    changed = dict(files)
    data = bytearray(unpack(changed['result_4p'])); data[12:16] = b'EDIT'
    changed['result_4p'] = bytes(data)
    assert baseline.matching_layouts(changed, candidates) == []
    with pytest.raises(AssetError, match='six files'):
        baseline.matching_layouts({key: value for key, value in files.items() if key != 'result_4p'}, candidates)
    with pytest.raises(AssetError, match='bounded candidates'):
        baseline.matching_layouts(files, {'retail/bool': True})


def test_portrait_registry_and_native_binding_reject_wrong_donor_and_retail_override():
    from test_fighter_native import catalog, pack
    from fighter_registry import RegistryError
    source, files, baseline, _ = portrait_fixture()
    resource = Portrait('alpha/portrait', source, files, baseline, 1)
    native, _, _ = catalog()
    definition = pack()
    definition['resources'] = [{'id': 'portrait', 'kind': 'portrait', 'compatibility': {}, 'source': source}]
    definition['fighters'][0]['components']['portrait'] = 'alpha/portrait'
    _, report = native.compile([definition], portraits={'alpha/portrait': resource})
    assert report['portrait_bindings'] == {'alpha/fighter-0': 'alpha/portrait'}
    assert report['portrait_donors']['alpha/fighter-0'] == source['donor']
    with pytest.raises(RegistryError, match='native asset adapter'):
        native.compile([definition])
    resource.donor_selection = 2
    with pytest.raises(RegistryError, match='different donor layout'):
        native.compile([definition], portraits={'alpha/portrait': resource})
    resource.donor_selection = 1
    definition['fighters'] = []
    definition['overrides'] = [{'target': source['donor'], 'components': {'portrait': 'alpha/portrait'}, 'supersedes': []}]
    with pytest.raises(RegistryError, match='ownership adapter'):
        native.compile([definition], portraits={'alpha/portrait': resource})


def test_portrait_only_pack_full_compiler_cache_receipts_and_tampering(tmp_path, monkeypatch):
    import json
    from test_fighter_probe import driver
    from test_fighter_native import catalog, pack
    cli = driver(tmp_path, monkeypatch).registry
    source, files, _, screens = portrait_fixture()
    native, _, _ = catalog()
    monkeypatch.setattr(cli, 'retail_catalog', lambda path: native)
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/fighter-native-baseline.json').write_text(json.dumps({'screens_sha256': hashlib.sha256(screens).hexdigest()}))
    (tmp_path / 'game/screens').mkdir(parents=True)
    (tmp_path / 'game/screens/screens.viv').write_bytes(screens)
    manifests, packs = [], []
    for owner in ('alpha', 'beta'):
        root = tmp_path / owner; root.mkdir()
        for part, data in files.items():
            (root / source[part]['path']).write_bytes(data)
        definition = pack(owner)
        definition['resources'] = [{'id': 'portrait', 'kind': 'portrait', 'compatibility': {}, 'source': source}]
        definition['fighters'][0]['components']['portrait'] = owner + '/portrait'
        manifests.append(root / 'fighter.json'); packs.append(definition)
    data, report, resources = cli.compile_inputs(tmp_path / 'game/assets/djv2.sod', manifests, packs)
    assert len(resources) == 12 and len(report['portrait_resources']) == 2 and 'appearance_files' not in report
    assert (data, report, resources) == cli.compile_inputs(tmp_path / 'game/assets/djv2.sod', manifests[::-1], packs[::-1])
    cache = Path(cli.write_preview(data, report, resources))
    assert cli.write_preview(data, report, resources) == str(cache)
    with pytest.raises(ValueError, match='targets'):
        cli.write_preview(data, report, dict(resources, **{'../escape': b'bad'}))
    name = next(iter(resources))
    with pytest.raises(ValueError, match='receipt'):
        cli.write_preview(data, report, dict(resources, **{name: b'changed'}))
    (cache / name).write_bytes(b'changed')
    with pytest.raises(ValueError, match='cache is corrupt'):
        cli.write_preview(data, report, resources)
