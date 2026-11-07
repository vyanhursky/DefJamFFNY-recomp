"""Synthetic split data/link resources and bounded animation-name lists."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_animation import AnimationEnvelope, AnimationIndex
from fighter_assets import AssetError
from fighter_elf import Model, ModelError
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


def test_complete_animation_repacking_preserves_data_graph_and_all_metadata():
    data, links, names = animation_fixture()
    original = Model(data + links)
    # Synthetic exporter variant: section table before string/symbol metadata,
    # with metadata sections in a different physical order.
    image = bytearray(data)
    table_at = len(image)
    image.extend(bytes(240))
    rows = list(original.sections)
    for index in (3, 2, 5, 4):
        row = list(rows[index]); image.extend(bytes(-len(image) % row[8]))
        row[4] = len(image)
        old = original.sections[index]
        image.extend(original.data[old[4]:old[4] + old[5]])
        rows[index] = tuple(row)
    struct.pack_into('<I', image, 32, table_at)
    image[table_at:table_at + 240] = b''.join(struct.pack('<10I', *r) for r in rows)
    variant = bytes(image)
    with pytest.raises(AssetError, match='boundary'):
        AnimationEnvelope(variant[:len(data)], variant[len(data):], names)
    envelope = AnimationEnvelope.from_model(variant, names)
    assert envelope.tokens == ('N0001_A', 'N0001_B')
    assert envelope.model.symbols == original.symbols
    assert envelope.model.pointers == original.pointers
    for before, after in zip(original.sections[1:], envelope.model.sections[1:]):
        assert original.data[before[4]:before[4] + before[5]] == envelope.model.data[after[4]:after[4] + after[5]]
    assert envelope.model.canonical_bytes() == envelope.model.data
    assert not envelope.metadata()['runtime_ready']


def test_complete_animation_repacking_keeps_import_and_executable_gates():
    image, rows, _ = fixture('__AnimationBank:::a', 'unknown-native-import')
    with pytest.raises(ModelError, match='forbidden model imports'):
        AnimationEnvelope.from_model(image)
    changed = bytearray(image)
    # Executable section flag must fail before any output normalization.
    sections = struct.unpack_from('<I', changed, 32)[0]
    struct.pack_into('<I', changed, sections + 40 + 8, 7)
    with pytest.raises(ModelError, match='executable'):
        AnimationEnvelope.from_model(bytes(changed))


def index_fixture(change=None):
    """Invented bank with two names sharing one parent and one opaque child."""
    original, rows, _ = fixture('__AnimationBank:::a')
    payload = bytearray(96)
    struct.pack_into('<6I', payload, 0, 0, 2, 0, 0, 24, 32)
    struct.pack_into('<4I', payload, 24, 40, 40, 80, 84)
    struct.pack_into('<HHIHHI', payload, 40, 15, 0, 0, 1, 0, 56)
    struct.pack_into('<H', payload, 56, 13)
    payload[80:88] = b'A_s\0A_t\0'
    pointers = [16, 20, 24, 28, 32, 36, 52]
    if change:
        change(payload, pointers)
    pieces = [b'', bytes(payload), original[rows[2][4]:rows[2][4] + rows[2][5]],
              b'\0__AnimationBank:::a\0', bytes(16) + struct.pack('<IIIBBH', 1, 0, 24, 17, 0, 1),
              b''.join(struct.pack('<II', at, 258) for at in pointers)]
    image = bytearray(original[:64])
    output_rows = [rows[0]]
    for i in range(1, 6):
        image += bytes(-len(image) % rows[i][8])
        output_rows.append((*rows[i][:4], len(image), len(pieces[i]), *rows[i][6:]))
        image += pieces[i]
    image += bytes(-len(image) % 4)
    struct.pack_into('<I', image, 32, len(image))
    image += b''.join(struct.pack('<10I', *row) for row in output_rows)
    split = output_rows[2][4]
    return AnimationEnvelope(bytes(image[:split]), bytes(image[split:]), struct.pack('<2I', 2, 0) + b'A.B.')


def test_animation_index_tracks_native_missing_sentinel_without_curve_admission():
    index = AnimationIndex(index_fixture())
    assert index.names == ['A_s', 'A_t']
    assert index.token_links == ((1, 0), (-1, -1))
    assert index.records == [40, 40]  # sharing is allowed
    assert index.children == {40: (56,)}
    report = index.metadata()
    assert report['record_types'] == {13: 1, 15: 1}
    assert report['missing_t_links'] == report['missing_s_links'] == 1
    assert not report['animation_records_validated'] and not report['runtime_ready']


@pytest.mark.parametrize('change, message', [
    (lambda b, p: struct.pack_into('<I', b, 4, 65536), 'count'),
    (lambda b, p: p.remove(16), 'relocation'),
    (lambda b, p: struct.pack_into('<I', b, 16, 92), 'range'),
    (lambda b, p: b.__setitem__(slice(80, 88), b'A_t\0A_s\0'), 'sorted'),
    (lambda b, p: struct.pack_into('<I', b, 36, 80), 'unique'),
    (lambda b, p: b.__setitem__(slice(80, 96), b'X' * 16), 'unterminated'),
    (lambda b, p: struct.pack_into('<H', b, 48, 100), 'range'),
    (lambda b, p: struct.pack_into('<I', b, 52, 40), 'Cyclic'),
])
def test_animation_index_rejects_malformed_reference_graph(change, message):
    with pytest.raises((AssetError, ModelError), match=message):
        AnimationIndex(index_fixture(change))
