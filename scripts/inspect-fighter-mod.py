#!/usr/bin/env python3
"""Inspect a legacy fighter .mod ZIP without installing or extracting its assets.

    python scripts/inspect-fighter-mod.py "path/to/pack.mod" --output logs/fighter-mod.json
    python scripts/inspect-fighter-mod.py "path/to/pack.mod" --dump /path/to/extracted

Reports metadata/hashes only. This is a research diagnostic, not a compatibility
validator: a successful inspection does not mean this runtime can play the mod.
Reads every payload to check ZIP CRC and SHA-256, with bounded archive sizes.
"""
import argparse
import collections
import configparser
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import zipfile

MAX_FILES = 10000
MAX_FILE = 256 * 1024**2
MAX_TOTAL = 1024**3
MAX_TEXT = 64 * 1024


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_entries(infos):
    """Validate portable relative names and expansion bounds before payload reads."""
    require(len(infos) <= MAX_FILES, 'Too many archive entries')
    require(sum(i.file_size for i in infos) <= MAX_TOTAL, 'Archive expands too far')
    seen = set()
    files = set()
    for info in infos:
        name = info.filename
        require(info.orig_filename == name, 'Noncanonical archive path')
        parts = name.rstrip('/').split('/')
        require(name and '\\' not in name and not name.startswith('/'), 'Unsafe archive path')
        for part in parts:
            require(part and part not in ('.', '..') and not re.search(r'[<>:"|?*\x00-\x1f]', part)
                    and not part.endswith((' ', '.')), 'Unsafe archive path')
            require(not re.fullmatch(r'(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?', part,
                                     flags=re.I), 'Reserved archive path')
        key = '/'.join(parts).casefold()
        require(key not in seen, 'Duplicate or case-colliding archive path')
        seen.add(key)
        mode = info.external_attr >> 16
        require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'Special archive entry')
        require(not info.flag_bits & 1, 'Encrypted archive entry')
        require(0 <= info.file_size <= MAX_FILE, 'Oversized archive entry')
        if not info.is_dir():
            files.add(key)
    for key in seen:
        parts = key.split('/')
        require(not any('/'.join(parts[:i]) in files for i in range(1, len(parts))),
                'File/directory archive collision')


def mapping(text, activation=False):
    result = []
    ids = set()
    for line in text.splitlines():
        words = line.split('#', 1)[0].split()
        if not words:
            continue
        require(len(words) in ((3, 4) if activation else (3,)), 'Malformed runtime mapping')
        core = int(words[0])
        require(0 < core < 256 and core not in ids, 'Duplicate or out-of-range core ID')
        ids.add(core)
        if activation:
            require(all(re.fullmatch(r'[A-Za-z0-9_]{1,31}', x) for x in words[1:3]),
                    'Invalid activation archive name')
            require(len(words) == 3 or words[3] == 'cri', 'Unknown activation annotation')
            result.append(dict(core_id=core, plan=words[1], ending=words[2],
                               cry_annotation=len(words) == 4))
        else:
            donor, voice = map(int, words[1:])
            require(0 <= donor < 104 and 0 <= voice < 1024, 'Out-of-range donor or voice')
            result.append(dict(core_id=core, donor_id=donor, voice_id=voice))
    return result


def chunks(data):
    """Summarize a length-prefixed stream (used by motion/main_all.dat)."""
    result = collections.Counter()
    offset = 0
    while offset < len(data):
        require(offset + 8 <= len(data), 'Truncated chunk header')
        tag = data[offset:offset + 4]
        size = struct.unpack_from('<I', data, offset + 4)[0]
        require(all(32 <= x < 127 for x in tag), 'Invalid chunk tag')
        require(size <= len(data) - offset - 8, 'Chunk exceeds payload')
        result[tag.decode('ascii')] += 1
        offset += 8 + size
    return dict(sorted(result.items()))


def sod_header(data):
    """Only header/section observations; deliberately not a SOD object decoder."""
    require(len(data) >= 24 and data[:4] == b'SODB', 'Invalid SODB header')
    version, schema_hash, schema, objects, strings = struct.unpack_from('<5I', data, 4)
    require(24 <= schema < objects < strings <= len(data) - 8, 'Invalid SODB offsets')
    return dict(version=version, schema_hash=f'{schema_hash:08x}',
                schema_offset=schema, data_offset=objects, string_table_offset=strings,
                section_tags=[data[x:x + 4].decode('ascii') for x in (schema, objects, strings)])


def inspect(path, dump=None):
    with Path(path).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(archive_sha256=digest, archive_bytes=Path(path).stat().st_size,
                  runtime_compatibility='not established', entries=[], extensions={},
                  top_level={}, mappings={}, observations={})
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        validate_entries(infos)
        ext, top = collections.Counter(), collections.Counter()
        for info in infos:
            if info.is_dir():
                continue
            name = info.filename
            hasher = hashlib.sha256()
            observed = 0
            with archive.open(info) as stream:
                while block := stream.read(1024 * 1024):
                    observed += len(block)
                    require(observed <= info.file_size, 'Payload exceeds declared size')
                    hasher.update(block)
            require(observed == info.file_size, 'Payload size mismatch')
            row = dict(path=name, bytes=observed, compressed_bytes=info.compress_size,
                       sha256=hasher.hexdigest())
            if dump:
                base = Path(dump).joinpath(*PurePosixPath(name).parts)
                if base.is_file():
                    with base.open('rb') as stream:
                        base_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
                    row.update(loose_baseline='identical' if base_sha == row['sha256'] else 'changed',
                               baseline_sha256=base_sha, baseline_bytes=base.stat().st_size)
                else:
                    row['loose_baseline'] = 'absent (may be an archive member)'
            report['entries'].append(row)
            ext[PurePosixPath(name).suffix.lower()] += 1
            top[name.split('/')[0]] += 1
        names = {i.filename for i in infos}
        if 'mod.ini' in names:
            require(archive.getinfo('mod.ini').file_size <= MAX_TEXT, 'Oversized mod.ini')
            parser = configparser.ConfigParser(interpolation=None)
            parser.read_string(archive.read('mod.ini').decode('utf-8-sig'))
            report['legacy_metadata'] = dict(parser['mod'])
        for name, activation in [('coreid.txt', False), ('blazin_activation.txt', True)]:
            if name in names:
                require(archive.getinfo(name).file_size <= MAX_TEXT, 'Oversized runtime mapping')
                report['mappings'][name] = mapping(archive.read(name).decode('utf-8-sig'), activation)
        for name, parser in [('motion/main_all.dat', chunks), ('assets/djv2.sod', sod_header)]:
            if name in names:
                report['observations'][name] = parser(archive.read(name))
                if dump and (Path(dump) / name).is_file():
                    report['observations']['baseline/' + name] = parser((Path(dump) / name).read_bytes())
        activations = report['mappings'].get('blazin_activation.txt', [])
        report['activation_archives_missing'] = sorted({f'assets/v2ta/{row[key]}.viv'
            for row in activations for key in ('plan', 'ending')
            if f'assets/v2ta/{row[key]}.viv' not in names})
        report['extensions'] = dict(sorted(ext.items()))
        report['top_level'] = dict(sorted(top.items()))
        report['file_count'] = len(report['entries'])
        report['unpacked_bytes'] = sum(row['bytes'] for row in report['entries'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--dump', type=Path, help='Optional extracted baseline, read only')
    parser.add_argument('--output', type=Path, help='New metadata-only JSON file; refuses overwrite')
    args = parser.parse_args()
    try:
        report = inspect(args.archive, args.dump)
        payload = json.dumps(report, indent=2, ensure_ascii=True) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(payload)
            print(f"{report['file_count']} files; {report['unpacked_bytes']} unpacked bytes; "
                  f"SHA-256 {report['archive_sha256']}; report: {args.output}")
        else:
            print(payload, end='')
    except (OSError, ValueError, KeyError, UnicodeError, zipfile.BadZipFile,
            configparser.Error, NotImplementedError) as error:
        parser.exit(1, f'Inspection failed: {error}\n')


if __name__ == '__main__':
    main()
