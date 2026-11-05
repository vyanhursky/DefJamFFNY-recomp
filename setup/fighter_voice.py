"""Owned, bounded mono PCM16 voice streams for native decoder validation.

This deliberately admits a small authored profile, not arbitrary EA audio.
Native parser/packet/decoder sites: 1264F0, 129E60, 11F300, 12E490, 130EA0.
Bank event mappings, runtime registration and resource lifetime are separate
gates; a valid stream alone is not a runtime-ready fighter voice bank.
"""
from dataclasses import dataclass
import hashlib
import struct

from fighter_assets import AssetError


MAX_BYTES = 16 * 1024**2
MAX_SAMPLES = 4_000_000
MAX_PACKET_SAMPLES = 16384
MIN_RATE, MAX_RATE = 8000, 48000
PROPERTIES = (0xA0, 0x82, 0x84, 0x85)


def require(condition, message):
    if not condition:
        raise AssetError(message)


def chunk(tag, payload):
    return tag + struct.pack('<I', len(payload) + 8) + payload


def property_value(tag, value):
    # Four-byte positive signed BE integers avoid sign ambiguity at 128/32768.
    return bytes((tag, 4)) + struct.pack('>i', value)


@dataclass(frozen=True)
class VoiceStream:
    sample_rate: int
    sample_count: int
    packet_count: int
    pcm16: bytes
    sha256: str

    def metadata(self):
        return {'schema': 'fighter-voice-pcm16-1', 'sample_rate': self.sample_rate,
                'sample_count': self.sample_count, 'channels': 1,
                'native_codec': 8, 'packet_count': self.packet_count,
                'sha256': self.sha256, 'runtime_ready': False}


def parse_stream(data):
    """Reject unknown tags/codecs, ambiguous lengths and sample mismatches.

    No alignment padding is accepted after SCEl here. A bank container must
    validate its own alignment and pass the exact stream span to this parser.
    SCCl is optional; if present, our profile checks its packet count even
    though the native dispatch skips it.
    """
    require(isinstance(data, bytes) and 8 <= len(data) <= MAX_BYTES,
            'Voice stream exceeds its byte budget or is truncated')
    at, properties, declared_packets = 0, None, None
    packets, samples, decoded = 0, 0, []
    ended = False
    while at < len(data):
        require(at + 8 <= len(data), 'Truncated voice chunk header')
        tag, size = struct.unpack_from('<4sI', data, at)
        require(8 <= size <= 0xFFFFFF and size <= len(data) - at,
                'Voice chunk length is outside its bounded span')
        payload = data[at + 8:at + size]
        if tag == b'SCHl':
            require(at == 0 and properties is None, 'Voice header must be first and unique')
            require(payload[:4] == b'PT\x07\x00', 'Unsupported voice header profile')
            properties, cursor = {}, 4
            while cursor < len(payload) and payload[cursor] != 0xFF:
                require(cursor + 2 <= len(payload), 'Truncated voice property')
                key, width = payload[cursor:cursor + 2]
                cursor += 2
                require(key in PROPERTIES and key not in properties,
                        'Unknown or duplicate voice property')
                require(1 <= width <= 4 and cursor + width <= len(payload),
                        'Invalid voice property integer span')
                properties[key] = int.from_bytes(payload[cursor:cursor + width], 'big', signed=True)
                cursor += width
            require(cursor < len(payload) and payload[cursor:] == b'\xff',
                    'Voice property terminator or trailing bytes differ')
            require(set(properties) == set(PROPERTIES), 'Voice header is missing required properties')
            require(properties[0xA0] == 8 and properties[0x82] == 1,
                    'Only mono PCM16 voice streams are supported')
            require(MIN_RATE <= properties[0x84] <= MAX_RATE,
                    'Voice sample rate is outside the authored profile')
            require(0 < properties[0x85] <= MAX_SAMPLES,
                    'Voice sample count exceeds its budget')
        elif tag == b'SCCl':
            require(properties is not None and not packets and declared_packets is None
                    and len(payload) == 4, 'Invalid voice packet-count chunk')
            declared_packets, = struct.unpack('<I', payload)
            require(0 < declared_packets <= MAX_SAMPLES, 'Invalid declared voice packet count')
        elif tag == b'SCDl':
            require(properties is not None and len(payload) >= 8,
                    'Voice data precedes its header or has no packet fields')
            count, relative = struct.unpack_from('<2I', payload)
            require(0 < count <= MAX_PACKET_SAMPLES and relative == 0,
                    'Invalid PCM voice packet count or relative offset')
            require(len(payload) == 8 + 2 * count, 'PCM voice packet sample span differs')
            samples += count
            require(samples <= properties[0x85], 'Voice packets exceed the declared samples')
            packets += 1
            decoded.append(payload[8:])
        elif tag == b'SCEl':
            require(properties is not None and packets and size == 8
                    and at + size == len(data), 'Invalid voice end marker or trailing bytes')
            ended = True
        else:
            raise AssetError('Unsupported voice chunk')
        at += size
    require(ended, 'Voice stream has no end marker')
    require(samples == properties[0x85], 'Voice sample total differs from its header')
    require(declared_packets is None or packets == declared_packets,
            'Voice packet total differs from SCCl')
    return VoiceStream(properties[0x84], samples, packets, b''.join(decoded),
                       hashlib.sha256(data).hexdigest())


def encode_stream(pcm16, sample_rate, packet_samples=4096):
    """Compile caller-owned signed LE PCM samples; never execute package code."""
    require(isinstance(pcm16, bytes) and 0 < len(pcm16) <= MAX_SAMPLES * 2
            and len(pcm16) % 2 == 0, 'Invalid PCM16 voice input span')
    require(type(sample_rate) is int and MIN_RATE <= sample_rate <= MAX_RATE,
            'Invalid voice sample rate')
    require(type(packet_samples) is int and 0 < packet_samples <= MAX_PACKET_SAMPLES,
            'Invalid voice packet sample budget')
    count = len(pcm16) // 2
    packet_count = (count + packet_samples - 1) // packet_samples
    require(37 + 12 + len(pcm16) + packet_count * 16 + 8 <= MAX_BYTES,
            'Encoded voice stream exceeds its byte budget')
    header = b'PT\x07\x00' + b''.join(property_value(key, value)
              for key, value in zip(PROPERTIES, (8, 1, sample_rate, count))) + b'\xff'
    parts = [chunk(b'SCHl', header), chunk(b'SCCl', struct.pack('<I', packet_count))]
    for at in range(0, len(pcm16), packet_samples * 2):
        packet = pcm16[at:at + packet_samples * 2]
        parts.append(chunk(b'SCDl', struct.pack('<2I', len(packet) // 2, 0) + packet))
    parts.append(chunk(b'SCEl', b''))
    output = b''.join(parts)
    parse_stream(output)
    return output
