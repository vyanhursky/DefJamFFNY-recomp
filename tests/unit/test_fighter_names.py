"""Cross-language FML1 validation, using synthetic names and native C decoder."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_names import encode_names, MAX_COUNT, MAX_TEXT
from fighter_sod import name_hash

PROBE = r'''
#include "fighter_names.h"
#include "fighter_roster.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    FILE *f; unsigned char *data; size_t count; FighterNames names; uint32_t offset, length;
    if (argc < 2 || !(f=fopen(argv[1],"rb"))) return 2;
    data=(unsigned char *)malloc(FIGHTER_NAMES_MAX_FILE+1); if (!data) return 2;
    count=fread(data,1,FIGHTER_NAMES_MAX_FILE+1,f); fclose(f);
    if (!fighter_names_decode(&names,data,count)) { free(data); return 1; }
    if (argc==4) {
        uint32_t items[1024], keys[1024], scratch[1024], n=0, custom; char *p=argv[3], *end;
        while(*p && n<1024) { keys[n]=(uint32_t)strtoul(p,&end,16); items[n]=n+1000; ++n; if(p==end) return 2; p=*end?end+1:end; }
        custom=fighter_roster_partition(items,keys,n,scratch,&names);
        printf("%u:",custom);
        for(uint32_t i=0;i<n;++i) printf("%08x,",items[i]);
    } else if (argc==3) {
        uint32_t key=(uint32_t)strtoul(argv[2],NULL,16);
        if (!fighter_names_find(&names,key,&offset,&length)) { free(data); return 3; }
        for(uint32_t i=0;i<length;++i) printf("%02x",data[names.text_offset+offset+i]);
    } else printf("%u",names.count);
    free(data); return 0;
}
'''


@pytest.fixture(scope='module')
def native_probe(tmp_path_factory):
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler:
        pytest.skip('Native C compiler not available in this shell')
    folder = tmp_path_factory.mktemp('fighter-names-c')
    source = folder / 'probe.c'
    source.write_text(PROBE, encoding='utf-8')
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    if os.name == 'nt':
        cmd = [compiler, '/nologo', '/TC', '/I' + str(ROOT / 'src/hooks'), str(source),
               str(ROOT / 'src/hooks/fighter_names.c'), str(ROOT / 'src/hooks/fighter_roster.c'), '/Fe' + str(exe)]
    else:
        cmd = [compiler, '-std=c11', '-I', str(ROOT / 'src/hooks'), str(source),
               str(ROOT / 'src/hooks/fighter_names.c'), str(ROOT / 'src/hooks/fighter_roster.c'), '-o', str(exe)]
    result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def run_native(exe, path, data, key=None):
    path.write_bytes(data)
    args = [str(exe), str(path)] + ([] if key is None else [f'{key:x}'])
    return subprocess.run(args, capture_output=True, text=True, timeout=10)


def test_names_encoder_is_deterministic_and_bounded():
    entries = {'fm-one': 'Alpha', 'fm-two': '\u732b\U0001f601'}
    assert encode_names(entries) == encode_names(dict(reversed(list(entries.items()))))
    assert encode_names({}) == b'FML1' + struct.pack('<III', 1, 0, 0)
    for bad in ({'fm-one': ''}, {'fm-one': 'nul\0value'}, {'fm-one': '\ud800'},
                {'fm-one': 'x' * MAX_TEXT}, {str(i): 'A' for i in range(MAX_COUNT + 1)}):
        with pytest.raises(ValueError):
            encode_names(bad)


def test_native_c_reads_python_names_and_unicode(native_probe, tmp_path):
    entries = {'fm-one': 'Alpha', 'fm-two': '\u732b\U0001f601'}
    data = encode_names(entries)
    path = tmp_path / 'names.bin'
    assert run_native(native_probe, path, data).stdout == '2'
    for symbol, text in entries.items():
        result = run_native(native_probe, path, data, name_hash(symbol))
        assert result.returncode == 0, result.stderr
        assert result.stdout == (text.encode('utf-16le') + b'\0\0').hex()
    assert run_native(native_probe, path, data, 123).returncode == 3
    assert run_native(native_probe, path, encode_names({})).returncode == 0


def test_native_roster_partition_preserves_retail_context_order_and_custom_order(native_probe, tmp_path):
    a, b = name_hash('fm-one'), name_hash('fm-two')
    path = tmp_path / 'names.bin'
    path.write_bytes(encode_names({'fm-one': 'Alpha', 'fm-two': 'Beta'}))
    for items in ([], [a, 255, b, 256, 257, a, 254], [1, 2, 3], [b, a], [a] * 1000):
        result = subprocess.run([str(native_probe), str(path), 'order', ','.join(f'{v:x}' for v in items)],
                                capture_output=True, text=True, timeout=10)
        expected = [i + 1000 for i, v in enumerate(items) if v not in (a, b)] + [i + 1000 for i, v in enumerate(items) if v in (a, b)]
        assert result.returncode == 0
        assert result.stdout == str(sum(v in (a, b) for v in items)) + ':' + ''.join(f'{v:08x},' for v in expected)


@pytest.mark.parametrize('mutation', [
    lambda b: b[:8],
    lambda b: b + b'extra',
    lambda b: b'FAIL' + b[4:],
    lambda b: b[:4] + struct.pack('<I', 2) + b[8:],
    lambda b: b[:8] + struct.pack('<I', 0xffffffff) + b[12:],
    lambda b: b[:20] + struct.pack('<I', 0xffffffff) + b[24:],
    lambda b: b[:24] + struct.pack('<I', 3) + b[28:],
    lambda b: b[:28] + b[16:20] + b[32:],  # duplicate key
    lambda b: b[:40] + b'\x00\xd8' + b[42:],  # unpaired surrogate
    lambda b: b[:40] + b'\x00\x00' + b[42:],  # early NUL
    lambda b: b[:-2] + b'xx',
])
def test_native_c_rejects_malformed_bindings(native_probe, tmp_path, mutation):
    data = encode_names({'fm-one': 'Alpha', 'fm-two': 'Beta'})
    assert run_native(native_probe, tmp_path / 'bad.bin', mutation(data)).returncode == 1
