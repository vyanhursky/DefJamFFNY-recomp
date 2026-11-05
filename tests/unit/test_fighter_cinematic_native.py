"""Native cinematic identity, nested request scope and coupled receipts."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_ui_native import TYPES
from test_fighter_cinematic_compile import bundle, fixture, RIG, track
from fighter_cinematic_compile import CinematicArchive, bind_cinematics

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "patches/fighter_cinematic.h"
unsigned char memory[0x400000];
static int enabled=1;
int defjam_fighter_research_active(void) {return enabled;}
static void environment(const char *key,const char *value) {
#ifdef _WIN32
 assert(!_putenv_s(key,value));
#else
 assert(!setenv(key,value,1));
#endif
}
int main(int argc,char **argv) {
 assert(argc==7);
 environment("RECOMP_FIGHTER_CINEMATIC_BANKS",argv[1]);
 environment("RECOMP_FIGHTER_CINEMATIC_BINDINGS",argv[2]);
 environment("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256",argv[3]);
 environment("RECOMP_FIGHTER_RESEARCH_CINEMATICS",argv[4]);
 environment("RECOMP_FIGHTER_RESEARCH_CINEMATICS_SHA256",argv[5]);
 if(!strcmp(argv[6],"inactive"))enabled=0;
 int ok=defjam_fighter_cinematic_start();
 if(!strcmp(argv[6],"reject")||!strcmp(argv[6],"inactive")){assert(!ok);return 0;}
 assert(ok&&!strcmp(defjam_fighter_cinematic_path(),argv[1]));
 memset(memory,0xCD,sizeof(memory));
 uint32_t manager=0x1000,config=0x40000,c=0x50000,request=0x60000;
 MEM32(manager+0x2FF5C)=config;MEM32(manager+0x2B9EC)=0;
 MEM32(request)=1;MEM32(request+4)=2;MEM32(request+12)=0;MEM32(request+0x20)=1;
 MEM32(config+0xA8+8)=1001;MEM32(0x3B90B8+8)=1000;
 if(!strcmp(argv[6],"mismatch"))MEM32(config+0xA8+8)=257;
 if(!strcmp(argv[6],"two-actor"))MEM32(manager+0x2B9EC)=0x02000000;
 uint64_t previous=defjam_fighter_cinematic_enter(manager,c,request);
 assert(previous==0);
 defjam_fighter_cinematic_name(c+0x400);assert(MEM8(c+0x4A8)==0xCD);
 defjam_fighter_cinematic_name(c);assert(!memcmp(memory+c+0xA8,"fmc01000",9));
 assert(MEM8(c+0xA7)==0xCD&&MEM8(c+0xB1)==0xCD);
 /* An unsupported nested request must not inherit the outer fighter. */
 MEM32(request)=0;
 uint64_t nested=defjam_fighter_cinematic_enter(manager,c+0x400,request);
 assert(nested!=0);
 memset(memory+c+0xA8,'x',9);defjam_fighter_cinematic_name(c);assert(MEM8(c+0xA8)=='x');
 defjam_fighter_cinematic_leave(nested,request);
 defjam_fighter_cinematic_name(c);assert(!memcmp(memory+c+0xA8,"fmc01000",9));
 MEM32(request)=1;
 if(!strcmp(argv[6],"bad-owner"))MEM32(request+0x20)=2;
 defjam_fighter_cinematic_leave(previous,request);
 /* Persistent label supports delayed XML completion outside request scope. */
 MEM32(c+0x19C)=1;MEM32(c+0xA4)=0;
 memcpy(memory+0x70000,"FI00000",8);
 if(!strcmp(argv[6],"wrong-clip"))MEM8(0x70006)='9';
 defjam_fighter_cinematic_selected(c,0x70000);
 MEM32(c+0xA4)=1;memcpy(memory+0x70000,"FV00000",8);
 defjam_fighter_cinematic_selected(c,0x70000);
 memset(memory+c+0xA8,'z',9);defjam_fighter_cinematic_name(c);assert(MEM8(c+0xA8)=='z');
 /* Full-width cores and invalid participant indices never truncate. */
 for(unsigned mode=0;mode<4;++mode){
  MEM32(request+4)=mode==0?4:2;
  MEM32(0x3B90B8+8)=mode==1?16384:mode==2?0xffffffffu:4;
  assert(defjam_fighter_cinematic_enter(manager,c,request)==0);
  defjam_fighter_cinematic_name(c);assert(MEM8(c+0xA8)=='z');
  defjam_fighter_cinematic_leave(0,request);
 }
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-cinematic-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER, encoding='utf-8')
    exe = folder / ('cinematic.exe' if os.name == 'nt' else 'cinematic')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_cinematic.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
               if os.name == 'nt' else [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra',
                    '-Werror', '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    source = fixture({'CI_0001.viv': bundle(), 'CE_0001.viv': bundle('CE_0001')})
    banks, receipt = CinematicArchive(source, hashlib.sha256(source).hexdigest()).compose({
        key: {'template': token, 'rig_sha256': RIG, 'bone_count': 4, 'tracks': track()}
        for key, token in [('a', 'CI_0001'), ('b', 'CE_0001')]})
    nis = fixture({'assets/IntroExtro.xml': b'<tauntslist></tauntslist>'})
    nis, table, report = bind_cinematics(banks, receipt, nis, hashlib.sha256(nis).hexdigest(), {
        core: {'intro': 'a', 'victory': 'b'} for core in (256, 257, 1000)})
    bp, tp, np = (tmp_path / name for name in ('v2ta.viv', 'bindings.bin', 'nis.viv'))
    bp.write_bytes(banks); tp.write_bytes(table); np.write_bytes(nis)
    return [bp, tp, report['banks_sha256'], np, report['nis_sha256']]


@pytest.mark.parametrize('mode', ['good', 'inactive'])
def test_native_scope_and_persistent_label(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode', ['mismatch', 'two-actor', 'bad-owner', 'wrong-clip'])
def test_native_identity_or_ownership_mismatch_stops_before_wrong_playback(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 1 and 'cinematic stopped:' in result.stderr


@pytest.mark.parametrize('offset,value', [(0, 0), (4, 2), (8, 0), (8, 16384), (12, 0), (16, 0),
                                        (20, 1), (24, 0), (56, 0), (88, 140), (88, 16384),
                                        (108, 256), (92, 0), (92, 0x2f), (99, 65)])
def test_malformed_receipt_cannot_activate(tool, files, offset, value):
    table = files[1]
    data = bytearray(table.read_bytes()); struct.pack_into('<I', data, offset, value)
    table.write_bytes(data)
    result = subprocess.run([tool, *files, 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
