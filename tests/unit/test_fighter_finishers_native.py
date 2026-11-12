"""Receipt bounds, native provider registration and paired role ownership."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest
from test_fighter_ui_native import TYPES

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "patches/fighter_finishers.h"
unsigned char memory[0x400000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
static unsigned allocations,frees;
static int enabled=1;
static int timed,missing_timelines;
int defjam_fighter_research_active(void){return enabled;}
int defjam_fighter_cpu_contains(uint32_t address){return address != 0;}
void defjam_fighter_cpu_released(void){}
int defjam_fighter_graph_start(const uint8_t *p,size_t n,uint32_t c){(void)p;(void)n;(void)c;return timed;}
int defjam_fighter_graph_has(uint32_t ordinal){return timed&&ordinal>=873&&ordinal<877;}
int defjam_fighter_graph_known(uint32_t ordinal,const char *name){(void)ordinal;(void)name;return timed;}
int defjam_fighter_graph_complete(void){return 1;}
int defjam_fighter_graph_bound(uint32_t ordinal,uint32_t bank){(void)ordinal;(void)bank;return 1;}
int defjam_fighter_graph_bank(uint32_t a,uint32_t b,uint32_t c,uint32_t d){(void)a;(void)b;(void)c;(void)d;return timed;}
int defjam_fighter_graph_actor(uint32_t a,uint32_t b){(void)a;(void)b;return timed;}
void defjam_fighter_graph_release(void){}
void xbox_NoteAnchorEvent(const char *text){assert(!strncmp(text,"fighter-finisher:P",18));}
int defjam_fighter_events_has(const char *name,unsigned flags){(void)name;return timed&&!missing_timelines&&flags!=0;}
uint32_t xbox_HeapAlloc(uint32_t bytes,uint32_t alignment){assert(timed&&bytes==32&&alignment==16);return 0x70000;}
void sub_00029680(void){
 assert(MEM32(g_esp+4)==200&&MEM32(g_esp+8)==0x29D4B4&&!MEM32(g_esp+12));
 allocations++;g_eax=0x20000;g_ecx=0xBAD;g_esp+=4;
}
void sub_00029760(void){assert(MEM32(g_esp+4)==0x20000);frees++;g_eax=0xBAD;g_esp+=4;}
static void environment(const char *k,const char *v){
#ifdef _WIN32
 assert(!_putenv_s(k,v));
#else
 assert(!setenv(k,v,1));
#endif
}
int main(int argc,char **argv){
 assert(argc==5);
 environment("RECOMP_FIGHTER_FINISHERS",argv[1]);
 environment("RECOMP_FIGHTER_FINISHER_BINDINGS",argv[2]);
 environment("RECOMP_FIGHTER_FINISHERS_SHA256",argv[3]);
 const char *mode=argv[4];
 timed=!strncmp(mode,"timed",5);missing_timelines=!strcmp(mode,"timed-missing");
 if(!strcmp(mode,"inactive"))enabled=0;
 int ok=defjam_fighter_finishers_start();
 if(!strcmp(mode,"reject")||!strcmp(mode,"inactive")||!strcmp(mode,"timed-missing")||!strcmp(mode,"timed-reject")){assert(!ok);return 0;}
 assert(ok&&!strcmp(defjam_fighter_finishers_path(),argv[1]));
 if(!strcmp(mode,"admission"))return 0;
 uint32_t a=0x3B92E0,b=a+0x12E8,p=0x10438;
 g_esp=0x3F0000;g_eax=42;g_ecx=43;
 for(unsigned slot=0;slot<4;++slot)MEM32(a+slot*0x12E8+0x28)=UINT32_MAX;
 MEM32(a+0x28)=0;MEM32(a+0x2C)=256;MEM32(a+0xBB8)=2;
 MEM32(b+0x28)=1;MEM32(b+0x2C)=1000;MEM32(b+0xBB8)=2;
 MEM32(a)=b;MEM32(b)=a;MEM8(a+0x926)=MEM8(b+0x926)=1;
 MEM32(a+0xF50)=MEM32(b+0xF50)=31;
 if(!strncmp(mode,"slots",5))MEM32(a+0xBBC)=2;
 if(!strcmp(mode,"slots-choice"))MEM32(a+0xBBC)=3;
 MEM32(0x1000)=709;MEM32(0x1004)=164;MEM32(0x1008)=0x3BE628;
 MEM8(0x3BE628+4)=MEM8(0x3BE628+5)=1;
 if(!strcmp(mode,"choice"))MEM32(a+0xBB8)=3;
 defjam_fighter_finishers_mask(0x1000,0x1004,0x1008);
 assert(defjam_fighter_finisher_cpu_file("motion/blazin.viv|P0000_A.ord"));
 assert(!defjam_fighter_finisher_cpu_file("motion/blazin.viv|P0000_A.orl"));
 assert(!defjam_fighter_finisher_cpu_file("motion/other.viv|P0000_A.ord"));
 assert(!defjam_fighter_finisher_cpu_file("motion/blazin.viv|P9999_A.ord"));
 assert(allocations==1&&MEM32(0x1000)==709&&MEM32(0x1004)==168&&MEM32(0x1008)==0x20000);
 assert(MEM8(0x3BE628+164)==0&&MEM8(0x20000+164)==1&&MEM8(0x20000+167)==1);
 assert(g_esp==0x3F0000&&g_eax==42&&g_ecx==43);
 MEM32(p+0x14)=0x30000;MEM32(p+0x18)=0x31000;MEM32(p+0x28)=0x32000;
 MEM32(p+0x2C)=168;MEM32(p+0x30)=709;MEM32(p+0x34)=0x20000;MEM32(p+0x38)=6;
 for(unsigned i=0;i<6;++i){
  uint32_t key=i<2?713+i:871+i, bank=0x40000+i*0x1000;
  MEM32(0x30000+i*24)=key;MEM32(0x30004+i*24)=i;
  if(i<2)continue;
  uint32_t name=defjam_fighter_finisher_name(6,key,0);
  assert(name);memcpy(memory+0x30008+i*24,memory+name,8);
  MEM32(0x32004+i*12)=bank;MEM32(bank+4)=2;
  MEM32(bank+16)=bank+0x100;MEM32(bank+20)=bank+0x200;
  MEM32(0x31008+i*16)=0;MEM32(0x31004+i*16)=1;
  MEM32(bank+0x100)=bank+0x300;MEM32(bank+0x200)=bank+0x400;
  memcpy(memory+bank+0x400,memory+name,7);memcpy(memory+bank+0x407,"_s",3);
  MEM8(bank+0x300)=15;MEM8(bank+0x308)=1;MEM32(bank+0x30C)=bank+0x500;MEM8(bank+0x500)=11;
 }
 if(!strcmp(mode,"missing"))MEM32(p+0x38)=5;
 if(!strcmp(mode,"duplicate"))MEM32(0x30000+5*24)=876-1;
 if(!strcmp(mode,"wrong-name"))MEM8(0x30008+2*24)='X';
 if(!strcmp(mode,"fallback"))MEM32(0x31008+2*16)=1;
 if(!strcmp(mode,"child"))MEM8(0x42500)=9;
 defjam_fighter_finishers_loaded(p);
 assert(!defjam_fighter_finisher_cpu_file("motion/blazin.viv|P0000_A.ord"));
 MEM32(0x3B8634)=0x50000;MEM32(0x3B862C)=39;MEM32(0x3B8630)=873;
 for(unsigned i=0;i<4;++i){
  MEM32(a+0x84)=0;MEM32(a+0x88)=MEM32(a+0x8C)=873+i;
  uint32_t source=0x50000+(873+i)*39;
  assert(defjam_fighter_finisher_parameters(a+0x2BC,source,123)==source);
  assert(defjam_fighter_finisher_parameters(a+0x2BC,source,0x1A867E)==0x50000+(713+i%2)*39);
  assert(MEM32(a+0x88)==873+i&&MEM32(a+0x8C)==873+i);
 }
 MEM32(a+0x88)=MEM32(a+0x8C)=873;
 MEM32(a+0x84)=1;
 assert(defjam_fighter_finisher_parameters(a+0x2BC,0x50000+873*39,0x1A867E)==0x50000+873*39);
 MEM32(a+0x84)=0;MEM32(a+0x8C)=712;
 assert(defjam_fighter_finisher_parameters(a+0x2BC,0x50000+712*39,0x1A867E)==0x50000+712*39);
 MEM32(a+0x8C)=873;
 if(!strcmp(mode,"parameter-stride"))MEM32(0x3B862C)=40;
 if(!strcmp(mode,"parameter-count"))MEM32(0x3B8630)=872;
 if(!strcmp(mode,"parameter-overflow"))MEM32(a+0x88)=MEM32(a+0x8C)=UINT32_MAX;
 defjam_fighter_finisher_parameters(a+0x2BC,0x50000+873*39,0x1A867E);
 assert(!defjam_fighter_finisher_name(1,873,0)&&!defjam_fighter_finisher_name(6,872,0));
 MEM32(0x2EC1C8+713*4)=0x60100;MEM32(0x2EC1C8+714*4)=0x60200;
 assert(defjam_fighter_finisher_name(0,873,0x1A3ECF)==(timed?0x70000u:0x60100u));
 assert(defjam_fighter_finisher_name(0,874,0x1A3ECF)==(timed?0x70008u:0x60200u));
 assert(defjam_fighter_finisher_name(0,875,0x1A3ECF)==(timed?0x70010u:0x60100u));
 assert(defjam_fighter_finisher_name(0,876,0x1A3ECF)==(timed?0x70018u:0x60200u));
 assert(!memcmp(memory+defjam_fighter_finisher_name(0,873,0x1B252F),"P0000_A",8));
 FighterFinisherScope outer=defjam_fighter_finisher_enter(a);
 assert(defjam_fighter_finisher_motion(a,10713,6,0x123)==10713);
 assert(defjam_fighter_finisher_motion(a,10713,6,0x1D3BA0)==10873);
 if(!strcmp(mode,"role"))defjam_fighter_finisher_motion(a,10714,6,0x1D3BAA);
 assert(defjam_fighter_finisher_motion(b,10714,6,0x1D3BAA)==10874);
 if(!strncmp(mode,"slots",5)){
  MEM32(a+0xF50)=32;
  if(!strcmp(mode,"slots-changed"))MEM32(a+0xBBC)=3;
  assert(defjam_fighter_finisher_motion(a,10713,6,0x1D3BA0)==10875);
  assert(defjam_fighter_finisher_motion(b,10714,6,0x1D3BAA)==10876);
  MEM32(a+0xF50)=39;
  assert(defjam_fighter_finisher_motion(a,10713,6,0x1D3BA0)==10875);
  MEM32(a+0xF50)=33;MEM32(a+0xBC0)=2;
  assert(defjam_fighter_finisher_motion(a,10713,6,0x1D3BA0)==10713);
  MEM32(a+0xF50)=31;
 }
 FighterFinisherScope inner=defjam_fighter_finisher_enter(b);
 assert(defjam_fighter_finisher_motion(b,10713,6,0x1D3BA0)==10875);
 assert(defjam_fighter_finisher_motion(a,10714,6,0x1D3BAA)==10876);
 defjam_fighter_finisher_leave(inner);
 assert(defjam_fighter_finisher_motion(a,10713,6,0x1D3BA0)==10873);
 defjam_fighter_finisher_leave(outer);
 assert(defjam_fighter_finisher_motion(a,10713,6,0x1D3BA0)==10713);
 defjam_fighter_finishers_release(0x2000);assert(!frees);
 defjam_fighter_finishers_release(0x10000);assert(frees==1);
 if(timed)assert(!memcmp(memory+0x70000,"P0000_A\0P0000_B\0P0001_A\0P0001_B\0",32));
 defjam_fighter_finishers_release(0x10000);assert(frees==1);
 assert(!defjam_fighter_finisher_name(6,873,0)&&g_eax==42&&g_ecx==43&&g_esp==0x3F0000);
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-finishers-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER, encoding='utf-8')
    exe = folder / ('finishers.exe' if os.name == 'nt' else 'finishers')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_finishers.c'), str(ROOT / 'src/patches/fighter_fatal.c'), str(ROOT / 'tests/unit/native_stubs/host_fatal.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
               if os.name == 'nt' else [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra',
                    '-Werror', '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    # Invented archive bytes: native admission checks the sealed digest; Python
    # compiler tests separately exercise real container structure and record IO.
    data = b'invented archive' * 4
    digest = hashlib.sha256(data).digest()
    table = b'FBP1' + struct.pack('<4I', 1, 2, 168, len(data)) + digest
    table += struct.pack('<III8s8s', 256, 2, 873, b'P0000_A', b'P0000_B')
    table += struct.pack('<III8s8s', 1000, 2, 875, b'P0001_A', b'P0001_B')
    archive, binding = tmp_path / 'blazin.viv', tmp_path / 'bindings.bin'
    archive.write_bytes(data); binding.write_bytes(table)
    return archive, binding, digest.hex()


@pytest.mark.parametrize('mode',['timed','timed-missing','timed-reject'])
def test_snapshot_owned_camera_and_tag_identity_is_coupled_and_retained(tool,files,mode):
    archive,binding,digest=files
    table=b'FBP4'+struct.pack('<4I',4,2,168,len(archive.read_bytes()))+bytes.fromhex(digest)
    for core,ordinal,token in [(256,873,'P0000_'),(1000,875,'P0001_')]:
        table+=struct.pack('<5I8s8s',core,0,2,ordinal,2 if mode=='timed-reject' else 1,
                           (token+'A').encode(),(token+'B').encode())
    table+=b'invented sealed graph proof; verified by the dedicated native proof fixture'
    binding.write_bytes(table)
    result=subprocess.run([tool,*files,mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('mode', ['good', 'inactive'])
def test_registration_roles_names_and_lifetime(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode', ['choice', 'missing', 'duplicate', 'wrong-name', 'fallback', 'child', 'role',
                                 'parameter-stride', 'parameter-count', 'parameter-overflow'])
def test_provider_or_role_mismatch_stops_before_playback(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 1 and 'finisher stopped:' in result.stderr, result.stdout + result.stderr


@pytest.mark.parametrize('offset,value', [(0, 0), (4, 2), (8, 0), (8, 0xFFFFFFFF), (12, 164),
    (12, 0xFFFFFFFF), (16, 1), (52, 140), (52, 16384), (56, 82), (60, 872), (60, 874),
    (60, 877), (60, 0xFFFFFFFF), (64, 0), (80, 255), (88, 873)])
def test_invalid_receipts_and_overflow_never_activate(tool, files, offset, value):
    archive, binding, digest = files
    data = bytearray(binding.read_bytes()); struct.pack_into('<I', data, offset, value)
    binding.write_bytes(data)
    result = subprocess.run([tool, archive, binding, digest, 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('choice,mode', [(2, 'admission'), (3, 'reject')])
def test_shared_animation_requires_the_same_inherited_behavior(tool, files, choice, mode):
    archive, binding, digest = files
    data = bytearray(binding.read_bytes())
    struct.pack_into('<III8s8s', data, 80, 1000, choice, 873, b'P0000_A', b'P0000_B')
    binding.write_bytes(data)
    result = subprocess.run([tool, archive, binding, digest, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def slot_files(files):
    archive, binding, digest = files
    table = b'FBP2' + struct.pack('<4I', 2, 3, 168, len(archive.read_bytes())) + bytes.fromhex(digest)
    for core, slot, ordinal, token in [(256, 0, 873, 'P0000_'), (256, 1, 875, 'P0001_'), (1000, 0, 875, 'P0001_')]:
        table += struct.pack('<4I8s8s', core, slot, 2, ordinal, (token+'A').encode(), (token+'B').encode())
    binding.write_bytes(table)
    return files


@pytest.mark.parametrize('mode', ['slots', 'slots-choice', 'slots-changed'])
def test_native_slot_identity_distinguishes_duplicate_behavior_and_rechecks_choice(tool, slot_files, mode):
    result = subprocess.run([tool, *slot_files, mode], capture_output=True, text=True)
    expected = 0 if mode == 'slots' else 1
    assert result.returncode == expected, result.stdout + result.stderr
    if expected:
        assert 'finisher stopped:' in result.stderr


@pytest.mark.parametrize('offset,value', [(4, 1), (56, 4), (56, 0xffffffff), (60, 82), (88, 0), (88, 4), (92, 3)])
def test_malformed_slot_receipt_is_rejected(tool, slot_files, offset, value):
    archive, binding, digest = slot_files
    table = bytearray(binding.read_bytes()); struct.pack_into('<I', table, offset, value); binding.write_bytes(table)
    result = subprocess.run([tool, archive, binding, digest, 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
