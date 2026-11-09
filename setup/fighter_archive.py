"""Bounded BIG composition for runtime-owned adapters, without movie edits.

The source must be the player's verified retail/language-composed archive.
Fighter packages do not supply selection movies or arbitrary BIG replacements.
Payloads and the opaque directory footer are retained byte for byte; expanding
the directory shifts the original payload block by one aligned displacement.
"""
from dataclasses import dataclass
import struct

from fighter_assets import AssetError, unpack

MAX_ARCHIVE = 512 * 1024**2
MAX_ENTRIES = 100_000


@dataclass(frozen=True)
class Entry:
    name: str
    offset: int
    size: int


class Archive:
    def __init__(self, data, *, native_separators=False):
        # Some verified retail audio directories use backslashes. Preserve
        # their exact names on disk while checking aliases canonically.
        self.native_separators = native_separators
        if not isinstance(data, bytes) or not 16 <= len(data) <= MAX_ARCHIVE or data[:4] not in (b'BIGF', b'BIG4'):
            raise AssetError('Invalid BIG envelope or archive budget')
        if struct.unpack_from('<I', data, 4)[0] != len(data):
            raise AssetError('BIG size does not match its envelope')
        count, header_end = struct.unpack_from('>II', data, 8)
        if not 0 < count <= MAX_ENTRIES or not 16 <= header_end <= len(data):
            raise AssetError('BIG directory budget or header bounds')
        entries, names, at = [], set(), 16
        for _ in range(count):
            if at + 9 > header_end:
                raise AssetError('Truncated BIG directory')
            offset, size = struct.unpack_from('>II', data, at)
            end = data.find(b'\0', at + 8, min(header_end, at + 8 + 513))
            if end < 0:
                raise AssetError('Unterminated or excessive BIG name')
            try:
                name = data[at + 8:end].decode('ascii')
            except UnicodeError as error:
                raise AssetError('BIG names must be ASCII') from error
            canonical = name.replace('\\', '/') if native_separators else name
            valid_name(canonical)
            if canonical.lower() in names or offset < header_end or offset + size > len(data):
                raise AssetError('Duplicate BIG name or out-of-bounds payload')
            names.add(canonical.lower())
            entries.append(Entry(name, offset, size))
            at = end + 1
        ranges = sorted((e.offset, e.offset + e.size) for e in entries if e.size)
        if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
            raise AssetError('Overlapping BIG payloads')
        first = min(e.offset for e in entries)
        if at > header_end or header_end > first:
            raise AssetError('BIG directory overlaps its payload')
        alignment = 4096
        while alignment > 1 and any(e.offset % alignment for e in entries):
            alignment //= 2
        self.data, self.entries = data, tuple(entries)
        self.directory_end, self.header_end, self.first = at, header_end, first
        self.alignment = alignment
        self.by_name = {self.name_key(e.name): e for e in entries}

    def name_key(self, name):
        return (name.replace('\\', '/') if self.native_separators else name).lower()

    def read(self, name):
        try:
            entry = self.by_name[self.name_key(name)]
        except KeyError as error:
            raise AssetError('Missing BIG entry: ' + name) from error
        return self.data[entry.offset:entry.offset + entry.size]

    def compose(self, additions=None, renames=None, replacements=None):
        additions, renames, replacements = additions or {}, renames or {}, replacements or {}
        if not additions and not renames and not replacements:
            return self.data
        if set(renames) - {e.name for e in self.entries}:
            raise AssetError('Cannot rename a missing BIG entry')
        if set(replacements) - {e.name for e in self.entries}:
            raise AssetError('Cannot replace a missing BIG entry')
        output_names = [renames.get(e.name, e.name) for e in self.entries] + sorted(additions)
        for name in output_names:
            valid_name(self.name_key(name) if self.native_separators else name)
        if len(set(self.name_key(name) for name in output_names)) != len(output_names):
            raise AssetError('BIG composition has conflicting names')
        if len(output_names) > MAX_ENTRIES or any(not isinstance(value, bytes) for value in [*additions.values(), *replacements.values()]):
            raise AssetError('BIG composition budget or payload type')
        directory_size = 16 + sum(9 + len(name) for name in output_names)
        # Preserve the footer (e.g. L253) and original padding as opaque data.
        tail = self.data[self.directory_end:self.first]
        new_first = directory_size + len(tail)
        new_first += -new_first % self.alignment
        shift = new_first - self.first
        total = len(self.data) + shift
        added_entries, replaced_entries, appended = [], {}, []
        for name in sorted(replacements):
            total += -total % self.alignment
            entry = Entry(renames.get(name, name), total, len(replacements[name]))
            replaced_entries[name] = entry
            appended.append((entry, replacements[name]))
            total += entry.size
        for name in sorted(additions):
            total += -total % self.alignment
            added_entries.append(Entry(name, total, len(additions[name])))
            appended.append((added_entries[-1], additions[name]))
            total += len(additions[name])
        if total > MAX_ARCHIVE:
            raise AssetError('Composed BIG exceeds archive budget')
        header = bytearray(self.data[:16])
        struct.pack_into('<I', header, 4, total)
        struct.pack_into('>II', header, 8, len(output_names), directory_size + self.header_end - self.directory_end)
        output = header
        updated = [replaced_entries.get(e.name, Entry(renames.get(e.name, e.name), e.offset + shift, e.size)) for e in self.entries] + added_entries
        for entry in updated:
            output += struct.pack('>II', entry.offset, entry.size) + entry.name.encode('ascii') + b'\0'
        output += tail
        output += bytes(new_first - len(output))
        output += self.data[self.first:]
        for entry, data in appended:
            output += bytes(entry.offset - len(output)) + data
        result = bytes(output)
        Archive(result, native_separators=self.native_separators)
        return result


def valid_name(name):
    if not isinstance(name, str) or not 1 <= len(name) <= 512 or not name.isascii() or '\\' in name:
        raise AssetError('Invalid BIG entry name')
    if any(part in ('', '.', '..') for part in name.split('/')) or any(ord(c) < 32 or c in ':\0' for c in name):
        raise AssetError('Unsafe BIG entry name')


def store(data):
    """Literal-only RefPack, matching the native decoder's standard format."""
    if not 0 < len(data) <= 64 * 1024**2:
        raise AssetError('Portrait envelope exceeds asset budget')
    width = 3 if len(data) < 1 << 24 else 4
    output = bytearray(b'\x10\xfb' if width == 3 else b'\x90\xfb') + len(data).to_bytes(width, 'big')
    at = 0
    while len(data) - at >= 4:
        size = min(112, (len(data) - at) & ~3)
        output.append(0xe0 + ((size - 4) >> 2))
        output += data[at:at + size]
        at += size
    output.append(0xfc + len(data) - at)
    return bytes(output + data[at:])


def portrait_aliases(data, pairs, *, results=False,extended=()):
    """Map {custom selection token: retail portrait token}; never alias identity.

    Portrait envelopes are renamed together without changing their payloads.
    Custom result logos use the verified original blank movie so donor branding
    cannot obscure custom labels. Movies must not embed their file basename.
    An occupied destination is a conflict, including another mod's same path.
    """
    archive, additions = Archive(data), {}
    if type(extended) not in (set,frozenset,tuple,list) or not set(extended)<=set(pairs):
        raise AssetError('Extended portraits require owned selection aliases')
    for target, donor in sorted(pairs.items()):
        if not all(type(value) is int and 0 <= value <= 0x7ffffffe for value in (target, donor)) or target == donor:
            raise AssetError('Invalid portrait selection binding')
        families = [('screens/portrait/p_CF/', 'p_cf_', 1)]
        if results:
            # GetMatchSummary's fid is used directly; selector portraits alone
            # add one. These are different namespaces in the original movies.
            families += [('screens/portrait/t_MS/', 't_MS_', 0), ('screens/portrait/', 'l_MS_', 0)]
        if target in extended:
            # oldMLoad's verified REVERSE_CHARS list contains only retail IDs
            # 7..82. Appended logical identities start100 and need no Rvariant.
            if target<100: raise AssetError('Extended loading portraits require appended logical identities')
            families += [('screens/portrait/l_CF/','l_CF_',0),
                         ('screens/match/3_fighters/','p_ML_',1),('screens/match/3_fighters/','l_ML_',0)]
        for prefix, stem, increment in families:
            for players in (2, 3, 4):
                old, new = f'{stem}{donor + increment}_{players}p', f'{stem}{target + increment}_{players}p'
                path = prefix + new + '.big'
                if path.lower() in archive.by_name or path in additions:
                    raise AssetError('Portrait alias destination already owned: ' + path)
                # Custom names use our text field. Loading a donor logo would
                # overwrite an early _visible=false when that movie arrives.
                # The original blank movie has no model/texture dependencies.
                if stem == 'l_MS_' and target not in extended:
                    old = 'empty2'
                    inner = Archive(unpack(archive.read('screens/trans/empty2.big')))
                    expected = {old + suffix for suffix in ('.apt', '.const')}
                else:
                    inner = Archive(unpack(archive.read(prefix + old + '.big')))
                    expected = {old + suffix for suffix in ('.apt', '.const', '.o', '.xsh')}
                if {entry.name for entry in inner.entries} != expected:
                    raise AssetError('Unsupported donor portrait envelope')
                if any(old.encode('ascii') in inner.read(name) for name in expected):
                    raise AssetError('Portrait has embedded filename references; needs a typed adapter')
                result = inner.compose(renames={name: new + name[len(old):] for name in expected})
                additions[path] = store(result)
    return archive.compose(additions=additions)
