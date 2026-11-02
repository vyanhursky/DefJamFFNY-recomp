"""Bounded native windows keep large logical rosters out of fixed guest arrays."""
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_native import catalog, pack
from fighter_bindings import native_rows
from fighter_sod import Database
from fighter_window import encode_window


def test_compiler_separates_300_templates_from_four_native_banks():
    source, original, _ = catalog(menu=True)
    data, report = source.compile([pack(count=300)], binding_window=True)
    assert report['binding_mode'] == 'participant-window'
    assert report['native_character_count'] == 6
    assert len(native_rows(Database(data))) == 6
    assert len(report['window']['fighters']) == len(report['menu_roster']) == 300
    assert len(report['handle_bindings']) == 302
    assert sum(row['available'] for row in report['handle_bindings'].values()) == 2
    assert not report['launch_allowed'] and 'window-save-extension' in report['blockers']
    offsets = set()
    for row in report['window']['fighters']:
        offsets.add(row['record_offset'])
        assert struct.unpack_from('<I', data, row['record_offset'] + 32)[0] == row['selection_key']
    assert len(offsets) == 300
    assert source.compile([pack(count=300)], binding_window=True) == (data, report)
    for row in source.rows.values():
        at = row['record_offset']
        assert data[at:at + 104] == original[at:at + 104]


PROBE = r'''
#include "fighter_window.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    FILE *f; uint8_t *bytes; size_t size; FighterWindow w; FighterWindowRow row;
    if(argc<2 || !(f=fopen(argv[1],"rb"))) return 2;
    bytes=(uint8_t*)malloc(FIGHTER_WINDOW_MAX_FILE+1); if(!bytes) return 2;
    size=fread(bytes,1,FIGHTER_WINDOW_MAX_FILE+1,f); fclose(f);
    if(!fighter_window_decode(&w,bytes,size)) { free(bytes); return 1; }
    if(argc==2) { printf("%u",w.count); free(bytes); return 0; }
    for(uint32_t i=0;i<4;++i) {
        if(!fighter_window_bind(&w,i,254+i,&row)) return 3;
        if(fighter_window_native(&w,row.stable_handle)!=w.banks[i].native_handle) return 4;
        if(fighter_window_stable(&w,w.banks[i].native_handle)!=row.stable_handle) return 5;
        if(w.banks[i].selection_key!=100+i) return 6;
    }
    w.frozen=1;
    if(fighter_window_bind(&w,0,255,&row) || !fighter_window_bind(&w,0,254,&row)) return 7;
    if(fighter_window_bind(&w,4,254,&row) || fighter_window_bind(&w,0,99,&row)) return 8;
    if(fighter_window_native(&w,0x07012345)!=UINT32_MAX) return 9;
    w.frozen=0;
    if(fighter_window_bind(&w,0,255,&row)) return 10;
    free(bytes); return 0;
}
'''


@pytest.fixture(scope='module')
def window_probe(tmp_path_factory):
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler:
        pytest.skip('Native C compiler unavailable')
    root = Path(__file__).resolve().parents[2]
    folder = tmp_path_factory.mktemp('fighter-window-c')
    path = folder / 'probe.c'; path.write_text(PROBE)
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    inputs = [str(path), str(root / 'src/hooks/fighter_window.c')]
    command = ([compiler, '/nologo', '/TC', '/I' + str(root / 'src/hooks'), *inputs, '/Fe' + str(exe)]
               if os.name == 'nt' else [compiler, '-std=c11', '-I', str(root / 'src/hooks'), *inputs, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def test_native_binding_window_roundtrip_and_match_freeze(window_probe, tmp_path):
    source, _, _ = catalog(menu=True)
    _, report = source.compile([pack(count=300)], binding_window=True)
    path = tmp_path / 'window.bin'; path.write_bytes(encode_window(report['window']))
    result = subprocess.run([str(window_probe), str(path), 'bind'], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mutation', ['truncated', 'trailing', 'version', 'count', 'banks', 'table', 'sod-size',
                                     'bank-native', 'private', 'bank-selection', 'bank-offset', 'row-selection', 'row-offset', 'reserved'])
def test_native_window_rejects_invalid_data(window_probe, tmp_path, mutation):
    source, _, _ = catalog(menu=True)
    _, report = source.compile([pack(count=2)], binding_window=True)
    data = bytearray(encode_window(report['window']))
    if mutation == 'truncated': data = data[:-1]
    elif mutation == 'trailing': data += b'x'
    else:
        offset, value = {'version': (4, 2), 'count': (8, 0xffffffff), 'banks': (12, 5), 'table': (16, 256),
                         'sod-size': (20, 12), 'bank-native': (24, 0xffffffff), 'private': (28, 0xffffffff),
                         'bank-selection': (36, 128), 'bank-offset': (40, 0xffffffff), 'row-selection': (124, 99),
                         'row-offset': (132, 0xffffffff), 'reserved': (140, 1)}[mutation]
        struct.pack_into('<I', data, offset, value)
    path = tmp_path / 'bad-window.bin'; path.write_bytes(data)
    assert subprocess.run([str(window_probe), str(path)], capture_output=True, timeout=10).returncode == 1
