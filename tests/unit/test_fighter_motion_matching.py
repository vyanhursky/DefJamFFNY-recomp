"""Exact inherited behavior matching cannot conceal other global edits."""
import struct

import pytest

from test_fighter_motion import chunk, table, stream
from fighter_assets import AssetError
from fighter_motion import MotionIndex
from fighter_motion_matching import match_finishers, chunks


def fixture():
    moves = [bytes(32) for _ in range(256)]
    parameters = [bytes(39) for _ in range(873)]
    for choice in range(82):
        moves[142 + choice] = bytes([choice + 1]) + bytes(31)
        for role in range(2):
            parameters[709 + 2 * choice + role] = bytes([2 * choice + role + 1]) + bytes(38)
    def index(m, p):
        secondary = [chunk(b'WAZA', struct.pack('<4I', 32, len(m), 1, 224) + b''.join(m)),
                     chunk(b'FZUI', struct.pack('<2I', 39, len(p)) + b''.join(p) + bytes(-(8 + 39 * len(p)) % 4)),
                     table()[2]]
        return MotionIndex(stream(table() + secondary))
    retail = index(moves, parameters)
    for choice, template in ((82, 11), (83, 79)):
        moves[142 + choice] = moves[142 + template]
        parameters.extend(parameters[709 + 2 * template:711 + 2 * template])
    return retail, index(moves, parameters)


def test_exact_unique_pairs_account_for_padding_replacement_and_appended_role_rows():
    retail, source = fixture()
    report = match_finishers(retail, source, [83, 82])
    assert report['mapping'] == {'82': 11, '83': 79}
    assert report['shared_unaccounted_bytes'] == 0 and report['packed_and_native_equal']
    assert report['shared_prefix_bytes'] == chunks(source)[1]
    assert not report['animation_conversion'] and not report['per_core_records_accounted']


@pytest.mark.parametrize('kind', ['packed-tail', 'primary', 'unclaimed-secondary', 'groups', 'name'])
def test_unaccounted_global_or_tail_changes_fail(kind):
    retail, source = fixture()
    data = bytearray(source.data)
    if kind == 'packed-tail':
        # Tail bits are absent from decoded native storage but still matter.
        data[source.move_spans[1][0] + 224 * 32 + 31] ^= 1
    elif kind == 'primary':
        data[source.move_spans[0][0]] ^= 1
    elif kind == 'unclaimed-secondary':
        data[source.move_spans[1][0] + 40 * 32] ^= 1
    elif kind == 'groups':
        struct.pack_into('<I', data, source.move_spans[1][0] - 4, 223)
    else:
        position = data.index(b'SYNTHETIC')
        data[position] = ord('A')
    with pytest.raises(AssetError, match='match|unaccounted'):
        match_finishers(retail, MotionIndex(bytes(data)), [82, 83])


def test_ambiguous_template_match_is_an_error_instead_of_an_arbitrary_choice():
    retail, source = fixture()
    data = bytearray(retail.data)
    m, p = retail.move_spans[1][0], retail.parameter_spans[1][0]
    data[m + 154 * 32:m + 155 * 32] = data[m + 153 * 32:m + 154 * 32]
    data[p + 733 * 39:p + 735 * 39] = data[p + 731 * 39:p + 733 * 39]
    with pytest.raises(AssetError, match='exactly one'):
        match_finishers(MotionIndex(bytes(data)), source, [82, 83])
