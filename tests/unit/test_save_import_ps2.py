"""PS2 converter: invented save bytes only, never downloaded game/save fixtures."""
import importlib.util
import struct
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import ps2_save_containers as containers
from ps2_lzari import LzariDecoder

spec = importlib.util.spec_from_file_location('ps2_import', ROOT / 'scripts/save-import-ps2.py')
ps2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ps2)
xbox = ps2.xbox


def mc02(payload, kind='User'):
    identity = ('DJFFNY::%s 17 %d' % (kind, ps2.PS2_BUILD)).encode().ljust(64, b'\0')
    header = struct.pack('<4I', 0x4D433032, 92 + len(payload), 64, len(payload))
    header += struct.pack('<II', ps2.mc02_checksum(identity), ps2.mc02_checksum(payload))
    return header + struct.pack('<I', ps2.mc02_checksum(header)) + identity + payload


def story(name='DEMO'):
    payload = bytearray(ps2.PS2_PROFILE)
    payload[:16] = name.encode().ljust(16, b'\0')
    struct.pack_into('<II', payload, 0x14, 123456, 99)
    struct.pack_into('<5I', payload, 0xF0, 11, 22, 33, 44, 50)
    payload[0x134:0x138] = bytes([0, 1, 4, 91])
    payload[0x4D84:0x4D8E] = b'\x01\x12\x34\x56\x78\x01\0\0\0\x57'
    struct.pack_into('<38I', payload, 0x5560, *range(38))
    return bytes(payload)


def psu(raw, filename='BASLUS-21004DEMO'):
    def entry(mode, count, name):
        record = bytearray(512)
        struct.pack_into('<HI', record, 0, mode, 0)
        struct.pack_into('<I', record, 4, count)
        record[64:64+len(name)] = name.encode()
        return bytes(record)
    return (entry(0x20, 3, filename) + entry(0x20, 0, '.') + entry(0x20, 0, '..') +
            entry(0x10, len(raw), filename) + raw.ljust((len(raw)+1023)//1024*1024, b'\0'))


def cbs(raw):
    header = bytearray(296)
    header[:4] = b'CFU\0'
    record = bytearray(64)
    struct.pack_into('<IH', record, 16, len(raw), 0x10)
    record[32:51] = b'BASLUS-21004DEMO'.ljust(19,b'\0')
    body = zlib.compress(record + raw)
    struct.pack_into('<III', header, 8, 296, len(record)+len(raw), len(body))
    return bytes(header) + containers.rc4(body)


def native_options(save):
    title = save / 'UserData/45410049'
    target = title / xbox.folder_name('Options')
    target.mkdir(parents=True)
    data = ps2.signed_profile('Global', bytes(ps2.XBOX_OPTIONS))
    (target/'Options').write_bytes(data)
    (target/'SaveMeta.xbx').write_bytes(b'\xff\xfe' + 'Name=Options\r\n'.encode('utf-16le'))
    return target


def test_crc_independent_synthetic_vector():
    # Independent bitwise polynomial implementation, on invented bytes.
    data = b'checksum fixture with no game data'
    value = int.from_bytes(data[:4], 'big') ^ 0xFFFFFFFF
    for byte in data[4:]:
        for _ in range(8):
            value = ((value << 1) ^ (0x04C11DB7 if value & 0x80000000 else 0)) & 0xFFFFFFFF
        value ^= byte
    assert ps2.mc02_checksum(data) == value ^ 0xFFFFFFFF


def test_layout_keeps_flags_counter_lists_and_appearance():
    payload = story()
    name, parsed = ps2.parse_profile(mc02(payload))
    out = ps2.convert_story(parsed)
    assert name == 'DEMO' and xbox.header_fault(out) is None
    assert all(xbox.signatures_ok(out, xbox.PORT_KEY))
    data = out[140:]
    assert len(data) == 0x5904
    assert data[:0x17E] == payload[:0x17E]
    assert data[0x17E:0x4D88] == payload[0x184:0x4D8E]
    assert data[0x4D88:] == payload[0x4D90:]
    assert data[0x4D87] == 0x57  # do not drop/move this counter with padding
    assert struct.unpack_from('<38I', data, 0x5558) == tuple(range(38))


@pytest.mark.parametrize('offset', [0, 4, 8, 12, 16, 20, 24, 50, 120, 2000])
def test_corrupt_source_is_rejected(offset):
    raw = bytearray(mc02(story()))
    raw[offset] ^= 1
    with pytest.raises(ValueError):
        ps2.parse_profile(raw)


@pytest.mark.parametrize('options', [False, True])
def test_database_reference_checks_the_entire_row_index(options):
    # The table tag is the high byte; do not accidentally accept a large row
    # whose low 16 bits happen to fit the table.
    if options:
        payload = bytearray(ps2.PS2_OPTIONS)
        struct.pack_into('<II', payload, 0x1214, 1, 0)
        struct.pack_into('<I', payload, 0x121C, 0x17010001)
    else:
        payload = bytearray(ps2.convert_story(story())[xbox.IDENTITY_END:])
        struct.pack_into('<II', payload, 0x51A0, 1, 0x15010001)
    with pytest.raises(ValueError, match='database reference'):
        ps2.check_unlock_lists(payload, options)


def test_unknown_revision_and_nonzero_padding_refused():
    with pytest.raises(ValueError):
        ps2.convert_story(story()[:0x17E]+b'\1'+story()[0x17F:])
    raw = bytearray(mc02(story()))
    raw[30] = ord('X')
    with pytest.raises(ValueError):
        ps2.parse_profile(bytes(raw))


@pytest.mark.parametrize('wrapper', [psu, cbs])
def test_import_and_safe_replacement(tmp_path, wrapper):
    source = tmp_path/'input.psu'
    source.write_bytes(wrapper(mc02(story())))
    before = source.read_bytes()
    save = tmp_path/'save'
    assert ps2.main([str(source),'--check']) == 0
    assert ps2.main([str(source),'--save-dir',str(save),'--dry-run']) == 0
    assert not save.exists()
    assert ps2.main([str(source),'--save-dir',str(save)]) == 0
    target = save/'UserData/45410049'/xbox.folder_name('DEMO')/'DEMO'
    assert all(xbox.signatures_ok(target.read_bytes(), xbox.PORT_KEY))
    target.write_bytes(b'my old save')
    assert ps2.main([str(source),'--save-dir',str(save)]) == 1
    assert target.read_bytes() == b'my old save'
    assert ps2.main([str(source),'--save-dir',str(save),'--force']) == 0
    backups = list(save.glob('import-backup-*/*/DEMO'))
    assert [p.read_bytes() for p in backups] == [b'my old save']
    assert source.read_bytes() == before


def test_zip_psv_reader_and_duplicates(tmp_path):
    raw = mc02(story())
    data = bytearray(220)
    data[:4] = b'\0VSP'
    struct.pack_into('<I', data, 60, 2)
    struct.pack_into('<I', data, 100, 1)
    struct.pack_into('<II', data, 176, len(raw), 0x10)
    data[184:199] = b'BASLUS-21004DEMO'
    struct.pack_into('<I', data, 216, 220)
    source = tmp_path/'export.zip'
    with zipfile.ZipFile(source, 'w') as archive:
        archive.writestr('PS3/EXPORT/one.psv', data+raw)
        archive.writestr('two.psu', psu(raw))
    save = tmp_path/'save'
    assert ps2.main([str(source),'--save-dir',str(save)]) == 0
    assert len(list((save/'UserData/45410049').iterdir())) == 1


def test_conflicting_sources_fail_before_any_write(tmp_path):
    a,b = tmp_path/'a',tmp_path/'b'
    a.write_bytes(mc02(story()))
    payload = bytearray(story());payload[20] ^= 1
    b.write_bytes(mc02(payload))
    save = tmp_path/'save'
    assert ps2.main([str(a),str(b),'--save-dir',str(save)]) == 2
    assert not save.exists()


def test_options_only_unlocks_preserves_native_preferences_and_metadata(tmp_path):
    save = tmp_path/'save'
    target = native_options(save)
    template = bytearray(ps2.XBOX_OPTIONS)
    template[:7] = b'NATIVE!'
    template[0x148C:] = b'KEEP'
    (target/'Options').write_bytes(ps2.signed_profile('Global', template))
    payload = bytearray(ps2.PS2_OPTIONS)
    struct.pack_into('<II',payload,0x1214,1,1)
    struct.pack_into('<I',payload,0x121C,0x17000001)
    struct.pack_into('<I',payload,0x1294,0x07000002)
    source = tmp_path/'Options.psu';source.write_bytes(psu(mc02(payload,'Global')))
    assert ps2.main([str(source),'--save-dir',str(save),'--force']) == 1
    assert ps2.main([str(source),'--save-dir',str(save),'--include-options','--force']) == 0
    out = (target/'Options').read_bytes()[140:]
    assert out[:0x1214] == template[:0x1214]
    assert out[0x1214:0x148C] == payload[0x1214:0x148C]
    assert out[0x148C:] == b'KEEP'
    assert len(list(save.glob('import-backup-*/*/Options'))) == 1


@pytest.mark.parametrize('danger', ['../bad.psu','/bad.psu','C:/bad.psu'])
def test_unsafe_zip_refused(tmp_path,danger):
    source=tmp_path/'unsafe.zip'
    with zipfile.ZipFile(source,'w') as z:z.writestr(danger,psu(mc02(story())))
    assert ps2.main([str(source),'--check']) == 2
    assert not (tmp_path/'bad.psu').exists()


def test_linked_target_and_oversized_source_refused(tmp_path):
    source=tmp_path/'source';source.write_bytes(mc02(story()))
    save=tmp_path/'save';other=tmp_path/'other';other.mkdir();save.mkdir()
    (save/'UserData').symlink_to(other,target_is_directory=True)
    assert ps2.main([str(source),'--save-dir',str(save)]) == 2
    assert list(other.iterdir()) == []
    source.write_bytes(bytes(containers.MAX_FILE+1))
    assert ps2.main([str(source),'--check']) == 2


def test_max_lzari_invented_literal_vector():
    # Ross Ridge's reference literal encoder, input: one invented DEMO file.
    compressed=bytes.fromhex('f21793ed692bb01bd5fffffffffffffffffffffffffffffbd407f7595c16341102616cce159409f799bc60')
    plain=struct.pack('<I32s',17,b'DEMO')+b'synthetic fixture'+bytes(3)
    assert LzariDecoder().decode(compressed,56) == plain
    header=struct.pack('<12sI32s32sIII',b'Ps2PowerSave',0,b'DIR',b'',len(compressed)+4,1,56)
    raw=bytearray(header+compressed)
    struct.pack_into('<I',raw,12,zlib.crc32(raw))
    assert containers.unpack(bytes(raw)) == [('DEMO',b'synthetic fixture')]
    raw[-1] ^= 1
    with pytest.raises(ValueError,match='CRC'):containers.unpack(bytes(raw))


def test_bounded_decompression_and_card_guidance(tmp_path):
    compressed=bytes.fromhex('f21793ed692bb01bd5fffffffffffffffffffffffffffffbd407f7595c16341102616cce159409f799bc60')
    header=struct.pack('<12sI32s32sIII',b'Ps2PowerSave',0,b'DIR',b'',len(compressed)+4,1,containers.MAX_FILE+1)
    raw=bytearray(header+compressed);struct.pack_into('<I',raw,12,zlib.crc32(raw))
    with pytest.raises(ValueError,match='limits'):containers.unpack(bytes(raw))
    source=tmp_path/'card.ps2';source.write_bytes(b'Sony PS2 Memory Card Format')
    assert ps2.main([str(source),'--check']) == 2


def test_legacy_directory_is_backed_up_instead_of_duplicated(tmp_path):
    source=tmp_path/'input';source.write_bytes(mc02(story('RANE')))
    save=tmp_path/'save'
    canonical=xbox.folder_name('RANE');value=int(canonical,16)
    legacy=canonical[:-1]+'%X'%((value|(value>>32))&15)
    old=save/'UserData/45410049'/legacy;old.mkdir(parents=True)
    (old/'RANE').write_bytes(b'old')
    assert ps2.main([str(source),'--save-dir',str(save)]) == 1
    assert ps2.main([str(source),'--save-dir',str(save),'--force']) == 0
    assert len(list(old.parent.iterdir())) == 1
    assert all(xbox.signatures_ok((old/'RANE').read_bytes(),xbox.PORT_KEY))


def test_replace_failure_restores_old_profile(tmp_path,monkeypatch):
    source=tmp_path/'input';source.write_bytes(mc02(story()))
    save=tmp_path/'save';target=save/'UserData/45410049'/xbox.folder_name('DEMO')
    target.mkdir(parents=True);(target/'DEMO').write_bytes(b'original')
    def fail(*_):raise OSError('injected rename failure')
    monkeypatch.setattr(ps2.os,'replace',fail)
    assert ps2.main([str(source),'--save-dir',str(save),'--force']) == 2
    assert (target/'DEMO').read_bytes() == b'original'
    assert not list(target.parent.glob('.ps2-import-*'))


def test_sps_and_truncation():
    raw=mc02(story())
    def record(name,length):return struct.pack('<H64sI',98,name.encode(),length)+bytes(28)
    archive=(b'\x0d\0\0\0SharkPortSave'+bytes(4)+bytes(12)+bytes(4)+
             record('BASLUS-21004DEMO',3)+record('BASLUS-21004DEMO',len(raw))+raw+bytes(4))
    assert containers.unpack(archive)==[('BASLUS-21004DEMO',raw)]
    for size in (10,100,len(archive)-1):
        with pytest.raises((ValueError,struct.error)):containers.unpack(archive[:size])


def test_source_inside_replacement_is_not_moved(tmp_path):
    save=tmp_path/'save';target=save/'UserData/45410049'/xbox.folder_name('DEMO')
    target.mkdir(parents=True);source=target/'ps2-save';source.write_bytes(mc02(story()))
    before=source.read_bytes()
    assert ps2.main([str(source),'--save-dir',str(save),'--force']) == 2
    assert source.read_bytes()==before
