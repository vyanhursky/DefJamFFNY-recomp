"""Verified PS2 FFNY layout conversion; shared by the launcher and command line."""
import re
import struct
import xbox_save_format as xbox
from ps2_save_containers import require

PS2_HEADER = 28
IDENTITY_END = 92
PS2_PROFILE = 0x590C
XBOX_PROFILE = 0x5904
PS2_OPTIONS = 0x1494
XBOX_OPTIONS = 0x1490
PS2_BUILD = -2048007603
XBOX_BUILD = -2030886228
NAME = re.compile(r'[A-Za-z0-9 _-]{1,11}\Z')


def _crc_table():
    table = []
    for i in range(256):
        value = i << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04C11DB7 if value & 0x80000000 else 0)) & 0xFFFFFFFF
        table.append(value)
    return table


CRC_TABLE = _crc_table()


def mc02_checksum(data):
    """EA's non-reflected CRC: seed with complemented first big-endian dword.

    This is not zlib.crc32. Feed subsequent bytes into the low byte, advancing
    the polynomial from the high byte; complement the final accumulator.
    """
    require(len(data) >= 4, 'MC02 checksum block is too short')
    value = int.from_bytes(data[:4], 'big') ^ 0xFFFFFFFF
    for byte in data[4:]:
        value = (((value << 8) | byte) ^ CRC_TABLE[value >> 24]) & 0xFFFFFFFF
    return value ^ 0xFFFFFFFF


def parse_profile(raw):
    require(len(raw) >= IDENTITY_END, 'truncated PS2 MC02 header')
    magic, size, identity_size, payload_size, c0, c1, c2 = struct.unpack_from('<7I', raw)
    require(magic == 0x4D433032 and size == len(raw) and identity_size == 64 and
            payload_size == len(raw) - IDENTITY_END, 'PS2 MC02 header/size mismatch')
    identity, payload = raw[PS2_HEADER:IDENTITY_END], raw[IDENTITY_END:]
    require((c0, c1, c2) == tuple(mc02_checksum(b) for b in (identity, payload, raw[:24])),
            'PS2 MC02 checksum mismatch (damaged source)')
    tag = identity.split(b'\0', 1)[0]
    if tag == ('DJFFNY::User 17 %d' % PS2_BUILD).encode('ascii'):
        require(len(payload) == PS2_PROFILE, 'unsupported PS2 Story layout')
        field = payload[:16]
        require(b'\0' in field, 'unterminated profile name')
        name = field.split(b'\0', 1)[0].decode('ascii')
        require(NAME.fullmatch(name) is not None and name != 'Options', 'unsupported profile name')
        require(payload[0x17E:0x184] == bytes(6) and payload[0x4D8E:0x4D90] == bytes(2),
                'unsupported PS2 profile padding/layout')
        return name, payload
    require(tag == ('DJFFNY::Global 17 %d' % PS2_BUILD).encode('ascii') and
            len(payload) == PS2_OPTIONS, 'unsupported FFNY version or save kind')
    return 'Options', payload


def signed_profile(kind, payload):
    identity = ('DJFFNY::%s 17 %d' % (kind, XBOX_BUILD)).encode('ascii').ljust(64, b'\0')
    header = struct.pack('<4I', 0x4D433032, xbox.IDENTITY_END + len(payload), 64, len(payload)) + bytes(60)
    return xbox.resign(header + identity + payload, xbox.PORT_KEY)


def convert_story(payload):
    # Observed retail PS2 saves have six zero bytes before the embedded arrays
    # and two after the flags/counter at 0x4D8D. Refuse nonzero spans rather
    # than treating unknown platform fields as padding. Keep that counter.
    require(len(payload) == PS2_PROFILE and payload[0x17E:0x184] == bytes(6) and
            payload[0x4D8E:0x4D90] == bytes(2), 'unsupported PS2 profile layout')
    out = payload[:0x17E] + payload[0x184:0x4D8E] + payload[0x4D90:]
    require(len(out) == XBOX_PROFILE, 'converted profile length mismatch')
    return signed_profile('User', out)


def convert_options(payload, native):
    require(len(payload) == PS2_OPTIONS, 'unsupported PS2 Options layout')
    return merge_unlocks(payload, native)


def merge_unlocks(payload, native):
    require(len(payload) in (PS2_OPTIONS, XBOX_OPTIONS), 'unsupported Options layout')
    require(xbox.header_fault(native) is None and all(xbox.signatures_ok(native, xbox.PORT_KEY)) and
            len(native) == xbox.IDENTITY_END + XBOX_OPTIONS and
            native[xbox.HEADER:xbox.IDENTITY_END].startswith(b'DJFFNY::Global 17 '),
            'Options target must be a valid native Options save; start the game once first')
    out = bytearray(native[xbox.IDENTITY_END:])
    out[0x1214:0x148C] = payload[0x1214:0x148C]
    return signed_profile('Global', bytes(out))


def check_unlock_lists(payload, options=False):
    """Check the fixed capacities the native loader trusts before giving it data."""
    if options:
        venue_count, fighter_count = struct.unpack_from('<II', payload, 0x1214)
        require(venue_count <= 30 and fighter_count <= 80, 'Options unlock count exceeds capacity')
        lists = [(0x121C, venue_count, 23, 24), (0x1294, fighter_count, 7, 75)]
        songs = struct.unpack_from('<I', payload, 0x1488)[0]
        require(songs <= 39, 'Options song count exceeds capacity')
        require(all(v < 32 for v in struct.unpack_from('<%dI' % songs, payload, 0x13F8)),
                'Options contains unsupported song references')
    else:
        # Profile points to two inline story-event lists, after removing padding.
        lists = []
        for count_at, values_at, capacity, table, rows in ((0x51A0, 0x51A4, 140, 21, 95),
                                                         (0x53D4, 0x53D8, 96, 2, 81)):
            count = struct.unpack_from('<I', payload, count_at)[0]
            require(count <= capacity, 'Story event count exceeds capacity')
            lists.append((values_at, count, table, rows))
    for offset, count, table, rows in lists:
        values = struct.unpack_from('<%dI' % count, payload, offset)
        require(all(v >> 24 == table and (v & 0xFFFFFF) < rows for v in values),
                'unsupported saved database reference')
