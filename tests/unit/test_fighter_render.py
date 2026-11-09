"""Synthetic native RM instruction boundaries and independent parameter cursors."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_elf import Model, ModelError
from fighter_render import RenderProgram
from fighter_geometry import Geometry
from test_fighter_geometry import geometry_fixture


def test_program_uses_command_arity_and_independent_parameter_pairs():
    image, _, sites = geometry_fixture()
    program = RenderProgram(Model(bytes(image)), sites['rm0'])
    assert [c.opcode for c in program.commands] == [15, 15, 29, 2, 14, 26]
    assert program.matching(14)[0].parameter == sites['rm0'] + 0x5c
    assert program.commands[-1].parameter is None
    helper = RenderProgram(Model(bytes(image)), sites['rm1'])
    assert helper.matching(2)[0].parameter == sites['rm1'] + 0x4c  # two op1 skips
    point = RenderProgram(Model(bytes(image)), sites['rm2'])
    assert all(c.parameter is None for c in point.commands)  # op4 is not a skip
    assert not program.metadata()['runtime_ready']


@pytest.mark.parametrize('word', [0, 0xffff0002, 0xf0000, 0xf0002, 0xf0004, 0xffff])
def test_program_refuses_early_termination_unknown_or_bad_arity(word):
    image, start, sites = geometry_fixture()
    struct.pack_into('<I', image, start + sites['program0'], word)
    with pytest.raises(ModelError): RenderProgram(Model(bytes(image)), sites['rm0'])


def test_program_refuses_missing_terminator_and_out_of_bounds_parameters():
    image, start, sites = geometry_fixture()
    model = Model(bytes(image)); end = model.local_pointer(sites['rm0'] + 8, 4)
    struct.pack_into('<I', image, start + end - 4, 0x10001)
    with pytest.raises(ModelError): RenderProgram(Model(bytes(image)), sites['rm0'])
    image, start, sites = geometry_fixture()
    struct.pack_into('<I', image, start + sites['rm0'] + 8, sites['program0'])
    with pytest.raises(ModelError, match='bounds'): RenderProgram(Model(bytes(image)), sites['rm0'])


def test_explicitly_inherited_draw_count_is_not_guessed_from_next_pointer():
    image, start, sites = geometry_fixture()
    # Replace op2 and the second texture binding by one op1 each. Both skips
    # consume one pair, preserving op14's parameter without setting draw count.
    # This models state inheritance while retaining a bounded synthetic stream.
    commands = [(15, (80, 0)), (1, ()), (29, (0, -96, 56, -36, 104)),
                (1, ()), (14, (0,)), (26, (0, 5))]
    encoded = b''.join(struct.pack('<' + 'I' * (len(args) + 1), op << 16 | len(args) + 1,
                                  *(v & 0xffffffff for v in args)) for op, args in commands) + bytes(4)
    at = start + sites['program0']; image[at:at + len(encoded)] = encoded
    struct.pack_into('<I', image, start + sites['rm0'] + 8, sites['program0'] + len(encoded))
    geometry = Geometry(Model(bytes(image)))
    assert geometry.meshes[0]['draw_count_inherited'] and geometry.meshes[0]['index_count'] == 6
    assert not geometry.metadata()['runtime_ready']
