"""Synthetic action streams; no game movie bytes are fixtures."""
import importlib.util
from pathlib import Path
import struct

spec = importlib.util.spec_from_file_location('apt_dump', Path(__file__).resolve().parents[2] / 'scripts/apt-dump.py')
apt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apt)


def test_function_end_does_not_truncate_parent_timeline():
    # DefineFunction with no parameters and one-byte End body, then PrevFrame,
    # and the parent's End. Its empty name lives after the action stream.
    data = b'\x9b\0\0\0' + struct.pack('<4I', 31, 0, 0, 1) + bytes(8) + b'\0\x05\0\0'
    instructions = apt.disassemble_block(data, 0, [])
    assert [instruction.name for instruction in instructions] == ['DefineFunction', 'End', 'PrevFrame', 'End']
    assert instructions[0].function_size == 1
    assert [instruction.offset for instruction in instructions] == [0, 28, 29, 30]


def test_invalid_function_size_does_not_walk_adjacent_payload():
    data = b'\x9b\0\0\0' + struct.pack('<4I', 31, 0, 0, 1000) + bytes(8) + b'\0\x05\0\0'
    instructions = apt.disassemble_block(data, 0, [])
    assert len(instructions) == 1
    assert 'exceeds block bounds' in instructions[0].note


def test_pushlong_is_an_unaligned_four_byte_unsigned_operand():
    data = b'\x04\xb7' + struct.pack('<I', 0x9c0b0e) + b'\x1d\0'
    instructions = apt.disassemble_block(data, 0, [])
    assert [instruction.name for instruction in instructions] == ['NextFrame', 'EA_PushLong', 'SetVariable', 'End']
    assert instructions[1].operands == ['value=10226446']
    assert instructions[2].offset == 6
