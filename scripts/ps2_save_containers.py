"""Read PS2 save exports without extracting archive paths or opening a memory card.

MAX/CBS/PSU/SPS layouts and CBS permutation: Ross Ridge's public-domain mymc
https://github.com/ps2dev/mymc/blob/master/ps2save.py
PSV field layout: https://github.com/PCSX2/myMCpp/blob/master/src/core/formats/PS2SaveFile.cpp
Only the contained FFNY MC02 data is used; PS2 icons and PS3 signatures are not
converted. The inner MC02 checksums are independently verified by the importer.
"""
import struct
import zlib

from ps2_lzari import LzariDecoder

MAX_FILE = 4 << 20
MAX_TOTAL = 32 << 20
MAX_FILES = 256

CBS_STATE = [0x5f, 0x1f, 0x85, 0x6f, 0x31, 0xaa, 0x3b, 0x18,
		    0x21, 0xb9, 0xce, 0x1c, 0x07, 0x4c, 0x9c, 0xb4,
		    0x81, 0xb8, 0xef, 0x98, 0x59, 0xae, 0xf9, 0x26,
		    0xe3, 0x80, 0xa3, 0x29, 0x2d, 0x73, 0x51, 0x62,
		    0x7c, 0x64, 0x46, 0xf4, 0x34, 0x1a, 0xf6, 0xe1,
		    0xba, 0x3a, 0x0d, 0x82, 0x79, 0x0a, 0x5c, 0x16,
		    0x71, 0x49, 0x8e, 0xac, 0x8c, 0x9f, 0x35, 0x19,
		    0x45, 0x94, 0x3f, 0x56, 0x0c, 0x91, 0x00, 0x0b,
		    0xd7, 0xb0, 0xdd, 0x39, 0x66, 0xa1, 0x76, 0x52,
		    0x13, 0x57, 0xf3, 0xbb, 0x4e, 0xe5, 0xdc, 0xf0,
		    0x65, 0x84, 0xb2, 0xd6, 0xdf, 0x15, 0x3c, 0x63,
		    0x1d, 0x89, 0x14, 0xbd, 0xd2, 0x36, 0xfe, 0xb1,
		    0xca, 0x8b, 0xa4, 0xc6, 0x9e, 0x67, 0x47, 0x37,
		    0x42, 0x6d, 0x6a, 0x03, 0x92, 0x70, 0x05, 0x7d,
		    0x96, 0x2f, 0x40, 0x90, 0xc4, 0xf1, 0x3e, 0x3d,
		    0x01, 0xf7, 0x68, 0x1e, 0xc3, 0xfc, 0x72, 0xb5,
		    0x54, 0xcf, 0xe7, 0x41, 0xe4, 0x4d, 0x83, 0x55,
		    0x12, 0x22, 0x09, 0x78, 0xfa, 0xde, 0xa7, 0x06,
		    0x08, 0x23, 0xbf, 0x0f, 0xcc, 0xc1, 0x97, 0x61,
		    0xc5, 0x4a, 0xe6, 0xa0, 0x11, 0xc2, 0xea, 0x74,
		    0x02, 0x87, 0xd5, 0xd1, 0x9d, 0xb7, 0x7e, 0x38,
		    0x60, 0x53, 0x95, 0x8d, 0x25, 0x77, 0x10, 0x5e,
		    0x9b, 0x7f, 0xd8, 0x6e, 0xda, 0xa2, 0x2e, 0x20,
		    0x4f, 0xcd, 0x8f, 0xcb, 0xbe, 0x5a, 0xe0, 0xed,
		    0x2c, 0x9a, 0xd4, 0xe2, 0xaf, 0xd0, 0xa9, 0xe8,
		    0xad, 0x7a, 0xbc, 0xa8, 0xf2, 0xee, 0xeb, 0xf5,
		    0xa6, 0x99, 0x28, 0x24, 0x6c, 0x2b, 0x75, 0x5d,
		    0xf8, 0xd3, 0x86, 0x17, 0xfb, 0xc0, 0x7b, 0xb3,
		    0x58, 0xdb, 0xc7, 0x4b, 0xff, 0x04, 0x50, 0xe9,
		    0x88, 0x69, 0xc9, 0x2a, 0xab, 0xfd, 0x5b, 0x1b,
		    0x8a, 0xd9, 0xec, 0x27, 0x44, 0x0e, 0x33, 0xc8,
		    0x6b, 0x93, 0x32, 0x48, 0xb6, 0x30, 0x43, 0xa5]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cut(data, offset, size):
    require(0 <= offset <= len(data) and 0 <= size <= MAX_FILE and offset + size <= len(data),
            'truncated or oversized save container')
    return data[offset:offset + size]


def name(raw):
    value = raw.split(b'\0', 1)[0].decode('ascii')
    require(value and not any(c in value for c in '/\\:') and value not in ('.', '..'),
            'unsafe or empty contained filename')
    return value


def rc4(data):
    state = CBS_STATE[:]
    j = 0
    out = bytearray()
    for pos, byte in enumerate(data):
        i = (pos + 1) & 255
        j = (j + state[i]) & 255
        state[i], state[j] = state[j], state[i]
        out.append(byte ^ state[(state[i] + state[j]) & 255])
    return bytes(out)


def unpack(data):
    """Return (member name, bytes) pairs. Bounds/checks precede decompression."""
    if data.startswith(b'20CM'):
        return [('', data)]
    if data.startswith(b'Ps2PowerSave'):
        _, checksum, _, _, compressed, count, size = struct.unpack('<12sI32s32sIII', cut(data, 0, 92))
        require(zlib.crc32(data[:12] + bytes(4) + data[16:]) == checksum, 'MAX archive CRC mismatch')
        require(0 < count <= MAX_FILES and 0 < size <= MAX_FILE, 'MAX expansion exceeds limits')
        # Some MAX writers put the uncompressed size in both size fields.
        require(compressed in (len(data) - 88, len(data) - 92, size), 'MAX compressed size mismatch')
        body = LzariDecoder().decode(data[92:], size)
        files, offset = [], 0
        for _ in range(count):
            length, raw_name = struct.unpack('<I32s', cut(body, offset, 36))
            offset += 36
            files.append((name(raw_name), cut(body, offset, length)))
            offset = ((offset + length + 8 + 15) // 16) * 16 - 8
        require(offset == len(body), 'MAX member count/length mismatch')
        return files
    if data.startswith(b'CFU\0'):
        header, size, compressed = struct.unpack('<III', cut(data, 8, 12))
        require(124 <= header <= len(data) and 0 < size <= MAX_FILE, 'invalid CBS sizes')
        require(compressed in (len(data), len(data) - header), 'CBS compressed size mismatch')
        stream = zlib.decompressobj()
        body = stream.decompress(rc4(data[header:]), size + 1)
        require(len(body) == size and stream.eof and not stream.unused_data and not stream.unconsumed_tail,
                'CBS decompressed length/stream mismatch')
        files, offset = [], 0
        while offset < len(body):
            record = cut(body, offset, 64)
            length = struct.unpack_from('<I', record, 16)[0]
            require(struct.unpack_from('<H', record, 20)[0] & 0x10, 'CBS member is not a file')
            offset += 64
            files.append((name(record[32:64]), cut(body, offset, length)))
            offset += length
            require(len(files) <= MAX_FILES, 'too many CBS members')
        return files
    if data.startswith(b'\x0d\0\0\0SharkPortSave'):
        offset = 21
        for _ in range(3):
            length = struct.unpack('<I', cut(data, offset, 4))[0]
            cut(data, offset + 4, length)
            offset += 4 + length
        offset += 4
        header, _, count = struct.unpack('<H64sI', cut(data, offset, 70))
        require(header >= 98 and 2 <= count <= MAX_FILES + 2, 'invalid SPS directory')
        cut(data, offset, header)
        offset += header
        files = []
        for _ in range(count - 2):
            header, raw_name, length = struct.unpack('<H64sI', cut(data, offset, 70))
            require(header >= 98, 'invalid SPS member header')
            cut(data, offset, header)
            offset += header
            files.append((name(raw_name), cut(data, offset, length)))
            offset += length
        require(len(data) - offset == 4, 'SPS trailing checksum/length mismatch')
        return files
    if data.startswith(b'\0VSP'):
        require(struct.unpack('<I', cut(data, 4, 4))[0] == 0 and
                struct.unpack('<I', cut(data, 60, 4))[0] == 2, 'only PS2 PSV exports are supported')
        count = struct.unpack('<I', cut(data, 100, 4))[0]
        require(0 < count <= MAX_FILES, 'invalid PSV member count')
        table_end = 160 + count * 60
        cut(data, 0, table_end)
        files, ranges = [], []
        for i in range(count):
            record = cut(data, 160 + i * 60, 60)
            length, mode = struct.unpack_from('<II', record, 16)
            offset = struct.unpack_from('<I', record, 56)[0]
            require(mode & 0x10 and offset >= table_end, 'invalid PSV file entry')
            require(all(offset + length <= a or offset >= b for a, b in ranges), 'overlapping PSV files')
            ranges.append((offset, offset + length))
            files.append((name(record[24:56]), cut(data, offset, length)))
        return files
    if len(data) >= 1536 and struct.unpack_from('<H', data)[0] & 0x20:
        # PSU has three 512-byte directory entries, then file entries/data
        # padded to 1024 bytes. Never infer this from a .ps2 card image.
        count = struct.unpack_from('<I', data, 4)[0]
        require(2 <= count <= MAX_FILES + 2, 'invalid PSU file count')
        for offset in (512, 1024):
            require(struct.unpack('<H', cut(data, offset, 2))[0] & 0x20, 'invalid PSU directory')
        files, offset = [], 1536
        for _ in range(count - 2):
            record = cut(data, offset, 512)
            require(struct.unpack_from('<H', record)[0] & 0x10, 'PSU member is not a file')
            length = struct.unpack_from('<I', record, 4)[0]
            offset += 512
            files.append((name(record[64:512]), cut(data, offset, length)))
            offset += ((length + 1023) // 1024) * 1024
        require(offset == len(data), 'PSU member count/length mismatch')
        return files
    raise ValueError('unsupported input; export the FFNY save from a PCSX2 card as .psu, or use a save folder')
