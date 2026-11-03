"""Typed bounds checks for observed model surfaces and material associations.

This is not a render-command interpreter or a skinning validator. Imported
render methods and shaders still need an independently verified runtime adapter.
No native resource capability follows from passing these data-structure checks.
"""
from bisect import bisect_left
import math
import re
import struct

from fighter_elf import Model, ModelError, MAX_STRING

MAX_GROUPS = 256
MAX_MESHES = 4096
MAX_VERTICES = 1_000_000
MAX_INDICES = 3_000_000
ANIMATION_BUFFER = '__const MATRIX4:::EAGLAnimationBuffer'


def require(condition, message):
    if not condition:
        raise ModelError(message)


class Geometry:
    def __init__(self, model):
        require(isinstance(model, Model), 'Geometry requires a validated model envelope')
        self.model = model
        self.relocations = sorted(model.pointers)
        roots = [name for name in model.exports if name.startswith('__Model:::')]
        require(len(roots) == 1, 'Geometry requires exactly one inline model')
        self.name = roots[0].removeprefix('__Model:::')
        root = model.export_offset(roots[0])
        model.data_range(root, 0xd0)
        self.floats(root + 0x0c, 16)
        require(self.text(model.local_pointer(root + 0xb4, 1)) == self.name,
                'Inline model name differs from its export')
        count = self.word(root + 0x9c)
        require(0 < count <= MAX_GROUPS, 'Model material group budget')
        material_names = model.local_pointer(root + 0xa0, count * 4)
        names = [self.text(model.local_pointer(material_names + i * 4, 1)) for i in range(count)]

        rms, streams = {}, {}
        rm_pattern = re.compile(r'__RM:::__GP_RM_' + re.escape(self.name) + r'_(0|[1-9][0-9]*)')
        vb_pattern = re.compile(r'__VB:::__GPvb_(0|[1-9][0-9]*)_(0|[1-9][0-9]*)_' + re.escape(self.name))
        for name in sorted(model.exports):
            if name.startswith('__RM:::'):
                match = rm_pattern.fullmatch(name)
                require(match is not None, 'Unsupported model render-resource name')
                rms[int(match[1])] = model.export_offset(name)
            elif name.startswith('__VB:::'):
                match = vb_pattern.fullmatch(name)
                require(match is not None and int(match[1]) < 32, 'Unsupported model vertex-stream name')
                streams.setdefault(int(match[2]), []).append((int(match[1]), model.export_offset(name)))
        require(0 < len(rms) <= MAX_MESHES and set(rms) == set(range(len(rms)))
                and set(streams) == set(rms), 'Model render resources/streams do not form one bounded set')

        group = model.local_pointer(root + 0xcc, 4)
        require(self.word(group) == 0, 'Unsupported model material group header')
        cursor, used, groups = group + 4, set(), []
        reverse = {offset: index for index, offset in rms.items()}
        require(len(reverse) == len(rms), 'Aliased model render exports')
        for name in names:
            population = self.word(cursor); cursor += 4
            require(0 < population <= len(rms) - len(used), 'Invalid material render-resource population')
            model.data_range(cursor, population * 4)
            members = []
            for i in range(population):
                wrapper = model.local_pointer(cursor + i * 4, 4)
                rm = model.local_pointer(wrapper, 4)
                require(rm in reverse and wrapper == rm + 0x38 and rm not in used,
                        'Material wrapper does not uniquely reference an exported render resource')
                members.append(reverse[rm]); used.add(rm)
            cursor += population * 4
            groups.append({'name': name, 'render_resources': members})
        require(used == set(reverse), 'Material groups omit render resources')
        self.groups = groups

        meshes, total_vertices, total_indices = [], 0, 0
        for index, rm in sorted(rms.items()):
            buffers = [self.vertex_buffer(offset) for _, offset in sorted(streams[index])]
            strides = tuple(row['stride'] for row in buffers)
            require(strides in ((12, 8, 4, 4, 2), (12, 4, 4), (12, 2, 4, 4)),
                    'Unsupported model vertex-stream layout')
            parent = model.pointers.get(rm + 0x1c, {})
            require(parent.get('imported') and parent == model.pointers.get(rm + 0x2c),
                    'Model render resource has inconsistent parent bindings')
            if strides == (12, 2, 4, 4):
                require(parent['symbol'] == 'ParentRM_DJFXSparkle_Skin', 'Point streams need the reviewed sparkle parent')
            elif strides == (12, 4, 4):
                require(parent['symbol'] == 'ParentRM_LitGouraud', 'Helper streams need the reviewed untextured parent')
            vertices = buffers[0]['count']
            total_vertices += vertices
            require(total_vertices <= MAX_VERTICES, 'Model vertex budget')
            for i, buffer in enumerate(buffers):
                if buffer['stride'] == 2:
                    require(buffer['bytes'] in (vertices * 2, (vertices * 2 + 3) & ~3),
                            f'Short stream differs from its position count in render resource {index}')
                else:
                    require(buffer['count'] == vertices, f'Model vertex streams differ in count in render resource {index}')
            bounds = self.position_bounds(buffers[0])
            if strides == (12, 8, 4, 4, 2):
                self.floats(buffers[1]['data'], vertices * 2)
            point = strides == (12, 2, 4, 4)
            indices, triangles = 0, 0
            if not point:
                if strides == (12, 4, 4):
                    field = rm + 0x50
                else:
                    candidates = [offset for offset in range(rm + 0x40, rm + 0x80, 4)
                                  if model.pointers.get(offset, {}).get('symbol') == ANIMATION_BUFFER
                                  and model.pointers[offset]['imported']]
                    require(len(candidates) == 1, 'Surface index layout needs one animation-buffer binding')
                    field = candidates[0] + 8
                indices = self.word(field + 4)
                require(3 <= indices <= MAX_INDICES - total_indices, 'Model index budget')
                total_indices += indices
                header = model.local_pointer(field, 16)
                require(self.words(header, 4) == (indices, 0, 0, 0), f'Unsupported model index header in render resource {index}')
                data = model.local_pointer(field + 8, indices * 2)
                at = self.scalars(data, indices * 2)
                previous = []
                for item, in struct.iter_unpack('<H', model.data[at:at + indices * 2]):
                    require(item < vertices, 'Model index exceeds its vertex stream')
                    if len(previous) == 2:
                        triangles += len({*previous, item}) == 3
                        previous.pop(0)
                    previous.append(item)
            meshes.append({'index': index, 'kind': 'points' if point else 'triangle-strip',
                           'vertex_count': vertices, 'strides': list(strides), 'index_count': indices,
                           'nondegenerate_triangles': triangles, 'bounds': bounds})
        self.meshes = meshes
        shapes, external = set(), set()
        for name in model.imports:
            if not name.startswith('__EAGL::TAR:::'):
                continue
            if not name.startswith('__EAGL::TAR:::RUNTIME_ALLOC::'):
                require(re.fullmatch(r'__EAGL::TAR:::[A-Za-z0-9_]{1,64}', name),
                        'Unsupported external texture binding name')
                external.add(name)
                continue
            matches = re.findall(r'(?:^|;)SHAPENAME=([A-Za-z0-9_]{4}),1;', name)
            require(len(matches) == 1, 'Unsupported model texture shape binding')
            shapes.update(matches)
        self.texture_shapes = sorted(shapes)
        self.external_texture_bindings = sorted(external)

    def scalars(self, offset, size):
        at = self.model.data_range(offset, size)
        index = bisect_left(self.relocations, offset)
        require(index == len(self.relocations) or self.relocations[index] >= offset + size,
                'Model scalar data contains a pointer relocation')
        return at

    def word(self, offset):
        return self.words(offset, 1)[0]

    def words(self, offset, count):
        self.scalars(offset, count * 4)
        return self.model.data_words(offset, count)

    def floats(self, offset, count):
        at = self.scalars(offset, count * 4)
        require(all(math.isfinite(value) for value, in struct.iter_unpack('<f', self.model.data[at:at + count * 4])),
                'Model transforms/positions/UVs must be finite')

    def text(self, offset):
        at = self.model.data_range(offset, 1)
        end = self.model.data.find(b'\0', at, min(self.model.sections[1][4] + self.model.sections[1][5], at + MAX_STRING + 1))
        require(end > at and all(32 <= c < 127 for c in self.model.data[at:end]),
                'Invalid/unterminated model data string')
        self.scalars(offset, end - at + 1)
        return self.model.data[at:end].decode('ascii')

    def vertex_buffer(self, offset):
        size, stride, flags = self.words(offset + 4, 3)
        require(flags == 1 and stride in (2, 4, 8, 12) and 0 < size <= MAX_VERTICES * stride
                and size % stride == 0, 'Invalid model vertex-buffer dimensions/flags')
        data = self.model.local_pointer(offset + 16, size)
        header = self.model.local_pointer(offset, 8)
        require(self.word(header) == 1 and self.model.local_pointer(header + 4, size) == data,
                'Model vertex-buffer header differs from its inline data pointer')
        self.scalars(data, size)
        return {'bytes': size, 'stride': stride, 'count': size // stride, 'data': data}

    def position_bounds(self, buffer):
        at = self.scalars(buffer['data'], buffer['bytes'])
        minimum, maximum = [math.inf] * 3, [-math.inf] * 3
        for row in struct.iter_unpack('<3f', self.model.data[at:at + buffer['bytes']]):
            require(all(math.isfinite(value) for value in row), 'Model transforms/positions/UVs must be finite')
            for axis, value in enumerate(row):
                minimum[axis] = min(minimum[axis], value); maximum[axis] = max(maximum[axis], value)
        return {'min': minimum, 'max': maximum}

    def require_textures(self, textures, baseline_shapes=()):
        """The caller must derive any baseline shapes from verified original data."""
        from fighter_xsh import Textures
        require(isinstance(textures, Textures), 'Model requires validated texture data')
        missing = set(self.texture_shapes) - {image['name'] for image in textures.images} - set(baseline_shapes)
        require(not missing, 'Missing model texture shapes: ' + ', '.join(sorted(missing)))

    def metadata(self):
        return {'format': 'fighter-geometry-draft-1', 'model': self.name, 'material_groups': self.groups,
                'meshes': self.meshes, 'texture_shapes': self.texture_shapes,
                'external_texture_bindings': self.external_texture_bindings,
                'render_commands_validated': False, 'skin_weights_validated': False,
                'runtime_ready': False}
