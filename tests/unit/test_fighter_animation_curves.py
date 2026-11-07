"""Invented curve layouts: pointers, lengths and numerical trust boundaries."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_animation import AnimationIndex
from fighter_animation_curves import CurveLayouts
from fighter_assets import AssetError
from fighter_elf import ModelError
from test_fighter_animation import index_fixture


def curves(kind, mutate=None):
    def build(data, pointers):
        data.extend(bytes(256 - len(data)))
        data[240:248] = data[80:88]
        data[80:88] = bytes(8)
        struct.pack_into('<2I', data, 32, 240, 244)
        record = 160 if kind == 25 else 56
        struct.pack_into('<I', data, 52, record)
        struct.pack_into('<H', data, record, kind)
        if kind in (11, 13):
            if kind == 11:
                struct.pack_into('<IHH', data, 60, 100, 3, 4)
                pointers.append(60)
            else:
                struct.pack_into('<IIHH', data, 60, 100, 160, 3, 4)
                pointers.extend([60, 64])
            struct.pack_into('<HBB12f', data, 100, 4, 8, 0, *([0., 1., 0.] * 4))
            struct.pack_into('<2H', data, 160, 1, 2)
        elif kind == 25:
            struct.pack_into('<5I', data, 140, 0, 0, 25, 0, 0)
            struct.pack_into('<HBBII', data, 164, 2, 1, 0, 208, 220)
            pointers.extend([168, 172])
            data[208:210] = b'\x01\x03'
            struct.pack_into('<2H', data, 220, 0, 2)
        elif kind in (18, 19):
            struct.pack_into('<HBBII', data, 60, 3, 1, 1 if kind == 18 else 3, 208, 200)
            pointers.extend([64, 68])
            data[200] = 2
            struct.pack_into('<2H', data, 208, 1, 2)
            if kind == 18:
                data[72] = 3
                data[102] = 4  # after 18-byte header,16-byte descriptor,12 sample bytes
        else:
            struct.pack_into('<IIHH4B', data, 60, 200, 208, 3, 1, 3, 1, 0, 0)
            pointers.extend([60, 64])
            struct.pack_into('<H', data, 200, 8)
            struct.pack_into('<2H', data, 208, 1, 2)
            struct.pack_into('<H', data, 124 if kind == 20 else 92, 12)
        if mutate:
            mutate(data, pointers, record)
    return CurveLayouts(AnimationIndex(index_fixture(build)))


@pytest.mark.parametrize('kind, expected', [(11, 8), (13, 8), (20, 15), (21, 13)])
def test_numeric_curve_ranges_expose_output_requirements(kind, expected):
    parsed = curves(kind)
    assert parsed.records[56]['required_output_floats'] == expected
    assert parsed.metadata()['inspected_records'] == 1
    assert not parsed.metadata()['runtime_ready']
    assert not parsed.metadata()['numerical_decoder_validated']


def test_type11_supports_single_pose_and_inline_destinations_without_time_pointer():
    parsed = curves(11, lambda b,p,r: struct.pack_into('<H', b, r+8, 1))
    assert parsed.records[56]['keys'] == 1
    assert 64 not in parsed.model.pointers
    with pytest.raises((AssetError, ModelError), match='layout'):
        curves(11, lambda b,p,r: struct.pack_into('<H', b, r+8, 0))
    with pytest.raises((AssetError, ModelError), match='range'):
        curves(11, lambda b,p,r: struct.pack_into('<H', b, r+8, 65535))


def test_sample_bank_curve_requires_context_and_inert_dispatch_seed():
    parsed = curves(25)
    assert parsed.records[160] == {'kind': 25, 'keys': 2, 'sample_bank_selector': 1,
                                  'required_samples': 4, 'external_context_required': True}
    with pytest.raises(AssetError, match='inert'):
        curves(25, lambda b, p, r: struct.pack_into('<I', b, r - 20, 0x12345678))


@pytest.mark.parametrize('kind, expected', [(18, 224), (19, 128)])
def test_four_scalar_curves_use_element_stride_not_float_slot_destinations(kind, expected):
    record = curves(kind).records[56]
    assert record['required_output_bytes'] == expected
    assert 'required_output_floats' not in record


@pytest.mark.parametrize('target', [200, 256])
def test_empty_curve_array_can_keep_a_bounded_local_pointer(target):
    def change(data, pointers, record):
        data[record + 6] = data[record + 7] = 0
        struct.pack_into('<I', data, record + 12, target)
    parsed = curves(18, change)
    assert parsed.records[56]['channels'] == 0
    assert parsed.records[56]['required_output_bytes'] == 0


def test_empty_curve_array_cannot_smuggle_an_unrelocated_address():
    def change(data, pointers, record):
        data[record + 6] = data[record + 7] = 0
        pointers.remove(record + 12)
    with pytest.raises(AssetError, match='zero or a local'):
        curves(18, change)


@pytest.mark.parametrize('kind, mutate, message', [
    (18, lambda b,p,r: b.__setitem__(r+16, 255), 'shift'),
    (18, lambda b,p,r: b.__setitem__(r+17, 1), 'header control'),
    (19, lambda b,p,r: struct.pack_into('<H', b, r+28, 3), 'axis selector'),
    (19, lambda b,p,r: struct.pack_into('<H', b, r+4, 65535), 'range'),
])
def test_four_scalar_curves_reject_unbounded_controls(kind, mutate, message):
    with pytest.raises((AssetError, ModelError), match=message):
        curves(kind, mutate)


@pytest.mark.parametrize('kind, mutate, message', [
    (13, lambda b,p,r: struct.pack_into('<H', b, r+12, 65535), 'range'),
    (13, lambda b,p,r: struct.pack_into('<f', b, 104, float('nan')), 'non-finite'),
    (13, lambda b,p,r: struct.pack_into('<H', b, 100, 3), 'layout'),
    (20, lambda b,p,r: struct.pack_into('<f', b, r+20, float('inf')), 'non-finite'),
    (21, lambda b,p,r: b.__setitem__(r+16, 255), 'shift'),
    (25, lambda b,p,r: struct.pack_into('<H', b, r+4, 0), 'no keys'),
    (25, lambda b,p,r: struct.pack_into('<H', b, 222, 0), 'strictly increase'),
    (25, lambda b,p,r: p.remove(r+8), 'relocation'),
    (20, lambda b,p,r: struct.pack_into('<H', b, 210, 65535), 'wrap'),
])
def test_rejects_unsafe_lengths_numbers_and_time_arrays(kind, mutate, message):
    with pytest.raises((AssetError, ModelError), match=message):
        curves(kind, mutate)


def test_curve_cli_retains_separate_admission_gates(tmp_path, monkeypatch, capsys):
    import json
    import sys
    from test_fighter_probe import driver
    cli = driver(tmp_path, monkeypatch).registry
    model = curves(13).model
    split = model.sections[2][4]
    data, links = tmp_path / 'sample.ord', tmp_path / 'sample.orl'
    data.write_bytes(model.data[:split]); links.write_bytes(model.data[split:])
    monkeypatch.setattr(sys, 'argv', ['fighter-registry.py', 'inspect-animation-envelope',
                                    str(data), str(links), '--check-curves'])
    assert cli.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report['index_links']['named_entries'] == 2
    assert report['curve_layouts']['inspected_records'] == 1
    assert not report['curve_layouts']['output_context_validated']
    assert not report['runtime_ready']
