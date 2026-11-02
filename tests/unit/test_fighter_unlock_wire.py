"""The runtime and Python agree on the fixed Options set's real byte layout."""
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_unlocks import fixture
import fighter_unlocks as unlocks

ROOT = Path(__file__).resolve().parents[2]
PROBE = r'''
#include "fighter_unlocks.h"
#include <stdio.h>
int main(int argc, char **argv) {
    unsigned char data[FIGHTER_SETTINGS_SIZE+1]; uint32_t count=99; size_t size; FILE *file;
    if(argc!=2 || !(file=fopen(argv[1],"rb"))) return 2;
    size=fread(data,1,sizeof data,file); fclose(file);
    if(!fighter_unlocks_decode(data,size,&count)) return count ? 2 : 1;
    printf("%u:",count);
    for(uint32_t i=0;i<count;++i) printf("%08x,",fighter_unlocks_at(data,i));
    return 0;
}
'''


@pytest.fixture(scope='module')
def wire_probe(tmp_path_factory):
    compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
    if not compiler: pytest.skip('Native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-unlock-wire')
    source, exe = folder / 'probe.c', folder / ('probe.exe' if os.name == 'nt' else 'probe')
    source.write_text(PROBE)
    arguments = ([compiler, '/nologo', '/TC', '/I' + str(ROOT / 'src/hooks'), str(source),
                  str(ROOT / 'src/hooks/fighter_unlocks.c'), '/Fe' + str(exe)] if os.name == 'nt' else
                 [compiler, '-std=c11', '-I', str(ROOT / 'src/hooks'), str(source),
                  str(ROOT / 'src/hooks/fighter_unlocks.c'), '-o', str(exe)])
    result = subprocess.run(arguments, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.mark.parametrize('count', [0, 1, 79, 80, 81])
def test_native_fixed_capacity_metadata_and_bounds(wire_probe, tmp_path, count):
    _, _, _, payload = fixture()
    data = bytearray(payload)
    struct.pack_into('<I', data, unlocks.COUNT, count)
    values = [0x07000000 + i | (unlocks.METADATA if i % 2 else 0) for i in range(min(80, count))]
    struct.pack_into(f'<{len(values)}I', data, unlocks.KEYS, *values)
    path = tmp_path / 'settings.bin'; path.write_bytes(data)
    result = subprocess.run([str(wire_probe), str(path)], capture_output=True, text=True, timeout=10)
    if count == 81:
        assert result.returncode == 1
        with pytest.raises(ValueError): unlocks.settings_keys(bytes(data))
    else:
        assert result.returncode == 0
        assert result.stdout == str(count) + ':' + ''.join(f'{value:08x},' for value in unlocks.settings_keys(bytes(data)))


@pytest.mark.parametrize('fault', ['short', 'long', 'sentinel', 'duplicate', 'unsorted'])
def test_native_malformed_payloads_match_python_rejection(wire_probe, tmp_path, fault):
    _, _, _, payload = fixture(); data = bytearray(payload)
    if fault == 'short': data.pop()
    elif fault == 'long': data.append(0)
    elif fault == 'sentinel': struct.pack_into('<I', data, unlocks.SENTINEL, 0)
    else:
        struct.pack_into('<I', data, unlocks.COUNT, 2)
        struct.pack_into('<2I', data, unlocks.KEYS, *( (3, 3) if fault == 'duplicate' else (3, 2)))
    path = tmp_path / 'settings.bin'; path.write_bytes(data)
    assert subprocess.run([str(wire_probe), str(path)], timeout=10).returncode == 1
    with pytest.raises(ValueError): unlocks.settings_keys(bytes(data))
