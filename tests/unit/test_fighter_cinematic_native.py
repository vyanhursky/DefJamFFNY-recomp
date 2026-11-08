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
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "patches/fighter_cinematic.h"
unsigned char memory[0x400000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
static int enabled=1;
static int full;
static unsigned full_binds;
static unsigned proof_checks;
static int proofs_available=1;
int defjam_fighter_film_complete(const char *name,int intro){assert(name&&name[0]&&(intro==0||intro==1));proof_checks++;return proofs_available;}
int defjam_fighter_film_known(const char *name){return full&&!strcmp(name,"FV00000");}
int defjam_fighter_film_bind(const char *name,uint32_t entry,uint32_t visual,uint32_t descriptor){assert(!strcmp(name,"FV00000")&&entry==0x71000&&visual==0x72000&&descriptor);full_binds++;return 1;}
static unsigned constructed, started, ready;
static unsigned momentum;
static unsigned playback_events;
static char last_playback[48];
void sub_001A5190(void) {assert(MEM32(g_esp+8)==0x447A0000);momentum++;g_eax=0xBAD;g_esp+=4;}
void sub_000A2E20(void) { constructed++; g_eax=0xBAD;g_esp+=4; }
void sub_00087AF0(void) {
 uint32_t c=MEM32(g_esp+4),r=MEM32(g_esp+8);
 uint64_t previous=defjam_fighter_cinematic_enter(g_ecx,c,r);
 defjam_fighter_cinematic_name(c);
 MEM32(c+0x19C)=4;MEM32(c+0xA4)=2;MEM32(c+0xD0)=4;MEM32(c+0xD4)=MEM32(r+0x1C);
 MEM32(r+0x20)=1;
 defjam_fighter_cinematic_selected(c,c+0x61);
 defjam_fighter_cinematic_leave(previous,r);
 started++;g_eax=0xBAD;g_esp+=12;
}
void sub_000A3E80(void) {g_eax=ready;g_esp+=4;}
void sub_000A3130(void) {g_eax=0xBAD;g_esp+=8;}
int defjam_fighter_research_active(void) {return enabled;}
void xbox_NoteAnchorEvent(const char *text) {
 if(!strncmp(text,"fighter-blazin-playback:",23)){
  playback_events++;snprintf(last_playback,sizeof last_playback,"%s",text);return;
 }
 if(!strncmp(text,"fighter-blazin:B",16)){assert(strlen(text)==21);return;}
 assert(!strncmp(text,"fighter-cinematic:F",19));
 assert(strlen(text)==25);
}
static void environment(const char *key,const char *value) {
#ifdef _WIN32
 assert(!_putenv_s(key,value));
#else
 assert(!setenv(key,value,1));
#endif
}
int main(int argc,char **argv) {
 assert(argc==7||argc==8);
 environment("RECOMP_FIGHTER_CINEMATIC_BANKS",argv[1]);
 environment("RECOMP_FIGHTER_CINEMATIC_BINDINGS",argv[2]);
 environment("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256",argv[3]);
 environment("RECOMP_FIGHTER_RESEARCH_CINEMATICS",argv[4]);
 environment("RECOMP_FIGHTER_RESEARCH_CINEMATICS_SHA256",argv[5]);
 if(argc==8)environment("RECOMP_FIGHTER_BLAZIN_BINDINGS",argv[7]);
 if(!strcmp(argv[6],"inactive"))enabled=0;
 int ok=defjam_fighter_cinematic_start();
 if(!strcmp(argv[6],"reject")||!strcmp(argv[6],"inactive")){assert(!ok);return 0;}
 assert(ok&&!strcmp(defjam_fighter_cinematic_path(),argv[1]));
 if(!strcmp(argv[6],"coverage")||!strcmp(argv[6],"missing-proof")){
  proofs_available=!strcmp(argv[6],"coverage");
  assert(defjam_fighter_cinematic_proofs()==proofs_available);assert(proof_checks);return 0;
 }
 memset(memory,0xCD,sizeof(memory));
 uint32_t manager=0x1000,config=0x40000,c=0x50000,request=0x60000;
 MEM32(manager+0x2FF5C)=config;MEM32(manager+0x2B9EC)=0;
 if(argc==8){
  MEM32(manager+0x2D830)=0;MEM32(manager+0x2D834)=0;
  g_esp=0x3F0000;g_eax=42;g_ecx=43;g_edx=44;g_esi=45;
  defjam_fighter_cinematic_cache_begin(manager);
  assert(defjam_fighter_cinematic_allocation(0x1234,99)==99);
  assert(defjam_fighter_cinematic_allocation(0x8AE86,4+12*0x1AC)==4+52*0x1AC);
  assert(defjam_fighter_cinematic_allocation(0x8AED9,12*0x24)==52*0x24);
  MEM32(manager+0x2D830)=0x80000;MEM32(manager+0x2D834)=0x90000;MEM32(manager+0x2D868)=12;
  MEM32(manager+0x2D838)=2;MEM32(manager+0x2D844)=2;
  defjam_fighter_cinematic_cache_finish(manager);assert(constructed==40);
  assert(g_esp==0x3F0000&&g_eax==42&&g_ecx==43&&g_edx==44&&g_esi==45);
  c=0x80000+(12+20)*0x1AC;memset(memory+c,0xCD,0x1AC);
  for(unsigned i=0;i<4;++i)MEM32(0x3B90B8+4*i)=UINT32_MAX;
  MEM32(request)=4;MEM32(request+4)=2;MEM32(request+12)=2;MEM32(request+0x20)=1;
  MEM32(config+0xB0)=1001;MEM32(0x3B90C0)=1000;
  uint64_t shared=defjam_fighter_cinematic_enter(manager,0x80000,request);
  defjam_fighter_cinematic_name(0x80000);assert(MEM8(0x800A8)==0xCD);
  defjam_fighter_cinematic_leave(shared,request);
  uint64_t previous=defjam_fighter_cinematic_enter(manager,c,request);
  defjam_fighter_cinematic_name(c);
  assert(!memcmp(memory+c+0xA8,"fmb01000",9));
  defjam_fighter_cinematic_leave(previous,request);
  MEM32(c+0x19C)=4;MEM32(c+0xA4)=2;MEM32(c+0xD0)=4;
  memcpy(memory+c+0x1D,"BT4V01A",8);
  for(unsigned phase=0;phase<4;++phase){
   MEM32(c+0xD4)=phase;
   if(!strcmp(argv[6],"bad-phase"))MEM32(c+0xD4)=4;
   if(!strcmp(argv[6],"bad-count"))MEM32(c+0xD0)=3;
   if(!strcmp(argv[6],"bad-family"))MEM32(c+0x19C)=1;
   memcpy(memory+c+0x61,"BT1_01",7);
   uint32_t name=c+0x61;
   if(!strcmp(argv[6],"bad-name-pointer"))name++;
   defjam_fighter_cinematic_selected(c,name);
   char expected[8];snprintf(expected,sizeof expected,"B%05u",phase+4);
   assert(!memcmp(memory+c+0x61,expected,7));
   assert(MEM8(c+0x60)==0xCD&&MEM8(c+0x68)==0xCD);
   assert(!memcmp(memory+c+0x1D,"BT4V01A",8));
  }
  /* Unsupported categories and unbound cores preserve the native name. */
  memset(memory+c+0xA8,'z',9);MEM32(request+12)=4;
  previous=defjam_fighter_cinematic_enter(manager,c,request);
  defjam_fighter_cinematic_name(c);assert(MEM8(c+0xA8)=='z');
  defjam_fighter_cinematic_leave(previous,request);
  MEM32(request+12)=2;MEM32(config+0xB0)=258;MEM32(0x3B90C0)=257;
  previous=defjam_fighter_cinematic_enter(manager,c,request);
  defjam_fighter_cinematic_name(c);assert(MEM8(c+0xA8)=='z');
  defjam_fighter_cinematic_leave(previous,request);
  MEM32(config+0xB0)=1001;MEM32(0x3B90C0)=1000;
  MEM32(config+0xAC)=257;MEM32(0x3B90BC)=256;
  assert(!defjam_fighter_cinematic_cache_ready(manager));
  assert(started==20&&MEM32(manager+0x2D868)==12);
  ready=1;assert(defjam_fighter_cinematic_cache_ready(manager));assert(started==20);
  assert(defjam_fighter_cinematic_cache_index(manager,2)==32);
  assert(playback_events==0); /* Preload and ordinary play do not emit the test event. */
  assert(momentum==0);
  environment("RECOMP_FIGHTER_TEST_READY_BLAZIN","1");
  MEM32(0x3B8F30)=1;
  for(unsigned slot=0;slot<4;++slot){
   uint32_t actor=0x3B92E0+slot*0x12E8;
   MEM32(actor+0x28)=slot;MEM32(actor+0x2C)=MEM32(0x3B90B8+slot*4);
   MEM8(actor+0x933)=MEM8(actor+0x93E)=0;
  }
  defjam_fighter_cinematic_cache_poll(manager);assert(momentum==0);
  environment("RECOMP_TEST_OBSERVATIONS","1");
  defjam_fighter_cinematic_cache_poll(manager);assert(momentum==2);
  defjam_fighter_cinematic_cache_poll(manager);assert(momentum==2);
  for(unsigned shot=0;shot<10;++shot)
   assert(defjam_fighter_cinematic_cache_index(manager,2+shot)==12+20+shot);
  MEM32(manager+0x2D844)=1;
  for(unsigned shot=0;shot<10;++shot)
   assert(defjam_fighter_cinematic_cache_index(manager,2+shot)==12+10+shot);
  assert(playback_events==20&&!strcmp(last_playback,"fighter-blazin-playback:1:3"));
  environment("RECOMP_TEST_OBSERVATIONS","0");
  assert(defjam_fighter_cinematic_cache_index(manager,11)==31&&playback_events==20);
  assert(!memcmp(memory+0x80000+(12+10)*0x1AC+0x61,"B00000",7));
  assert(!memcmp(memory+0x80000+(12+20)*0x1AC+0x61,"B00004",7));
  assert(g_esp==0x3F0000&&g_eax==42&&g_ecx==43&&g_edx==44&&g_esi==45);
  defjam_fighter_cinematic_cache_release(manager);assert(MEM32(manager+0x2D868)==52);
  return 0;
 }
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
 full=1;MEM32(c+0x90)=0x71000;MEM32(c+0x94)=1;memcpy(memory+0x71000,"FV00000",8);
 MEM32(manager+0x2B9C0+8)=0x72000;MEM32(0x71000+0x44)=0x72000;
 if(!strcmp(argv[6],"wrong-visual"))MEM32(0x71000+0x44)=0x72010;
 if(!strcmp(argv[6],"wrong-entry-name"))MEM8(0x71000+6)='9';
 if(!strcmp(argv[6],"wrong-actor-count"))MEM32(c+0x94)=2;
 defjam_fighter_cinematic_bind(c);assert(full_binds==1);
 defjam_fighter_cinematic_cache_release(manager);defjam_fighter_cinematic_bind(c);assert(full_binds==1);
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


@pytest.mark.parametrize('mode', ['mismatch', 'two-actor', 'bad-owner', 'wrong-clip','wrong-visual','wrong-entry-name','wrong-actor-count'])
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


@pytest.fixture
def blazin_files(files, tmp_path):
    from fighter_archive import Archive
    from fighter_blazin_compile import BlazinArchive, encode_blazin_bindings
    from test_fighter_blazin_compile import bundle as activation, resource, TOKENS
    source = Archive(files[0].read_bytes()).compose(additions={
        token + '.viv': activation(token, phase) for phase, token in enumerate(TOKENS)})
    data, receipt = BlazinArchive(source, hashlib.sha256(source).hexdigest()).compose({
        'alpha/activation': resource(), 'beta/activation': resource()})
    # Existing cinematic payloads are unchanged; update the internal fixture's
    # final generation digest/size, then bind the independent activation table.
    table = bytearray(files[1].read_bytes())
    struct.pack_into('<I', table, 12, len(data)); table[24:56] = hashlib.sha256(data).digest()
    files[0].write_bytes(data); files[1].write_bytes(table); files[2] = hashlib.sha256(data).hexdigest()
    target = tmp_path / 'blazin.bin'
    target.write_bytes(encode_blazin_bindings(data, receipt, {256: 'alpha/activation', 1000: 'beta/activation'}))
    return files, target


def test_native_blazin_four_phases_keep_venue_camera_and_full_core_owner(tool, blazin_files):
    files, target = blazin_files
    result = subprocess.run([tool, *files, 'good', target], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode', ['bad-phase', 'bad-count', 'bad-family', 'bad-name-pointer'])
def test_native_blazin_contract_mismatch_stops(tool, blazin_files, mode):
    files, target = blazin_files
    result = subprocess.run([tool, *files, mode, target], capture_output=True, text=True)
    assert result.returncode == 1 and 'four-shot contract' in result.stderr


@pytest.mark.parametrize('offset,value', [(0,0),(4,2),(8,0),(8,16384),(12,0),(16,0),
                                        (48,140),(48,16384),(84,256),(52,0),(58,65)])
def test_native_blazin_malformed_binding_cannot_activate(tool, blazin_files, offset, value):
    files, target = blazin_files
    data = bytearray(target.read_bytes()); struct.pack_into('<I', data, offset, value)
    target.write_bytes(data)
    result = subprocess.run([tool, *files, 'reject', target], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode',['coverage','missing-proof'])
@pytest.mark.parametrize('activation',[False,True])
def test_full_graph_binding_versions_require_explicit_member_proofs(tool,files,blazin_files,mode,activation):
    files,target=blazin_files
    table=bytearray(files[1].read_bytes());rows=[]
    for at in range(88,len(table),20):rows.append(table[at:at+20]+struct.pack('<I',3))
    table[:4]=b'FIC2';struct.pack_into('<I',table,4,2);table[88:]=b''.join(rows);files[1].write_bytes(table)
    arguments=[tool,*files,mode]
    if activation:
        table=bytearray(target.read_bytes());rows=[]
        for at in range(48,len(table),36):rows.append(table[at:at+36]+struct.pack('<I',15))
        table[:4]=b'FBZ2';struct.pack_into('<I',table,4,2);table[48:]=b''.join(rows);target.write_bytes(table)
        arguments.append(target)
    result=subprocess.run(arguments,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
