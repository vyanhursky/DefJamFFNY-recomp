"""Verified language-base composition before runtime-owned fighter presentation.

This consumes the existing DJDELTA1 data format, never a fighter-supplied movie
or executable callback. The caller supplies the supported dump's pinned hash.
Nested replacements preserve the language runtime's directory/append order so
the resulting bytes can be attested against its independently built cache.
"""
import hashlib
import struct

from fighter_archive import Archive, MAX_ARCHIVE, store, valid_name
from fighter_assets import AssetError, MAX_ASSET, unpack
from fighter_registry import fingerprint

MAX_EDITS = 256
MAX_DELTA_BYTES = 256 * 1024**2
MAX_OPERATIONS = 1_000_000
MAX_DEPTH = 8


def require(condition, message):
    if not condition:
        raise AssetError(message)


def apply_delta(source, delta, maximum=MAX_ASSET):
    require(isinstance(source, bytes) and len(source) <= maximum
            and isinstance(delta, bytes) and 81 <= len(delta) <= MAX_DELTA_BYTES
            and delta[:8] == b'DJDELTA1', 'Invalid language composition delta')
    before, after = struct.unpack_from('<II', delta, 8)
    require(len(source) == before and hashlib.sha256(source).digest() == delta[16:48],
            'Language composition source differs from its verified delta')
    require(after <= maximum, 'Language composition output exceeds budget')
    output, at, operations = bytearray(), 80, 0
    while True:
        require(at < len(delta), 'Language composition delta has no end marker')
        opcode = delta[at]; at += 1
        if opcode == 0:
            break
        operations += 1
        require(operations <= MAX_OPERATIONS, 'Language composition operation budget')
        if opcode == 1:
            require(at + 8 <= len(delta), 'Truncated language copy operation')
            offset, size = struct.unpack_from('<II', delta, at); at += 8
            require(offset <= len(source) and size <= len(source) - offset
                    and len(output) + size <= after, 'Language copy exceeds bounds')
            output += source[offset:offset + size]
        elif opcode == 2:
            require(at + 4 <= len(delta), 'Truncated language literal operation')
            size, = struct.unpack_from('<I', delta, at); at += 4
            require(size <= len(delta) - at and len(output) + size <= after,
                    'Language literal exceeds bounds')
            output += delta[at:at + size]; at += size
        else:
            raise AssetError('Unknown language composition operation')
    require(at == len(delta) and len(output) == after and hashlib.sha256(output).digest() == delta[48:80],
            'Language composition output hash, length or trailing data differs')
    return bytes(output)


def _compose(source, edits, maximum):
    whole = [delta for parts, delta in edits if not parts]
    if whole:
        require(len(edits) == 1, 'Language target conflicts with an edit inside it')
        return apply_delta(source, whole[0], maximum)
    archive = Archive(source)
    grouped = {}
    for parts, delta in edits:
        entry = archive.by_name.get(parts[0].lower())
        require(entry is not None, 'Language composition target is missing')
        grouped.setdefault(entry.name, []).append((parts[1:], delta))
    output, directory = bytearray(source), 16
    for entry in archive.entries:
        if entry.name in grouped:
            original = archive.read(entry.name)
            compressed = len(original) >= 2 and int.from_bytes(original[:2], 'big') & 0x3eff == 0x10fb
            rebuilt = _compose(unpack(original), grouped[entry.name], MAX_ASSET)
            replacement = store(rebuilt) if compressed else rebuilt
            padding = -len(output) % archive.alignment
            require(len(output) + padding + len(replacement) <= maximum,
                    'Language composed archive exceeds budget')
            output += bytes(padding)
            struct.pack_into('>II', output, directory, len(output), len(replacement))
            output += replacement
        directory += 9 + len(entry.name)
    struct.pack_into('<I', output, 4, len(output))
    result = bytes(output)
    Archive(result)
    return result


def language_base(source, edits, expected_sha256):
    """Return composed bytes plus provenance; no cache is trusted by its name.

    edits are (tuple of archive entry names, delta bytes), relative to one
    verified original file. Empty paths address that entire file. A later
    fighter adapter must validate its own semantic input and attest its output.
    """
    require(isinstance(source, bytes) and 0 < len(source) <= MAX_ARCHIVE
            and hashlib.sha256(source).hexdigest() == expected_sha256,
            'Language composition requires the verified original source')
    require(isinstance(edits, list) and 0 < len(edits) <= MAX_EDITS,
            'Invalid language composition edit population')
    paths, total, provenance = set(), 0, []
    for edit in edits:
        require(isinstance(edit, tuple) and len(edit) == 2, 'Invalid language composition edit')
        parts, delta = edit
        require(isinstance(parts, tuple) and len(parts) <= MAX_DEPTH, 'Invalid language composition depth')
        for part in parts:
            valid_name(part)
            require(len(part) < 256 and '|' not in part, 'Invalid language composition target')
        identity = tuple(part.lower() for part in parts)
        require(identity not in paths and isinstance(delta, bytes), 'Duplicate language composition target')
        paths.add(identity); total += len(delta)
        require(total <= MAX_DELTA_BYTES, 'Language composition delta byte budget')
        provenance.append({'target': '|'.join(identity), 'delta_sha256': hashlib.sha256(delta).hexdigest()})
    result = _compose(source, edits, MAX_ARCHIVE)
    receipt = {'schema': 'fighter-language-base-1', 'source_sha256': expected_sha256,
               'base_sha256': hashlib.sha256(result).hexdigest(),
               'edits': sorted(provenance, key=lambda row: row['target'])}
    receipt['cache_key'] = fingerprint(receipt)
    return result, receipt
