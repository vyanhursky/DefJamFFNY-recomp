"""Compose owned voice samples behind verified native event-selection metadata.

The template comes from the verified local game, never a mod-supplied HDR/DAT.
Only explicit bank keys and sample offsets change; metadata, entry ordering,
selection masks and history configuration retain the original event contract.
This is a compiler primitive, not runtime admission or a named-event schema.
"""
import hashlib
import struct

from fighter_voice import parse_owned_stream, require
from fighter_assets import AssetError

MAX_BANK_BYTES = 64 * 1024**2
MAX_HEADER_BYTES = 64 * 1024
FAMILIES = {'Character': (0, 1), 'Taunts': (16625, 16626), 'Enviro': (40962, 40963)}


def stream_span(data):
    """Locate SCEl without invoking any codec; check the enclosing alignment.

    Unknown chunks/codecs are allowed only for verified original template
    entries. Authored replacements additionally pass the owned codec parser.
    """
    at = 0
    require(data[:4] == b'SCHl', 'Voice bank entry must start with SCHl')
    while at < len(data):
        require(at + 8 <= len(data), 'Truncated bank stream chunk')
        tag, size = struct.unpack_from('<4sI', data, at)
        require(8 <= size <= 0xFFFFFF and size <= len(data) - at,
                'Bank stream chunk exceeds its span')
        at += size
        if tag == b'SCEl':
            require(size == 8 and not any(data[at:]), 'Invalid bank stream end or padding')
            return data[:at]
    raise AssetError('Voice bank stream has no SCEl')


class VoiceBankTemplate:
    def __init__(self, header, data, header_sha256, data_sha256):
        require(isinstance(header, bytes) and 12 <= len(header) <= MAX_HEADER_BYTES
                and isinstance(data, bytes) and 0 < len(data) <= MAX_BANK_BYTES,
                'Voice bank input byte budget')
        require(hashlib.sha256(header).hexdigest() == header_sha256
                and hashlib.sha256(data).hexdigest() == data_sha256,
                'Voice bank template differs from verified source')
        self.header, self.data = header, data
        self.source_hashes = (header_sha256, data_sha256)
        self.first_key, self.voice_key = struct.unpack_from('<2H', header)
        self.criteria, self.count = header[4] & 127, header[5]
        self.stride, unit = self.criteria + 2, (header[7] + 1) * 256
        require(self.count > 0, 'Voice bank has no entries')
        table_end = 12 + self.count * self.stride
        trailer = (table_end + 3) & ~3
        # Validate minimum structural trailer. Its semantic fields are retained
        # from the trusted template, not accepted as arbitrary mod metadata.
        end = trailer + self.criteria * 4
        require(end <= len(header), 'Voice bank criteria trailer is truncated')
        if header[4] & 128:
            require(end < len(header) and 0 < header[end] <= self.count,
                    'Invalid voice bank eligibility partition count')
            end += 1 + (self.count + 7) // 8
        if header[6]:
            end += 1 + header[6]
        rows, = struct.unpack_from('<H', header, 10)
        # FFFF has a distinct native sentinel meaning. Its matrix span has not
        # been validated, so this initial compiler rejects it explicitly.
        require(rows != 0xFFFF, 'Voice bank matrix sentinel needs a separate adapter')
        end += (rows * self.count + 7) // 8
        require(end <= len(header), 'Voice bank history or eligibility matrix is truncated')
        starts = [int.from_bytes(header[12 + i * self.stride:14 + i * self.stride], 'big') * unit
                  for i in range(self.count)]
        terminal = struct.unpack_from('<H', header, 8)[0] * unit
        require(starts[0] == 0 and terminal <= len(data), 'Voice bank offsets exceed DAT')
        self.unindexed_bytes = len(data) - terminal
        stops = starts[1:] + [terminal]
        require(all(start < stop for start, stop in zip(starts, stops)),
                'Voice bank offsets must increase within DAT')
        self.streams = tuple(stream_span(data[start:stop]) for start, stop in zip(starts, stops))

    def compose(self, voice_key, replacements, *, family=None):
        """Replace entry ordinals with validated streams while preserving events.

        A higher-level event schema must resolve names to these ordinals. The
        first native bank key belongs to that inherited event contract; the
        filename's base/IP directory must not silently change it.
        """
        require(type(voice_key) is int and 0 <= voice_key < 0xFFFF,
                'Voice bank key must fit the non-sentinel native WORD')
        selected_family = self.first_key if family is None else family
        if family is not None:
            require(type(family) is int and any(self.first_key in group and family in group
                                              for group in FAMILIES.values()),
                    'Explicit voice family must retain its verified category')
        require(type(replacements) is dict, 'Voice replacements must map entry ordinals')
        for index, data in replacements.items():
            require(type(index) is int and 0 <= index < self.count,
                    'Voice replacement exceeds event entry count')
            parse_owned_stream(data)
        streams = [replacements.get(i, value) for i, value in enumerate(self.streams)]
        # Offsets are u16 units; choose the smallest representable unit. This
        # changes alignment only, never the sample bytes or event ordinals.
        unit = 256
        while unit <= 65536:
            sizes = [(len(value) + unit - 1) // unit * unit for value in streams]
            total = sum(sizes)
            if total // unit <= 0xFFFF:
                break
            unit += 256
        require(unit <= 65536 and total <= MAX_BANK_BYTES, 'Composed voice bank exceeds budget')
        header = bytearray(self.header)
        struct.pack_into('<H', header, 0, selected_family)
        struct.pack_into('<H', header, 2, voice_key)
        header[7] = unit // 256 - 1
        struct.pack_into('<H', header, 8, total // unit)
        at, parts = 0, []
        for index, (value, size) in enumerate(zip(streams, sizes)):
            struct.pack_into('>H', header, 12 + index * self.stride, at // unit)
            parts.extend((value, bytes(size - len(value))))
            at += size
        result_header, result_data = bytes(header), b''.join(parts)
        hashes = [hashlib.sha256(value).hexdigest() for value in (result_header, result_data)]
        checked = VoiceBankTemplate(result_header, result_data, *hashes)
        require(checked.streams == tuple(streams), 'Composed voice entry spans differ')
        return result_header, result_data, {
            'schema': 'fighter-voice-template-1', 'first_key': selected_family,
            'source_first_key': self.first_key,
            'voice_key': voice_key, 'entry_count': self.count,
            'authored_entries': sorted(replacements), 'source_hashes': list(self.source_hashes),
            'discarded_unindexed_bytes': self.unindexed_bytes,
            'sha256': hashes, 'event_policy': 'verified-original-metadata',
            'native_registration_required': True, 'runtime_ready': False,
        }
