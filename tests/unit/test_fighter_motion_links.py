"""Index namespaces and the native WWAZ scan boundary are independent."""
import struct

import pytest

from test_fighter_motion import stream, table, chunk
from fighter_motion import MotionIndex
from fighter_motion_links import MotionLinks
from fighter_assets import AssetError
from fighter_motion_records import PackedRecord, MOVE_FIELDS


def fixture():
    parts = table() + table()
    parts[1] = chunk(b'FZUI', struct.pack('<2I', 39, 1000) + bytes(39000))
    data = bytearray(stream(parts, cores=1))
    index = MotionIndex(bytes(data))
    start = index.core_spans[0] + 72
    for row in range(130):
        struct.pack_into('<3H', data, start + row * 6, 0xffff, 1000, 0)
    struct.pack_into('<3H', data, start + 6, 0, 0, 10)
    struct.pack_into('<3H', data, start + 12, 1, 10, 30)
    return data, start


def test_primary_move_sentinel_and_flags_remain_separate():
    data, start = fixture()
    struct.pack_into('<H', data, start + 12, 0x8001)
    graph = MotionLinks(MotionIndex(bytes(data)))
    assert graph.action(0, 0).primary_move is None
    assert graph.action(0, 2).primary_move == 1
    assert graph.action(0, 2).flags == 0x8000
    assert not graph.metadata()['runtime_ready']
    for core, row in ((1, 0), (0, 130), (-1, 0), (False, 0)):
        with pytest.raises(AssetError): graph.action(core, row)


def test_native_scan_uses_previous_row_and_synthetic_terminal():
    data, start = fixture()
    graph = MotionLinks(MotionIndex(bytes(data)))
    assert graph.primary_parameter(0, 9) == 19
    assert graph.primary_parameter(0, 10) == 30
    assert graph.primary_parameter(0, 12, state=65, actor_flags=4, move_link=40) == 39
    # All actual later boundaries equal ten; row125's encoded word is ignored.
    for row in range(3, 125): struct.pack_into('<H', data, start + row * 6 + 2, 10)
    struct.pack_into('<H', data, start + 125 * 6 + 2, 11)
    graph = MotionLinks(MotionIndex(bytes(data)))
    assert graph.primary_parameter(0, 11) == 31
    with pytest.raises(AssetError, match='parameter table'): graph.primary_parameter(0, 999)
    with pytest.raises(AssetError, match='namespace'): graph.primary_parameter(0, 1000)


def test_external_tables_use_independent_counts():
    graph = MotionLinks(MotionIndex(stream()))
    assert graph.external_row('move', 10002) == 2
    with pytest.raises(AssetError, match='own table count'): graph.external_row('parameter', 10002)
    with pytest.raises(AssetError, match='prefix'): graph.external_row('move', 2)


def test_dangling_primary_edges_fail_before_native_use():
    data, start = fixture()
    struct.pack_into('<H', data, start, 3)
    with pytest.raises(AssetError, match='Core 0 action 0'): MotionLinks(MotionIndex(bytes(data)))
    index = MotionIndex(stream())
    row = index.record('move', 0)
    values = list(row.values)
    values[next(i for i, field in enumerate(MOVE_FIELDS) if field.offset == 0x3c)] = 3
    data = bytearray(index.data)
    at = index.move_spans[0][0]
    data[at:at + 32] = PackedRecord('move', tuple(values), row.tail).encode()
    with pytest.raises(AssetError, match='row 0 .3c'): MotionLinks(MotionIndex(bytes(data)))


def test_motion_cli_explicit_link_check(tmp_path, monkeypatch, capsys):
    import json
    import sys
    from test_fighter_probe import driver
    cli = driver(tmp_path, monkeypatch).registry
    data, start = fixture()
    path = tmp_path / 'motion.dat'
    path.write_bytes(data)
    monkeypatch.setattr(sys, 'argv', ['fighter-registry.py', 'inspect-motion-index', str(path), '--check-links'])
    assert cli.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report['index_links']['core_count'] == 1
    assert not report['index_links']['runtime_ready']
    struct.pack_into('<H', data, start, 3)
    path.write_bytes(data)
    assert cli.main() == 1
    assert 'Core 0 action 0' in json.loads(capsys.readouterr().out)['error']['message']
