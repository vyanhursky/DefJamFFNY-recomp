"""Invented Team rasters verify independent states and immutable envelopes."""
import hashlib
from types import SimpleNamespace
import pytest
from PIL import Image
from test_fighter_ui_art import texture
from test_fighter_archive import fixture
from fighter_archive import Archive, store
from fighter_assets import unpack, AssetError
from fighter_portrait import UITextures, variant_path
from fighter_team_art import render, compile_movies


@pytest.fixture
def baseline(monkeypatch):
    import fighter_ui_model, fighter_caf_portrait
    monkeypatch.setattr(fighter_ui_model, 'UIModel', lambda *args: None)
    monkeypatch.setattr(fighter_caf_portrait, 'tiles', lambda model, tex: {int(t['name']): {
        'logical': (8, 8), 'image': t} for t in tex.images})
    entries = {}
    for part in ('team_icon', 'team_portrait'):
        path, stem = variant_path(part, 1)
        raw = texture() if part == 'team_portrait' else UITextures(texture()).appended({3: UITextures(texture(3))})
        entries[path] = store(fixture({stem + '.apt': b'original actions', stem + '.const': b'original constants',
                                      stem + '.o': b'original geometry', stem + '.xsh': raw}))
    return SimpleNamespace(archive=Archive(fixture(entries)))


def test_independent_team_states_preserve_native_envelope(baseline):
    images = {'team_portrait': Image.new('RGBA', (20, 40), 'blue'),
              'team_icon': Image.new('RGBA', (8, 8), 'red'),
              'team_icon_selected': Image.new('RGBA', (8, 8), 'green')}
    native, hd, receipt = render(images, baseline, 1, 4)
    assert set(native) == {'team_portrait', 'team_icon'} and len(hd) == 3
    assert [t['source'] for t in receipt['team_icon']['tiles']] == ['team_icon', 'team_icon_selected']
    files, _ = compile_movies('owned/team', native, baseline, 1)
    for part, raw in native.items():
        path, stem = variant_path(part, 1)
        original = Archive(unpack(baseline.archive.read(path)))
        assert UITextures(raw).controls == UITextures(original.read(stem + '.xsh')).controls
        compiled = Archive(unpack(next(data for path, data in files.items() if path.endswith('/' + part + '.big'))))
        for suffix in ('.apt', '.const', '.o'):
            assert compiled.read(__import__('fighter_resource_files').resource_name('owned/team') + '_' + part + suffix) == original.read(stem + suffix)


def test_optional_roles_and_selected_only_leave_normal_pixels(baseline):
    assert render({}, baseline, 1, 4) == ({}, {}, {})
    native, hd, receipt = render({'team_icon_selected': Image.new('RGBA', (8, 8), 'red')}, baseline, 1, 1)
    assert not hd and receipt['team_icon']['tiles'][0]['source'] == 'donor'
    path, stem = variant_path('team_icon', 1)
    original = UITextures(unpack(Archive(unpack(baseline.archive.read(path))).read(stem + '.xsh')))
    result = UITextures(native['team_icon'])
    tile = original.images[0]; at, size = tile['pixels_offset'], tile['pixels_bytes']
    assert original.data[at:at+size] == result.data[at:at+size]
    damaged = bytearray(native['team_icon']); damaged[0] ^= 1
    with pytest.raises(AssetError):
        compile_movies('owned/team', {'team_icon': bytes(damaged)}, baseline, 1)


def test_team_logical_dimensions_fill_the_full_sampled_raster(baseline, monkeypatch):
    import io
    import fighter_caf_portrait
    monkeypatch.setattr(fighter_caf_portrait, 'tiles', lambda model, tex: {int(t['name']): {
        'logical': (6, 5), 'image': t} for t in tex.images})
    native, hd, _ = render({'team_icon': Image.new('RGBA', (10, 10), 'red'),
                            'team_icon_selected': Image.new('RGBA', (10, 10), 'green')}, baseline, 1, 4)
    assert len(hd) == 2
    for raw in hd.values():
        image = Image.open(io.BytesIO(raw)).convert('RGBA')
        assert image.size == (32, 32) and image.getchannel('A').getextrema() == (255, 255)
