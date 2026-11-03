"""Synthetic split data/link resources and bounded animation-name lists."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_animation import AnimationEnvelope
from fighter_assets import AssetError
from fighter_elf import ModelError
from test_fighter_elf import fixture


def animation_fixture():
    image, rows, _ = fixture('__AnimationBank:::a', 'metadata')
    image = bytearray(image)
    # Replace the fixture's import with a local data object, making both
    # relocations local. No implementation or native animation bytes are used.
    struct.pack_into('<IIIBBH', image, rows[4][4] + 32, len('__AnimationBank:::a') + 2, 12, 4, 17, 0, 1)
    split = rows[2][4]
    names = struct.pack('<2I', 2, 0) + b'N0001_A.N0001_B.'
    return bytes(image[:split]), bytes(image[split:]), names


def test_animation_envelope_retains_parts_and_separates_semantic_gates():
    data, links, names = animation_fixture()
    envelope = AnimationEnvelope(data, links, names)
    report = envelope.metadata()
    assert envelope.model.data == data + links
    assert report['bank_export'] == '__AnimationBank:::a'
    assert report['name_count'] == 2 and report['relocation_count'] == 2
    assert set(report['decoded_sha256']) == {'data', 'links', 'names'}
    assert not any(report[key] for key in ('runtime_ready', 'animation_records_validated',
                                           'motion_name_links_validated', 'event_links_validated'))


def test_individual_animation_pair_can_be_inspected_without_its_shared_name_list():
    data, links, _ = animation_fixture()
    report = AnimationEnvelope(data, links).metadata()
    assert report['name_count'] is None and set(report['decoded_sha256']) == {'data', 'links'}
    assert report['motion_name_links_validated'] is False and report['runtime_ready'] is False


@pytest.mark.parametrize('names', [b'', struct.pack('<2I', 0, 0), struct.pack('<2I', 65536, 0),
                                 struct.pack('<2I', 1, 1) + b'A.', struct.pack('<2I', 2, 0) + b'A.',
                                 struct.pack('<2I', 1, 0) + b'A', struct.pack('<2I', 1, 0) + b'.',
                                 struct.pack('<2I', 1, 0) + b'../', struct.pack('<2I', 1, 0) + b'A\0.',
                                 struct.pack('<2I', 1, 0) + b'A' * 128 + b'.'])
def test_animation_names_reject_counts_paths_and_unsupported_tokens(names):
    data, links, _ = animation_fixture()
    with pytest.raises(AssetError):
        AnimationEnvelope(data, links, names)


def test_animation_split_boundary_and_complete_link_file_are_required():
    data, links, names = animation_fixture()
    for wrong_data, wrong_links in ((data[:-1], data[-1:] + links), (data + links[:1], links[1:]),
                                    (data, links[:-1]), (data, links + b'X')):
        with pytest.raises((AssetError, ModelError)):
            AnimationEnvelope(wrong_data, wrong_links, names)
    with pytest.raises(AssetError, match='must be bytes'):
        AnimationEnvelope(bytearray(data), links, names)


def test_animation_envelope_requires_self_contained_data_and_a_bank_export():
    data, links, names = animation_fixture()
    original, rows, _ = fixture('__AnimationBank:::a', 'unknown-native-import')
    split = rows[2][4]
    with pytest.raises(ModelError, match='forbidden model imports'):
        AnimationEnvelope(original[:split], original[split:], names)
    with pytest.raises(AssetError, match='bank export'):
        AnimationEnvelope(data, links.replace(b'__AnimationBank:::a', b'__DifferentBank:::a'), names)
