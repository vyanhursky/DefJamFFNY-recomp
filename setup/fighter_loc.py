"""Bounded LOCH/LOCT/LOCL composition for native fighter name registration.

Numeric lookup keys are internal adapter bindings, not public mod identities.
Existing language strings and opaque headers survive additions unchanged. This
module does not install an overlay or imply that native UI bounds are fixed.
"""
import struct

MAX_BYTES = 32 * 1024**2
MAX_STRINGS = 65536
MAX_LOCALES = 16
MAX_TEXT_BYTES = 16384


class LocError(ValueError):
    pass


def check(value, message):
    if not value:
        raise LocError(message)


class Localization:
    def __init__(self, data):
        check(isinstance(data, bytes) and 20 <= len(data) <= MAX_BYTES, 'Invalid LOC size')
        self.data = data
        check(data[:4] == b'LOCH', 'Missing LOCH header')
        header_size, reserved, count = self.words(4, 3)
        check(1 <= count <= MAX_LOCALES and header_size == 16 + count * 4 and reserved == 0,
              'Unsupported LOCH layout')
        self.header_size = header_size
        offsets = self.words(16, count)
        check(offsets[0] >= header_size and all(a < b for a, b in zip(offsets, offsets[1:])),
              'Invalid LOC chunk offsets')
        self.blocks, self.texts = [], []
        for offset, end in zip(offsets, (*offsets[1:], len(data))):
            check(offset + 16 <= end <= len(data) and data[offset:offset + 4] == b'LOCL', 'Invalid LOCL chunk')
            size, reserved, total = self.words(offset + 4, 3)
            check(size == end - offset and reserved == 0 and total <= MAX_STRINGS, 'Invalid LOCL size/count')
            positions = self.words(offset + 16, total)
            payload = 16 + total * 4
            check(all(payload <= p <= size - 2 and p % 2 == 0 for p in positions)
                  and all(a <= b for a, b in zip(positions, positions[1:])), 'Invalid LOCL string offsets')
            strings = []
            for position in positions:
                start = offset + position
                stop = start
                while stop + 2 <= end and stop - start <= MAX_TEXT_BYTES and data[stop:stop + 2] != b'\0\0':
                    stop += 2
                check(stop + 2 <= end and stop - start <= MAX_TEXT_BYTES and data[stop:stop + 2] == b'\0\0',
                      'Unterminated/oversized LOC string')
                try:
                    strings.append(data[start:stop].decode('utf-16le'))
                except UnicodeDecodeError as error:
                    raise LocError('Invalid UTF-16 LOC string') from error
            self.blocks.append((offset, end, positions))
            self.texts.append(tuple(strings))
        check(len({len(t) for t in self.texts}) == 1, 'Locale counts disagree')
        self.count = len(self.texts[0])
        self.index_header = None
        self.keys = {}
        if offsets[0] != header_size:
            check(data[header_size:header_size + 4] == b'LOCT'
                  and self.words(header_size + 4, 1)[0] == 16
                  and offsets[0] - header_size == 16 + self.count * 8,
                  'Unsupported LOCT layout')
            self.index_header = data[header_size:header_size + 16]
            pairs = tuple(struct.iter_unpack('<II', data[header_size + 16:offsets[0]]))
            check(all(a[0] < b[0] for a, b in zip(pairs, pairs[1:])), 'Unsorted/duplicate LOC keys')
            check({v for _, v in pairs} == set(range(self.count)), 'Invalid LOC key/index mapping')
            self.keys = dict(pairs)

    def words(self, offset, count):
        check(0 <= count <= MAX_STRINGS and 0 <= offset <= len(self.data)
              and count * 4 <= len(self.data) - offset, 'LOC range exceeds image')
        return struct.unpack_from(f'<{count}I', self.data, offset)

    def lookup(self, key, locale=0):
        check(type(locale) is int and 0 <= locale < len(self.texts), 'Invalid locale index')
        check(key in self.keys, 'Unknown LOC lookup key')
        return self.texts[locale][self.keys[key]]

    def merge(self, additions):
        """Append explicit numeric-key strings after language changes have applied.

        A string value supplies the same fallback text to every locale; a list
        supplies exactly one text per locale. Existing translations cannot be
        overwritten. Reapplying identical additions is an exact byte no-op.
        """
        check(isinstance(additions, dict) and len(additions) <= MAX_STRINGS, 'Invalid LOC additions')
        check(self.index_header is not None or not additions, 'LOC has an external key table; cannot add keys')
        normalized = {}
        for key, value in additions.items():
            check(type(key) is int and 0 <= key <= 0xffffffff, 'Invalid LOC lookup key')
            values = [value] * len(self.texts) if isinstance(value, str) else value
            check(isinstance(values, (list, tuple)) and len(values) == len(self.texts), 'Invalid localized text list')
            encoded = []
            for text in values:
                check(isinstance(text, str) and '\0' not in text, 'Invalid LOC text')
                try:
                    raw = text.encode('utf-16le') + b'\0\0'
                except UnicodeEncodeError as error:
                    raise LocError('Invalid UTF-16 LOC text') from error
                check(len(raw) <= MAX_TEXT_BYTES, 'LOC text exceeds budget')
                encoded.append(raw)
            if key in self.keys:
                check(all(self.lookup(key, i) == text for i, text in enumerate(values)), 'Conflicting LOC lookup key')
            else:
                normalized[key] = encoded
        if not normalized:
            return self.data
        check(self.count + len(normalized) <= MAX_STRINGS, 'LOC string count exceeds budget')
        ordered = sorted(normalized)
        keys = dict(self.keys)
        keys.update({key: self.count + i for i, key in enumerate(ordered)})
        output = bytearray(self.data[:self.header_size])
        output.extend(self.index_header)
        output.extend(b''.join(struct.pack('<II', key, value) for key, value in sorted(keys.items())))
        for locale, (start, end, old_positions) in enumerate(self.blocks):
            struct.pack_into('<I', output, 16 + locale * 4, len(output))
            old_payload_start = start + 16 + self.count * 4
            payload = bytearray(self.data[old_payload_start:end])
            positions = [p + len(ordered) * 4 for p in old_positions]
            new_header = 16 + (self.count + len(ordered)) * 4
            for key in ordered:
                positions.append(new_header + len(payload))
                payload.extend(normalized[key][locale])
            block_size = new_header + len(payload)
            check(len(output) + block_size <= MAX_BYTES, 'Expanded LOC exceeds image budget')
            output.extend(b'LOCL' + struct.pack('<III', block_size, 0, len(positions)))
            output.extend(struct.pack(f'<{len(positions)}I', *positions))
            output.extend(payload)
        rebuilt = Localization(bytes(output))
        for locale, strings in enumerate(self.texts):
            check(rebuilt.texts[locale][:self.count] == strings, 'Existing translations changed')
        return bytes(output)
