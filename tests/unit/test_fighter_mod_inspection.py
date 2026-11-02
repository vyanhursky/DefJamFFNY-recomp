"""Synthetic inputs only: archive/path bounds and legacy metadata observations."""
import importlib.util
from pathlib import Path
import stat
import struct
import zipfile

import pytest

spec = importlib.util.spec_from_file_location('fighter_inspection',
    Path(__file__).resolve().parents[2] / 'scripts/inspect-fighter-mod.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.mark.parametrize('name', ['../a', '/a', 'C:/a', 'a\\b', 'a//b', 'a/./b',
                                  'a./b', 'NUL.txt', 'a/x:y', 'a/line\nfeed'])
def test_unsafe_names(name):
    with pytest.raises(ValueError):
        mod.validate_entries([zipfile.ZipInfo(name)])


def test_links_collisions_and_size():
    link = zipfile.ZipInfo('a')
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    for infos in [[link], [zipfile.ZipInfo('A'), zipfile.ZipInfo('a')],
                  [zipfile.ZipInfo('a'), zipfile.ZipInfo('a/b')]]:
        with pytest.raises(ValueError):
            mod.validate_entries(infos)
    large = zipfile.ZipInfo('big')
    large.file_size = mod.MAX_FILE + 1
    with pytest.raises(ValueError):
        mod.validate_entries([large])


def test_mapping_validation():
    assert mod.mapping('142 18 600 # donor\n')[0]['voice_id'] == 600
    assert mod.mapping('142 BZ_TEST BY_TEST cri', True)[0]['cry_annotation']
    for text in ['142 18 600\n142 19 601', '256 18 600', '142 104 600', '142 18 -1', 'bad']:
        with pytest.raises(ValueError):
            mod.mapping(text)
    with pytest.raises(ValueError):
        mod.mapping('142 BZ_TEST BY_TEST unknown', True)


def test_chunk_bounds():
    assert mod.chunks(b'WPAR' + struct.pack('<I', 3) + b'abc') == {'WPAR': 1}
    for data in [b'WPAR', b'WPAR' + struct.pack('<I', 4) + b'abc']:
        with pytest.raises(ValueError):
            mod.chunks(data)


def test_encryption_and_aggregate_budget(monkeypatch):
    encrypted = zipfile.ZipInfo('secret')
    encrypted.flag_bits = 1
    with pytest.raises(ValueError):
        mod.validate_entries([encrypted])
    monkeypatch.setattr(mod, 'MAX_TOTAL', 10)
    entries = [zipfile.ZipInfo('a'), zipfile.ZipInfo('b')]
    for entry in entries:
        entry.file_size = 6
    with pytest.raises(ValueError):
        mod.validate_entries(entries)


def test_payload_crc_failure(tmp_path):
    archive = tmp_path / 'corrupt.mod'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as z:
        z.writestr('payload.txt', b'synthetic payload')
    data = bytearray(archive.read_bytes())
    offset = data.index(b'synthetic payload')
    data[offset] ^= 1
    archive.write_bytes(data)
    with pytest.raises(zipfile.BadZipFile):
        mod.inspect(archive)


def test_sod_header_bounds():
    data = b'SODB' + struct.pack('<5I', 2, 1, 24, 32, 40) + b'SKMA0000DATA0000STRT0000'
    assert mod.sod_header(data)['section_tags'] == ['SKMA', 'DATA', 'STRT']
    with pytest.raises(ValueError):
        mod.sod_header(data[:40])


def test_inspection_metadata_and_baseline(tmp_path):
    archive = tmp_path / 'test.mod'
    dump = tmp_path / 'dump'
    dump.mkdir()
    (dump / 'same.txt').write_bytes(b'synthetic')
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('mod.ini', '[mod]\nnom=Test\nversion=1\n')
        z.writestr('same.txt', b'synthetic')
        z.writestr('coreid.txt', '142 18 600\n')
        z.writestr('blazin_activation.txt', '142 BZ_TEST BY_TEST\n')
    report = mod.inspect(archive, dump)
    assert report['file_count'] == 4
    assert report['legacy_metadata']['nom'] == 'Test'
    assert report['entries'][1]['loose_baseline'] == 'identical'
    assert report['activation_archives_missing'] == ['assets/v2ta/BY_TEST.viv', 'assets/v2ta/BZ_TEST.viv']
    assert report['runtime_compatibility'] == 'not established'
    assert not (tmp_path / 'mod.ini').exists()
