"""Game-free fixtures for motion table boundaries, counts and native partitions."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
import fighter_motion as motion
from fighter_assets import AssetError


def chunk(tag, data):
    return tag + struct.pack('<I', len(data)) + data


def table(*, grouped=2, moves=3, name=b'SYNTHETIC\0', offset=0, padding=b'\0'):
    return [chunk(b'WAZA', struct.pack('<4I', 32, moves, 1, grouped) + bytes(moves * 32)),
            chunk(b'FZUI', struct.pack('<2I', 39, 1) + bytes(39) + padding),
            chunk(b'NAME', struct.pack('<IH', 1, offset) + name)]


def stream(parts=None, cores=2):
    return b''.join((parts if parts is not None else table() + table()) +
                    [piece for _ in range(cores) for piece in (chunk(b'WPAR', bytes(64)), chunk(b'WWAZ', bytes(780)))])


def test_motion_partitions_keep_independent_names_groups_and_core_counts():
    index = motion.MotionIndex(stream())
    report = index.metadata()
    assert report['core_count'] == 2 and [row['ordinal'] for row in report['cores']] == [1, 2]
    assert report['tables'][0]['move_count'] == 3
    assert report['tables'][0]['group_populations'] == [2]
    assert report['tables'][0]['ungrouped_move_count'] == 1
    assert report['tables'][0]['name_count'] == 1
    assert report['tables'][0]['parameter_count'] == 1
    assert not any(report[field] for field in ('runtime_ready', 'move_records_validated', 'animation_links_validated'))


@pytest.mark.parametrize('parts', [table(grouped=4), table(name=b'UNTERMINATED'), table(offset=1),
                                 table(offset=65535), table(name=b'BAD\nNAME\0'), table(padding=b'X'),
                                 table(padding=b''), table(name=b'A' * 1025 + b'\0')])
def test_motion_rejects_bad_group_string_and_padding_spans(parts):
    with pytest.raises(AssetError):
        motion.MotionIndex(stream(parts + table()))


@pytest.mark.parametrize('data', [b'', b'WAZA', stream()[:-1], stream() + b'X', stream(cores=0),
                                stream().replace(b'WWAZ', b'NOPE', 1)])
def test_motion_requires_complete_ordered_tables_and_pairs(data):
    with pytest.raises(AssetError):
        motion.MotionIndex(data)


@pytest.mark.parametrize('at,value', [(4, 0xffffffff), (8, 31), (12, 65536), (16, 4097), (16, 0)])
def test_motion_refuses_unsupported_stride_counts_and_chunk_overflow(at, value):
    data = bytearray(stream()); struct.pack_into('<I', data, at, value)
    with pytest.raises(AssetError):
        motion.MotionIndex(bytes(data))


def test_motion_name_offsets_can_share_an_empty_name_but_not_enter_a_string():
    parts = table()
    parts[2] = chunk(b'NAME', struct.pack('<I3H', 3, 0, 2, 2) + b'A\0\0')
    assert motion.MotionIndex(stream(parts + table())).metadata()['tables'][0]['name_count'] == 3


def test_motion_core_budget_and_pair_sizes_are_enforced(monkeypatch):
    monkeypatch.setattr(motion, 'MAX_CORES', 1)
    with pytest.raises(AssetError, match='population'):
        motion.MotionIndex(stream())
    for pair in ([chunk(b'WPAR', bytes(60)), chunk(b'WWAZ', bytes(780))],
                 [chunk(b'WPAR', bytes(64)), chunk(b'WWAZ', bytes(776))]):
        with pytest.raises(AssetError, match='pair dimensions'):
            motion.MotionIndex(stream(table() + table() + pair, cores=0))
