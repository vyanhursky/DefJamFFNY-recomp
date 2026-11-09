"""Numeric skin palettes and selector-to-uploaded-bank bounds, no game assets."""
import math
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_elf import Model, ModelError
from fighter_skin import Skin, palette_rows, palette_slot
from test_fighter_geometry import geometry_fixture


def test_three_weight_palette_preserves_indices_and_rejects_unread_holes():
    row = palette_rows(struct.pack('<4f', .5, .25, .25, float((1 << 24) | (2 << 16) | (3 << 8))), 4)[0]
    assert row == {'weights': [.5, .25, .25], 'bones': [1, 2, 3]}
    assert palette_rows(struct.pack('<4f', 1., 0., 0., float(1 << 24)), 2)[0]['bones'][0] == 1


@pytest.mark.parametrize('row', [(math.nan, 0., 0., 0.), (math.inf, 0., 0., 0.),
    (-1., 1., 1., 0.), (.5, 0., 0., 0.), (.5, 0., .5, 0.), (1., -0., 0., 0.),
    (1., 0., 0., -1.), (1., 0., 0., .5), (1., 0., 0., math.inf), (1., 0., 0., 1.),
    (1., 0., 0., float(2 << 24)), (0., 1., 0., float(2 << 24)),
    (.5, .5, 0., float(2 << 16)), (.5, .25, .25, float(2 << 8))])
def test_palette_rejects_invalid_values_and_every_dereferenced_matrix(row):
    with pytest.raises(ModelError): palette_rows(struct.pack('<4f', *row), 2)


@pytest.mark.parametrize('selector,slot', [(-96, 0), (-44, 13), (-36, 14), (64, 39)])
def test_signed_selectors_have_two_explicit_upload_ranges(selector, slot):
    assert palette_slot(selector) == slot


@pytest.mark.parametrize('selector', [-100, -40, -95, 68, True, 0.0])
def test_unmapped_selector_and_gap_are_rejected(selector):
    with pytest.raises(ModelError): palette_slot(selector)


def test_full_skin_graph_checks_rig_palette_binding_and_vb_header():
    image, start, sites = geometry_fixture(with_skin=True)
    skin = Skin(Model(bytes(image)))
    assert len(skin.resources) == 1
    assert skin.resources[0]['selectors'] == [{'stream': 4, 'vertices': 4, 'used_palette_rows': [0, 1]}]
    assert skin.metadata()['palette_numeric_bounds_validated']
    assert not skin.metadata()['runtime_ready']
    struct.pack_into('<h', image, start + sites['data0-4'], -88)
    with pytest.raises(ModelError, match='exceeds the supplied palette'): Skin(Model(bytes(image)))


@pytest.mark.parametrize('site,offset,value', [('rm0', 0x4c, 41), ('vb0-4', 8, 4), ('vb0-4', 12, 0)])
def test_full_skin_graph_rejects_wrong_count_and_stream_layout(site, offset, value):
    image, start, sites = geometry_fixture(with_skin=True)
    struct.pack_into('<I', image, start + sites[site] + offset, value)
    with pytest.raises(ModelError): Skin(Model(bytes(image)))


def test_skin_rejects_pointer_relocation_in_scalar_vb_header():
    image, start, sites = geometry_fixture(with_skin=True)
    model = Model(bytes(image))
    # Move an existing relocation onto a header scalar. Its stored word is
    # still a valid in-bounds local target, so the ELF envelope alone accepts it.
    rel = model.sections[5]
    for at in range(rel[4], rel[4] + rel[5], 8):
        if struct.unpack_from('<I', image, at)[0] == sites['vb0-4']:
            struct.pack_into('<I', image, at, sites['vb0-4'] + 8)
            break
    else:
        pytest.fail('Fixture must have an explicit VB relocation')
    with pytest.raises(ModelError, match='scalar data contains a pointer'):
        Skin(Model(bytes(image)))


def test_skin_cli_exposes_validation_scope(tmp_path, monkeypatch, capsys):
    import json
    from test_fighter_probe import driver
    cli = driver(tmp_path, monkeypatch).registry
    image, _, _ = geometry_fixture(with_skin=True)
    path = tmp_path / 'skin.o'; path.write_bytes(image)
    monkeypatch.setattr(sys, 'argv', ['fighter-registry.py', 'inspect-skin', str(path)])
    assert cli.main() == 0
    report = json.loads(capsys.readouterr().out)['skin']
    assert report['palette_numeric_bounds_validated']
    assert not report['runtime_ready'] and not report['animation_compatibility_validated']
