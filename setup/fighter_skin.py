"""Bounds and numeric checks for the observed three-weight skin palettes.

Native op31 supplies 16-byte palette rows; op29 (118b00 -> 118e30) combines
three 64-byte bone matrices and uploads two constant ranges. This validates
that data relationship, not the imported shaders, bone-pose convention or
compatibility of an animation bank with an authored skeleton.
"""
from bisect import bisect_left
import math
import struct

from fighter_elf import Model, ModelError
from fighter_render import RenderProgram
from fighter_rig import Skeleton

ANIMATION_BUFFER = '__const MATRIX4:::EAGLAnimationBuffer'
PALETTE_ARGUMENTS = (0, 0xffffffa0, 56, 0xffffffdc, 104)
MAX_PALETTE_ROWS = 40


def require(condition, message):
    if not condition:
        raise ModelError(message)


def palette_rows(data, bone_count):
    require(isinstance(data, bytes) and len(data) % 16 == 0
            and 0 < len(data) <= MAX_PALETTE_ROWS * 16, 'Invalid skin palette span')
    require(type(bone_count) is int and 0 < bone_count <= 256, 'Unsupported skin bone count')
    rows = []
    for weights_and_index in struct.iter_unpack('<4f', data):
        weights, encoded = weights_and_index[:3], weights_and_index[3]
        require(all(math.isfinite(value) and 0 <= value <= 1 for value in weights)
                and abs(sum(weights) - 1) <= 0.001, 'Skin weights must be finite, nonnegative and normalized')
        # Native skips the third influence whenever the second has zero bits.
        # Reject holes and negative zero rather than treating them as equivalent.
        require(not any(value == 0 and math.copysign(1., value) < 0 for value in weights)
                and (weights[1] != 0 or weights[2] == 0), 'Skin influences have an unsupported zero/hole')
        require(math.isfinite(encoded) and encoded.is_integer() and 0 <= encoded < 2**31,
                'Skin bone encoding is not a bounded exact integer')
        packed = int(encoded)
        require(packed & 255 == 0, 'Skin bone encoding has unsupported low bits')
        bones = (packed >> 24, (packed >> 16) & 255, (packed >> 8) & 255)
        # The first matrix is read even if its weight is zero.
        used = 3 if weights[2] else 2 if weights[1] else 1
        require(all(bone < bone_count for bone in bones[:used]), 'Skin palette references a missing bone')
        rows.append({'weights': list(weights), 'bones': list(bones)})
    return rows


def palette_slot(value):
    """Map the reviewed signed-short constant selector to its uploaded row."""
    require(type(value) is int and value % 4 == 0, 'Invalid skin constant selector alignment')
    if -96 <= value <= -44:
        return (value + 96) // 4
    require(-36 <= value <= 64, 'Skin constant selector is outside the uploaded banks')
    return 14 + (value + 36) // 4


class Skin:
    def __init__(self, model):
        require(isinstance(model, Model), 'Skin requires a validated model envelope')
        skeleton = Skeleton(model)
        relocations = sorted(model.pointers)
        vertex_buffers = {model.export_offset(name) for name in model.exports if name.startswith('__VB:::')}

        def scalar(offset, size):
            at = model.data_range(offset, size)
            index = bisect_left(relocations, offset)
            require(index == len(relocations) or relocations[index] >= offset + size,
                    'Skin scalar data contains a pointer relocation')
            return model.data[at:at + size]

        resources = []
        for symbol in sorted(model.exports):
            if not symbol.startswith('__RM:::'):
                continue
            program = RenderProgram(model, model.export_offset(symbol))
            palettes, animations = program.matching(31), program.matching(29)
            if not palettes and not animations:
                continue
            require(len(palettes) == len(animations) == 1, 'Skin needs one palette and one matrix binding')
            palette, animation = palettes[0], animations[0]
            require(palette.arguments == (0,) and animation.arguments == PALETTE_ARGUMENTS,
                    'Unsupported skin palette program arguments')
            require(program.commands.index(palette) < program.commands.index(animation),
                    'Skin matrix binding precedes its palette')
            pointer = model.pointers[animation.parameter + 4]
            require(pointer['imported'] and pointer['symbol'] == ANIMATION_BUFFER,
                    'Skin matrix binding is not the engine animation buffer')
            count, = model.data_words(palette.parameter, 1)
            require(0 < count <= MAX_PALETTE_ROWS, 'Skin palette row budget')
            rows = palette_rows(scalar(model.local_pointer(palette.parameter + 4, count * 16), count * 16),
                                len(skeleton.rows))
            selectors = []
            for command in program.matching(9):
                if command.arguments[-1] != 2:
                    continue
                require(command.arguments[0] == 0, 'Unsupported skin stream instance selector')
                vertex_count, = model.data_words(command.parameter, 1)
                require(0 < vertex_count <= 1_000_000, 'Skin vertex selector budget')
                # 118030 subtracts20 from the parameter pointer to obtain the
                # exported VB header. Validate that relationship explicitly.
                inline = model.local_pointer(command.parameter + 4, vertex_count * 2)
                vb = inline - 20
                require(vb in vertex_buffers, 'Skin selector has no exported VB header')
                size, stride, flags = struct.unpack('<3I', scalar(vb + 4, 12))
                require(stride == 2 and flags == 1 and size in (vertex_count * 2, (vertex_count * 2 + 3) & ~3)
                        and model.local_pointer(vb + 16, size) == inline,
                        'Skin selector binding differs from its native VB header')
                slots = [palette_slot(value) for value, in struct.iter_unpack('<h', scalar(inline, vertex_count * 2))]
                require(all(slot < count for slot in slots), 'Skin selector exceeds the supplied palette')
                selectors.append({'stream': command.arguments[1], 'vertices': vertex_count,
                                  'used_palette_rows': sorted(set(slots))})
            require(len(selectors) == 1, 'Skin needs one reviewed short selector stream')
            resources.append({'resource': symbol, 'palette': rows, 'selectors': selectors})
        require(resources, 'Model has no supported skin resources')
        self.resources, self.skeleton = resources, skeleton

    def metadata(self):
        return {'format': 'fighter-skin-draft-1', 'bone_count': len(self.skeleton.rows),
                'resources': self.resources, 'palette_numeric_bounds_validated': True,
                'shader_execution_validated': False, 'animation_compatibility_validated': False,
                'runtime_ready': False}
