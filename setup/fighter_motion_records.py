"""Lossless packed motion records, independently mapped from native consumers.

Fields are identified by decoded native offsets until their game-level meaning
is established. These are inspection/conversion primitives, not an authoring
contract or permission to activate unvalidated moves, events or animation links.
"""
from dataclasses import dataclass
import struct

from fighter_assets import AssetError


@dataclass(frozen=True)
class Field:
    offset: int
    bits: int
    storage: str
    conversion: str = 'raw'


MOVE_FIELDS = (
    Field(0, 8, 'H'), Field(2, 6, 'B'), Field(3, 6, 'b', 'signed'),
    *(Field(4 + i, width, 'B') for i, width in enumerate((7, 4, 3, 3, 5, 5, 5, 5, 3, 4))),
    *(Field(0x10 + i * 4, 6, 'f', 'tenths') for i in range(5)),
    *(Field(0x24 + i, width, 'B') for i, width in enumerate((4, 5, 4, 5, 4, 3, 6))),
    Field(0x2c, 32, 'I'), Field(0x30, 32, 'I'),
    Field(0x34, 8, 'H'), Field(0x36, 10, 'H'), Field(0x38, 7, 'H'),
    Field(0x3a, 12, 'H', 'sentinel'), Field(0x3c, 12, 'H'), Field(0x3e, 12, 'H'),
)
CORE_FIELDS = (
    Field(0, 3, 'I'), Field(4, 3, 'I', 'sentinel'), Field(8, 3, 'I', 'sentinel'),
    Field(12, 5, 'I'), Field(16, 5, 'I'),
    *(Field(0x14 + i * 4, width, 'I') for i, width in enumerate((2, 2, 3, 3, 3))),
    *(Field(0x28 + i * 4, 4, 'I') for i in range(17)),
    *(Field(0x6c + i, 6, 'B') for i in range(47)),
    *(Field(0x9c + i * 4, 3, 'I') for i in range(8)),
    *(Field(0xbc + i * 4, 7, 'I') for i in range(6)),
    *(Field(0xd4 + i * 4, 8, 'I') for i in range(4)),
    Field(0xe4, 16, 'H'), Field(0xe6, 16, 'H'),
)
# Native 1A38B0 reads the tail fields before the four repeated leading groups.
# Preserve wire order, which differs from decoded output-offset order.
PARAMETER_FIELDS = (
    Field(0x30, 11, 'I', 'sentinel'), Field(0x34, 11, 'I', 'sentinel'),
    *(Field(offset, 11, 'I') for offset in range(0x38, 0x58, 4)),
    *(Field(0x58 + i * 4, width, 'I') for i, width in enumerate((3, 7, 4, 11, 2, 5, 11, 2))),
    *(Field(offset, 8, 'f', 'hundredths') for offset in (0x78, 0x7c, 0x80)),
    Field(0x84, 16, 'H'),
    *(Field(group * 12 + i * 4, width, 'I') for group in range(4) for i, width in enumerate((11, 11, 7))),
)


@dataclass(frozen=True)
class PackedRecord:
    kind: str
    values: tuple
    tail: int = 0

    @property
    def layout(self):
        if self.kind == 'move':
            return MOVE_FIELDS, 32, 64
        if self.kind == 'core':
            return CORE_FIELDS, 64, 232
        if self.kind == 'parameter':
            return PARAMETER_FIELDS, 39, 136
        raise AssetError('Unknown packed motion record kind')

    @classmethod
    def decode(cls, kind, data):
        fields, size, _ = cls(kind, ()).layout
        if not isinstance(data, bytes) or len(data) != size:
            raise AssetError('Packed motion record has the wrong size')
        word, remaining, values = int.from_bytes(data, 'big'), size * 8, []
        for field in fields:
            remaining -= field.bits
            values.append((word >> remaining) & ((1 << field.bits) - 1))
        return cls(kind, tuple(values), word & ((1 << remaining) - 1))

    def encode(self):
        fields, size, _ = self.layout
        if type(self.values) is not tuple or len(self.values) != len(fields):
            raise AssetError('Packed motion record has the wrong field count')
        word = 0
        for field, value in zip(fields, self.values):
            if type(value) is not int or not 0 <= value < 1 << field.bits:
                raise AssetError(f'Packed motion field +{field.offset:02x} exceeds its bit width')
            word = (word << field.bits) | value
        remaining = size * 8 - sum(field.bits for field in fields)
        if type(self.tail) is not int or not 0 <= self.tail < 1 << remaining:
            raise AssetError('Packed motion tail exceeds its bit width')
        return ((word << remaining) | self.tail).to_bytes(size, 'big')

    def native_bytes(self):
        """Exact storage conversion; unknown domain semantics remain unvalidated."""
        self.encode()  # Validate manually constructed instances as well.
        fields, _, size = self.layout
        output = bytearray(size)
        # The original's multiplier is the float32 value at native 0x2972c4.
        # Multiplying by Python's decimal 0.1 changes some final float32 bits.
        scale = struct.unpack('<f', bytes.fromhex('cdcccc3d'))[0]
        for field, raw in zip(fields, self.values):
            value = raw
            if field.conversion == 'signed' and raw & (1 << (field.bits - 1)):
                value -= 1 << field.bits
            elif field.conversion == 'sentinel' and raw == (1 << field.bits) - 1:
                value = (1 << (8 * struct.calcsize(field.storage))) - 1
            elif field.conversion == 'tenths':
                value = raw * scale
            elif field.conversion == 'hundredths':
                # Original float32 multiplier at native 0x292378.
                value = raw * struct.unpack('<f', bytes.fromhex('0ad7233c'))[0]
            struct.pack_into('<' + field.storage, output, field.offset, value)
        if self.kind == 'parameter':
            previous, current = struct.unpack_from('<2I', output, 0x44)
            if previous != 0x7ff and current == 0x7ff:
                struct.pack_into('<I', output, 0x48, 0xffffffff)
        return bytes(output)

    def metadata(self):
        fields, size, native_size = self.layout
        self.encode()
        return {'kind': self.kind, 'packed_bytes': size, 'native_bytes': native_size,
                'fields': [{'native_offset': field.offset, 'packed_bits': field.bits,
                            'storage': field.storage, 'conversion': field.conversion, 'raw': value}
                           for field, value in zip(fields, self.values)],
                'uninterpreted_tail': self.tail, 'semantic_links_validated': False,
                'runtime_ready': False}
