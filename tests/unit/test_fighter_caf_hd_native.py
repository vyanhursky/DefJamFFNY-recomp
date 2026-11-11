"""Production HD reader/alpha routing with synthetic guest memory."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf_hd import encode
from test_fighter_motion_native import TYPES
ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hooks/guest_call.h"
unsigned char memory[0xC00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
#include "@SOURCE@"
static uint8_t recipe[240];
static unsigned calls,cleared;
static int linear;
static const uint8_t *lookup(uint32_t selection,uint32_t outfit) {return selection==100 && outfit<2?recipe:NULL;}
void texture_pack_memory_clear(uint32_t owner) {assert(owner==0x10000);++cleared;}
int texture_pack_memory_register(uint32_t owner,uint32_t address,uint32_t format,uint32_t nw,uint32_t nh,const uint8_t *bgra,uint32_t w,uint32_t h) {
 assert(owner==0x10000 && address==0x100010 && format==(linear?0x12u:6u));
 assert(nw==256 && nh==256 && w==h && (w==512 || w==1024 || w==2048));
 for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++) {
  unsigned at=(y*w+x)*4,native=(y/(h/256))*256+x/(w/256);
  assert(bgra[at]==11 && bgra[at+1]==22 && bgra[at+2]==33);
  assert(bgra[at+3]==(uint8_t)(native%3==0?133:219));
 }
 ++calls;return 1;
}
int main(int argc,char **argv) {
 assert(argc==4);linear=!strcmp(argv[3],"linear");
#if defined(_WIN32)
 _putenv_s("RECOMP_FIGHTER_CAF_HD",argv[1]);_putenv_s("RECOMP_FIGHTER_CAF_HD_SHA256",argv[2]);
#else
 setenv("RECOMP_FIGHTER_CAF_HD",argv[1],1);setenv("RECOMP_FIGHTER_CAF_HD_SHA256",argv[2],1);
#endif
 int valid=defjam_caf_hd_start(lookup);
 if(!strcmp(argv[3],"invalid")){assert(!valid);return 0;}
 assert(valid);
 MEM32(0x1A234)=0x100000;MEM8(0x100000)=0x7D;MEM16(0x100004)=MEM16(0x100006)=256;
 MEM32(0x10000C)=linear?0:0x2000;
 for(unsigned y=0;y<256;y++)for(unsigned x=0;x<256;x++) {
  unsigned native=y*256+x,at=linear?native:hd_swizzle(x)|(hd_swizzle(y)<<1);
  MEM8(0x100010+at*4+3)=(uint8_t)(native%3==0?133:219);
 }
 defjam_caf_hd_apply(0x10000,999,0);assert(!calls && !cleared);
 defjam_caf_hd_apply(0x10000,100,0);assert(calls==1 && cleared==1);
 defjam_caf_hd_apply(0x10000,100,1);assert(calls==1 && cleared==1);
 defjam_caf_hd_clear();assert(cleared==2 && !s_hd_owners[0]);
 defjam_caf_hd_clear();assert(cleared==2);return 0;
}
'''

@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else shutil.which('cc') or shutil.which('clang')
    if not cc:pytest.skip('native compiler unavailable')
    folder=tmp_path_factory.mktemp('caf-hd-native');(folder/'recomp/gen').mkdir(parents=True)
    (folder/'recomp/gen/recomp_types.h').write_text(TYPES)
    (folder/'texture_pack.h').write_text('#include <stdint.h>\nvoid texture_pack_memory_clear(uint32_t);\nint texture_pack_memory_register(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,const uint8_t *,uint32_t,uint32_t);\n')
    driver=folder/'driver.c';driver.write_text(DRIVER.replace('@SOURCE@',(ROOT/'src/patches/fighter_caf_hd.c').as_posix()))
    exe=folder/('hd.exe' if os.name=='nt' else 'hd')
    if os.name=='nt':command=[cc,'/nologo','/W4','/WX','/wd5105','/D_CRT_SECURE_NO_WARNINGS','/I'+str(folder),'/I'+str(ROOT/'src'),str(driver),'/Fe:'+str(exe)]
    else:command=[cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror','-I',str(folder),'-I',str(ROOT/'src'),str(driver),'-o',str(exe)]
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe

def raw(edge=512):
    block=struct.pack('<I',edge)+bytes((11,22,33,0))*(edge*edge)
    return encode({'a/b':{'extras':{'hd_atlases':{'a':block}}}},{'bindings':{'a/b':{'selection_key':100}}})

def run(tool,tmp_path,payload,mode):
    path=tmp_path/'hd.bin';path.write_bytes(payload)
    result=subprocess.run([str(tool),str(path),hashlib.sha256(payload).hexdigest(),mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr

@pytest.mark.parametrize('edge',[512,1024,2048])
@pytest.mark.parametrize('mode',['linear','swizzled'])
def test_live_rgb_detail_native_material_alpha_and_ownership(tool,tmp_path,edge,mode):
    run(tool,tmp_path,raw(edge),mode)

@pytest.mark.parametrize('offset,value',[(0,0),(4,2),(8,50000),(12,1),(16,999),(20,2),(24,49),(48,999),(28,49)])
def test_native_reader_rejects_malformed_and_unbound_blocks(tool,tmp_path,offset,value):
    payload=bytearray(raw());struct.pack_into('<I',payload,offset,value)
    run(tool,tmp_path,payload,'invalid')

def test_native_reader_rejects_trailing_bytes(tool,tmp_path):
    run(tool,tmp_path,raw()+bytes(4),'invalid')
