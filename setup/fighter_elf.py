"""Bounded inspection of the game's data-only ELF model/face containers.

These assets use a relocatable ELF32 little-endian MIPS envelope. They contain
EAGL data, symbols and pointer relocations, not CPU executable sections. This
checks the envelope and relocation graph; EAGL geometry/skeleton semantics are
a separate acceptance gate. Imports must come from a verified local baseline or
an explicitly resolved data library, never arbitrary native addresses.
"""
import hashlib
import struct

MAX_BYTES = 64 * 1024**2
MAX_SYMBOLS = 262144
MAX_RELOCATIONS = 1048576
MAX_STRING = 4096
SECTION_NAMES = ('', '.data', '.shstrtab', '.strtab', '.symtab', '.rel.data')


class ModelError(ValueError):
    pass


def check(value, message):
    if not value:
        raise ModelError(message)


class Model:
    def __init__(self, data):
        check(isinstance(data, bytes) and 52 <= len(data) <= MAX_BYTES, 'Invalid model size')
        self.data = data
        check(data[:16] == b'\x7fELF\x01\x01\x01' + bytes(9), 'Unsupported model ELF identification')
        kind, machine, version, entry, program, sections, flags, header, pw, pn, sw, sn, strings = self.unpack('<HHIIIIIHHHHHH', 16)
        check((kind, machine, version, entry, program, header, pw, pn, sw, sn, strings)
              == (1, 8, 1, 0, 0, 52, 0, 0, 40, 6, 2), 'Unsupported model ELF layout')
        check(flags == 0x20924000, 'Unsupported model ELF flags')
        self.range(sections, sn * sw)
        self.sections = [self.unpack('<10I', sections + i * sw) for i in range(sn)]
        check(self.sections[0] == (0,) * 10, 'Invalid null model section')
        # No executables, dynamic tables, constructors, TLS, arbitrary loader
        # extensions or absolute-address sections are accepted by this adapter.
        types = (0, 1, 3, 3, 2, 9)
        ranges = [(0, 52), (sections, sections + sn * sw)]
        for i, row in enumerate(self.sections[1:], 1):
            name, section_type, section_flags, address, offset, size, link, info, align, width = row
            check(section_type == types[i] and section_flags == (3 if i == 1 else 0) and address == 0,
                  'Unsupported or executable model section')
            check(align in (1, 4, 16) and offset % align == 0, 'Invalid model section alignment')
            self.range(offset, size)
            check(offset >= 52, 'Model section overlaps header')
            if size:
                ranges.append((offset, offset + size))
        check(all(a[1] <= b[0] for a, b in zip(sorted(ranges), sorted(ranges)[1:])), 'Overlapping model sections')
        for i, row in enumerate(self.sections):
            check(self.string(2, row[0]) == SECTION_NAMES[i], 'Unsupported model section name')
        check(self.sections[1][6:8] == (0, 0) and self.sections[1][9] == 0, 'Invalid model data section')
        for i in (2, 3):
            check(self.sections[i][6:8] == (0, 0) and self.sections[i][9] == 0, 'Invalid model string section')
        symbols = self.sections[4]
        check(symbols[6] == 3 and symbols[9] == 16 and symbols[5] % 16 == 0,
              'Invalid model symbol table')
        total = symbols[5] // 16
        check(0 < total <= MAX_SYMBOLS and symbols[7] <= total, 'Model symbol budget/order invalid')
        self.symbols, self.imports, self.exports = [], set(), set()
        for i in range(total):
            name, value, size, info, other, section = self.unpack('<IIIBBH', symbols[4] + i * 16)
            text = self.string(3, name)
            binding, symbol_type = info >> 4, info & 15
            check(binding in (0, 1, 2) and symbol_type in (0, 1, 3) and other == 0 and section in (0, 1),
                  'Unsupported executable/absolute model symbol')
            check((i < symbols[7]) == (binding == 0), 'Invalid model local/global symbol order')
            if not i:
                check((name, value, size, info, other, section) == (0,) * 6, 'Invalid null model symbol')
            elif section == 0:
                check(text and value == 0 and size == 0 and binding == 1 and symbol_type == 0,
                      'Invalid model import')
                self.imports.add(text)
            else:
                check(value <= self.sections[1][5] and size <= self.sections[1][5] - value,
                      'Model symbol exceeds data section')
                if binding in (1, 2):
                    check(text and text not in self.exports, 'Duplicate/empty model export')
                    self.exports.add(text)
            self.symbols.append((text, value, size, info, section))
        rel = self.sections[5]
        check(rel[6:8] == (4, 1) and rel[9] == 8 and rel[5] % 8 == 0
              and rel[5] // 8 <= MAX_RELOCATIONS, 'Invalid model relocation table')
        seen = set()
        for position in range(rel[4], rel[4] + rel[5], 8):
            offset, info = self.unpack('<II', position)
            symbol, method = info >> 8, info & 255
            check(method == 2 and 0 < symbol < total and offset % 4 == 0
                  and offset <= self.sections[1][5] - 4 and offset not in seen,
                  'Invalid/duplicate model pointer relocation')
            seen.add(offset)
            addend, = self.unpack('<I', self.sections[1][4] + offset)
            _, value, _, _, section = self.symbols[symbol]
            check((section == 0 and addend == 0) or (section == 1 and value + addend <= self.sections[1][5]),
                  'Model relocation points outside resolved data')
        self.relocations = len(seen)

    def range(self, offset, size):
        check(0 <= offset <= len(self.data) and 0 <= size <= len(self.data) - offset, 'Model range exceeds file')

    def unpack(self, format, offset):
        self.range(offset, struct.calcsize(format))
        return struct.unpack_from(format, self.data, offset)

    def string(self, section, offset):
        row = self.sections[section]
        check(0 <= offset < row[5], 'Model string index exceeds table')
        start = row[4] + offset
        end = self.data.find(b'\0', start, min(row[4] + row[5], start + MAX_STRING + 1))
        check(end >= start, 'Unterminated/oversized model symbol')
        try:
            text = self.data[start:end].decode('ascii')
        except UnicodeError as error:
            raise ModelError('Non-ASCII model symbol') from error
        check(all(32 <= ord(c) < 127 for c in text), 'Invalid model symbol characters')
        return text

    def require_imports(self, allowed):
        missing = self.imports - set(allowed)
        check(not missing, 'Unresolved or forbidden model imports: ' + ', '.join(sorted(missing)[:8]))

    def metadata(self):
        return {'format': 'fighter-elf-model-draft-1', 'sha256': hashlib.sha256(self.data).hexdigest(),
                'bytes': len(self.data), 'data_bytes': self.sections[1][5],
                'symbol_count': len(self.symbols), 'relocation_count': self.relocations,
                'imports': sorted(self.imports), 'exports': sorted(self.exports),
                'runtime_ready': False, 'pending': ['eagl-geometry-skeleton-material-validation', 'native-resource-acceptance']}
