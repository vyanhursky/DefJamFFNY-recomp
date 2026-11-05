"""Bounded inspection of the native main motion-table partitions.

The own-dump initializer at1A47B0 establishes the two WAZA/FZUI/NAME layouts
and subsequent WPAR/WWAZ pairs. This reader checks their envelopes and table
spans, not the opaque move records, event links or animation data they reference.
It does not make a package runtime-compatible or extend the native core table.
"""
import hashlib
import struct

from fighter_assets import AssetError

MAX_BYTES = 64 * 1024**2
MAX_CORES = 16384
MAX_MOVES = 65535
MAX_GROUPS = 4096
MAX_PARAMETERS = 1_000_000
MAX_NAME = 1024


def require(condition, message):
    if not condition:
        raise AssetError(message)


class MotionIndex:
    def __init__(self, data):
        require(isinstance(data, bytes) and 8 <= len(data) <= MAX_BYTES, 'Invalid motion index byte budget')
        self.data, self.offset = data, 0
        self.tables, self.move_spans, self.core_spans = [], [], []
        for _ in range(2):
            moves = self.chunk(b'WAZA')
            require(len(moves) >= 12, 'Truncated WAZA header')
            stride, count, groups = struct.unpack_from('<3I', moves)
            require(stride == 32 and 0 < count <= MAX_MOVES and 0 < groups <= MAX_GROUPS,
                    'Unsupported WAZA dimensions')
            require(len(moves) == 12 + groups * 4 + count * stride, 'WAZA table span differs from its dimensions')
            populations = list(struct.unpack_from('<' + 'I' * groups, moves, 12))
            self.move_spans.append((self.offset - len(moves) + 12 + groups * 4, count))
            # Added rows can follow the originally grouped rows. The community
            # stream does this; group population is not the total move count.
            require(sum(populations) <= count, 'WAZA groups exceed the move table')

            parameters = self.chunk(b'FZUI')
            require(len(parameters) >= 8, 'Truncated FZUI header')
            parameter_stride, parameter_count = struct.unpack_from('<2I', parameters)
            require(parameter_stride == 39 and 0 < parameter_count <= MAX_PARAMETERS,
                    'Unsupported FZUI dimensions')
            end = 8 + parameter_stride * parameter_count
            require(len(parameters) == ((end + 3) & ~3) and not any(parameters[end:]),
                    'FZUI table span or alignment padding differs')

            names = self.chunk(b'NAME')
            require(len(names) >= 4, 'Truncated motion NAME header')
            name_count, = struct.unpack_from('<I', names)
            start = 4 + name_count * 2
            require(0 < name_count <= MAX_MOVES and start < len(names), 'Invalid motion NAME dimensions')
            offsets = struct.unpack_from('<' + 'H' * name_count, names, 4)
            for relative in offsets:
                at = start + relative
                require(at < len(names) and (not relative or names[at - 1] == 0),
                        'Motion NAME offset does not start a bounded string')
                stop = names.find(b'\0', at, at + MAX_NAME + 1)
                require(stop >= at and all(32 <= value < 127 for value in names[at:stop]),
                        'Invalid or unterminated motion name')
            self.tables.append({'move_count': count, 'move_stride': stride,
                                'group_populations': populations, 'ungrouped_move_count': count - sum(populations),
                                'parameter_count': parameter_count, 'parameter_stride': parameter_stride,
                                'name_count': name_count})

        self.cores = []
        while self.offset < len(data):
            require(len(self.cores) < MAX_CORES, 'Motion core population exceeds budget')
            parameters = self.chunk(b'WPAR')
            self.core_spans.append(self.offset - len(parameters))
            moves = self.chunk(b'WWAZ')
            require(len(parameters) == 64 and len(moves) == 780, 'Unsupported core motion pair dimensions')
            self.cores.append({'ordinal': len(self.cores) + 1,
                               'parameters_sha256': hashlib.sha256(parameters).hexdigest(),
                               'moves_sha256': hashlib.sha256(moves).hexdigest()})
        require(self.cores, 'Motion index has no core pairs')

    def record(self, kind, index, partition=0):
        """Decode one bounded record; native offset names do not imply semantics."""
        from fighter_motion_records import PackedRecord
        require(type(partition) is int and partition in (0, 1), 'Invalid motion partition')
        require(type(index) is int and index >= 0, 'Invalid motion record index')
        if kind == 'move':
            start, count = self.move_spans[partition]
            require(index < count, 'Motion record index exceeds partition')
            start += index * 32
            size = 32
        else:
            require(kind == 'core' and partition == 0, 'Core records do not have move partitions')
            require(index < len(self.core_spans), 'Motion core record index exceeds table')
            start, size = self.core_spans[index], 64
        return PackedRecord.decode(kind, self.data[start:start + size])

    def chunk(self, expected):
        require(self.offset + 8 <= len(self.data), 'Truncated motion chunk header')
        tag, size = struct.unpack_from('<4sI', self.data, self.offset)
        require(tag == expected, 'Expected motion chunk ' + expected.decode('ascii'))
        start = self.offset + 8
        require(size <= len(self.data) - start, 'Motion chunk exceeds its envelope')
        self.offset = start + size
        return self.data[start:self.offset]

    def metadata(self):
        return {'format': 'fighter-motion-index-draft-1', 'sha256': hashlib.sha256(self.data).hexdigest(),
                'bytes': len(self.data), 'tables': self.tables, 'core_count': len(self.cores), 'cores': self.cores,
                'move_records_validated': False, 'animation_links_validated': False, 'runtime_ready': False}
