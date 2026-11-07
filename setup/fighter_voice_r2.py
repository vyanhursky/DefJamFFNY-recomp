"""Typed mono EA ADPCM R2 packets; no executable/container metadata admission.

The native codec consumes 15-byte predictive or 61-byte literal blocks of 28
samples, including a complete encoded block for a partial declared tail. Only
the four audited predictor coefficients are addressable. Rebuilding retains
the coded blocks and packet counts, preserving native float predictor history.
"""
from dataclasses import dataclass
import hashlib
import struct

from fighter_voice import MAX_BYTES, MAX_SAMPLES, MIN_RATE, MAX_RATE, chunk, property_value, require


R2_PROPERTIES = (0x80, 0xA0, 0x82, 0x84, 0x85)
SOURCE_PROPERTIES = frozenset((*R2_PROPERTIES, 0x06, 0x8C))
MAX_PACKET_SAMPLES = 16384


@dataclass(frozen=True)
class R2Stream:
    sample_rate: int
    sample_count: int
    packets: tuple
    sha256: str

    @property
    def packet_count(self):
        return len(self.packets)

    def metadata(self):
        return {'schema': 'fighter-voice-ea-r2-1', 'sample_rate': self.sample_rate,
                'sample_count': self.sample_count, 'channels': 1, 'native_codec': 10,
                'revision': 3, 'packet_count': self.packet_count, 'sha256': self.sha256,
                'runtime_ready': False}


def packet_blocks(payload, samples):
    require(type(samples) is int and 0 < samples <= MAX_PACKET_SAMPLES,
            'R2 packet sample population exceeds budget')
    at = 0
    for _ in range((samples + 27) // 28):
        require(at < len(payload), 'Truncated R2 block')
        selector = payload[at]
        require(selector == 0xEE or selector >> 4 < 4, 'Unsupported R2 predictor index')
        size = 61 if selector == 0xEE else 15
        require(at + size <= len(payload), 'R2 coded block exceeds packet')
        at += size
    require(len(payload) - at <= 3 and not any(payload[at:]), 'Unexpected R2 packet tail')
    return payload[:at]


def inspect_source(data):
    require(isinstance(data, bytes) and 16 <= len(data) <= MAX_BYTES, 'R2 stream byte budget')
    tag, size = struct.unpack_from('<4sI', data)
    require(tag == b'SCHl' and 16 <= size <= len(data) and data[8:12] == b'PT\x07\0',
            'Unsupported R2 platform header')
    at, properties, split = 12, {}, False
    while at < size and data[at] != 255:
        key = data[at]
        at += 1
        if key == 253:
            require(not split, 'Duplicate R2 property section')
            split = True
            continue
        require(key in SOURCE_PROPERTIES and key not in properties and at < size,
                'Unknown or duplicate R2 property')
        require((key == 0x06) != split,
                'R2 property belongs to a different header section')
        width = data[at]
        at += 1
        require(1 <= width <= 4 and at + width <= size, 'Invalid R2 property span')
        # Native 12C6E0 sign-extends short property integers. The count keeps
        # all 32 bits; unlike the bounded WORD sample rate, truncation cannot
        # turn a negative encoding back into its intended positive value.
        properties[key] = int.from_bytes(data[at:at + width], 'big', signed=key == 0x85)
        at += width
    require(at < size and data[at] == 255 and size - at <= 4 and not any(data[at + 1:size]),
            'Invalid R2 property terminator')
    require(split and properties.get(0x80) == 3 and properties.get(0xA0) == 10,
            'Expected revision 3 EA ADPCM R2')
    require(properties.get(0x06) == 101 and properties.get(0x8C) == 36,
            'Unsupported legacy R2 auxiliary properties')
    rate, count = properties.get(0x84, 24000), properties.get(0x85, 0)
    require(properties.get(0x82, 1) == 1 and MIN_RATE <= rate <= MAX_RATE
            and 0 < count <= MAX_SAMPLES, 'R2 mono rate/sample budget')
    at, packets, declared, total, ended = size, [], None, 0, False
    while at < len(data):
        require(at + 8 <= len(data), 'Truncated R2 chunk header')
        tag, size = struct.unpack_from('<4sI', data, at)
        require(8 <= size <= 0xFFFFFF and size <= len(data) - at, 'R2 chunk exceeds stream')
        if tag == b'SCCl':
            require(not packets and declared is None and size == 12, 'Invalid R2 packet-count chunk')
            declared = struct.unpack_from('<I', data, at + 8)[0]
        elif tag == b'SCDl':
            require(size > 16, 'R2 data packet has no coded blocks')
            samples, relative = struct.unpack_from('<II', data, at + 8)
            require(relative == 0, 'R2 mono relative packet offset differs')
            coded = packet_blocks(data[at + 16:at + size], samples)
            total += samples
            require(total <= count, 'R2 packets exceed declared samples')
            packets.append((samples, coded))
        elif tag == b'SCEl':
            require(size == 8 and at + size == len(data), 'R2 end marker or trailing bytes differ')
            ended = True
        else:
            require(False, 'Unsupported R2 chunk')
        at += size
    require(ended and packets and total == count and (declared is None or declared == len(packets)),
            'R2 sample/packet/end population differs')
    require(all(n % 28 == 0 for n, _ in packets[:-1]), 'Non-final partial R2 packet is unsupported')
    return R2Stream(rate, count, tuple(packets), hashlib.sha256(data).hexdigest())


def canonical_r2(data):
    source = inspect_source(data)
    header = b'PT\x07\0' + property_value(0x06, 101) + b'\xfd'
    header += b''.join(property_value(k, v) for k, v in
              zip(R2_PROPERTIES, (3, 10, 1, source.sample_rate, source.sample_count)))
    header += property_value(0x8C, 36) + b'\xff'
    parts = [chunk(b'SCHl', header), chunk(b'SCCl', struct.pack('<I', source.packet_count))]
    for count, coded in source.packets:
        parts.append(chunk(b'SCDl', struct.pack('<II', count, 0) + coded))
    parts.append(chunk(b'SCEl', b''))
    result = b''.join(parts)
    checked = inspect_source(result)
    require(checked.packets == source.packets and checked.sample_rate == source.sample_rate,
            'Canonical R2 payload changed')
    return result


def parse_r2(data):
    source = inspect_source(data)
    require(canonical_r2(data) == data, 'Native R2 stream must have a compiler-owned canonical header')
    return source
