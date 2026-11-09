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


def test_removing_last_pack_returns_retail_database_without_forgetting_identity():
    source, _, _ = catalog(menu=True)
    _, installed = source.compile([pack(count=2)], binding_window=True)
    data, removed = source.compile([], installed['binding_ledger'], binding_window=True)
    assert data == source.compile([])[0]
    assert removed['binding_mode'] == 'retail-only'
    assert removed['added_count'] == 0 and removed['menu_roster'] == {}
    assert 'window' not in removed and 'window_sha256' not in removed
    assert removed['native_character_count'] == len(source.rows)
    assert removed['binding_ledger'] == installed['binding_ledger']
    for key, row in removed['handle_bindings'].items():
        assert row['available'] == key.startswith('retail/')
    _, restored = source.compile([pack(count=2)], removed['binding_ledger'], binding_window=True)
    assert restored == installed


@pytest.mark.parametrize('identifier', ['alpha', 'single-starter', 'zeta'])
def test_window_selection_domains_do_not_depend_on_pack_name_order(identifier):
    source, _, _ = catalog(menu=True)
    data, report = source.compile([pack(identifier, count=1)], binding_window=True)
    assert report['window']['fighters'][0]['selection_key'] == 100
    assert [row['selection_key'] for row in report['window']['banks']] == [100, 101, 102, 103]
    assert len(native_rows(Database(data))) == len(source.rows) + 4


def test_deferred_selection_domain_still_rejects_duplicate_logical_keys():
    source, _, _ = catalog(menu=True)
    template = next(iter(source.rows.values()))['record_offset']
    additions = [{'key': key, 'template': template, 'fields': {}} for key in ('zeta/a', 'zeta/b')]
    with pytest.raises(ValueError, match='colliding allocated selection'):
        source.db.extend_character_records(additions, selection_keys={'zeta/a': 100, 'zeta/b': 100},
                                           deferred_keys={'zeta/a', 'zeta/b'})


PROBE = r'''
#include "fighter_window.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    FILE *f; uint8_t *bytes; size_t size; FighterWindow w; FighterWindowRow row;
    { const char *valid[]={"0", " -1", " +101 ", "\t2147483647\r\n", "-2147483648", "\v\f-0"};
      int32_t expected[]={0,-1,101,2147483647,(-2147483647-1),0}, value;
      const char *bad[]={"", " ", "+", "-", "--1", "9a", "2147483648", "-2147483649", "1.0"};
      for(uint32_t i=0;i<sizeof valid/sizeof valid[0];++i)
        if(!fighter_window_integer(valid[i],&value) || value!=expected[i])return 26;
      for(uint32_t i=0;i<sizeof bad/sizeof bad[0];++i)
        if(fighter_window_integer(bad[i],&value))return 27;
      if(fighter_window_integer(NULL,&value) || fighter_window_integer("1",NULL))return 28;
    }
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
    if(fighter_window_command(&w,"Fighters.KeepReady(15)")!=-1)return 17;
    if(fighter_window_bind(&w,0,255,&row) || !fighter_window_bind(&w,0,254,&row)) return 7;
    if(fighter_window_clear(&w,0) || fighter_window_clear(&w,UINT32_MAX)) return 11;
    if(fighter_window_bind(&w,4,254,&row) || fighter_window_bind(&w,0,99,&row)) return 8;
    if(fighter_window_native(&w,0x07012345)!=UINT32_MAX) return 9;
    if(!fighter_window_finish(&w) || w.frozen || fighter_window_finish(&w))return 29;
    for(uint32_t i=0;i<4;++i)if(!w.selected[i])return 30;
    { const char *bad[]={"Fighters.KeepReady", "Fighters.KeepReady()", "Fighters.KeepReady(16)",
        "Fighters.KeepReady(-1)", "Fighters.KeepReady(01)", "Fighters.KeepReady(0)tail"};
      for(uint32_t i=0;i<sizeof bad/sizeof bad[0];++i)
        if(fighter_window_command(&w,bad[i])!=-1 || !w.selected[0] || !w.selected[3])return 18;
    }
    if(fighter_window_command(&w,"Game.Quit()") || fighter_window_command(&w,NULL))return 19;
    if(fighter_window_command(&w,"Fighters.KeepReady(15)")!=1)return 20;
    if(fighter_window_bind(&w,0,255,&row)) return 10;
    if(!fighter_window_clear(&w,0) || w.selected[0] || !w.selected[1])return 12;
    if(fighter_window_stable(&w,w.banks[0].native_handle)!=w.banks[0].private_handle)return 13;
    if(!fighter_window_bind(&w,0,254,&row) || fighter_window_clear(&w,4))return 14;
    if(!fighter_window_clear(&w,UINT32_MAX))return 15;
    for(uint32_t i=0;i<4;++i)if(w.selected[i])return 16;
    if(fighter_window_command(&w,"Fighters.KeepReady(1)")!=-1)return 21;
    if(!fighter_window_bind(&w,0,254,&row) || !fighter_window_bind(&w,1,255,&row))return 22;
    if(fighter_window_command(&w,"Fighters.KeepReady(2)")!=1 || w.selected[0] || !w.selected[1])return 23;
    if(!fighter_window_bind(&w,0,254,&row))return 24;
    if(fighter_window_command(&w,"Fighters.KeepReady(0)")!=1 || !fighter_window_bind(&w,2,254,&row))return 25;
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
