"""Actual sculpt reader/adapter with invented guest buffers and evaluator ABI."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import pytest
from test_fighter_motion_native import TYPES
from test_fighter_caf_face import fixture
from fighter_caf_face import encode

ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hooks/guest_call.h"
unsigned char memory[0xC00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
#include "@SOURCE@"
static uint8_t recipe[232];
static unsigned calls;
static int wrong_result;
static const uint8_t *lookup(uint32_t selection,uint32_t outfit) {return selection==100&&outfit==0?recipe:NULL;}
void sub_000296B0(void) {assert(MEM32(g_esp+4)==0x4000);g_eax=0x600000;g_esp+=4;}
void sub_00026140(void) {
 uint32_t wrapper=MEM32(g_esp+4),root=MEM32(wrapper),at=root+36,model=MEM32(g_ecx+0x12c);
 uint32_t rows=MEM32(model+0xb8)+12;
 assert(MEM32(root)==1&&MEM32(root+16)==1&&MEM32(root+24)==1&&MEM32(root+28)==0&&MEM32(root+32)==9);
 assert(!strcmp((char *)XBOX_PTR(MEM32(root+20)),"Coordinates"));
 MEM32(model+0xd4)=root;
 for(unsigned m=0;m<9;++m) {
  uint32_t count=MEM32(at+4),rm=MEM32(at+12);
  assert(rm==s_rms[m]&&count==s_counts[m]&&MEM32(at)==0xc0000000u+count*12&&MEM32(at+8)==0);at+=16;
  uint32_t target=MEM32(rows+rm*16+12);
  for(uint32_t v=0;v<count;++v)for(unsigned k=0;k<3;++k) {if(!wrong_result)MEMF(target+v*12+k*4)+=MEMF(at)*.9999f;at+=4;}
 }
 ++calls;g_esp+=12;
}
static void make_head(uint32_t visual,uint32_t base,const uint8_t *source) {
 uint32_t part=visual+0x140+2u*0x420,model=base,group=base+0x100;
 MEM32(part+0x12c)=model;MEM32(model+0xb8)=group;MEM32(model+0xd4)=0xABCD;
 MEM32(group+4)=base+0x300;memcpy(XBOX_PTR(base+0x300),"Coordinates",12);MEM32(group+8)=10;
 unsigned vertex=0,mesh=0;
 for(unsigned rm=0;rm<10;++rm) {
  uint32_t row=group+12+rm*16,count=rm==8?10:s_counts[mesh++],data=base+0x1000+rm*0x3000;
  MEM32(row)=rm;MEM16(row+4)=(uint16_t)count;MEM16(row+6)=24;MEM32(row+8)=count*12;MEM32(row+12)=data;
  for(uint32_t v=0;v<count;++v) {
   if(rm==8) {MEMF(data+v*12+4)=19.5f;continue;}
   memcpy(XBOX_PTR(data+v*12),source+32+vertex*24,12);++vertex;
  }
 }
}
int main(int argc,char **argv) {
 assert(argc==4);const char *mode=argv[3];
 for(unsigned i=0;i<6;++i) {static const unsigned slots[]={0,5,6,9,10,11};uint32_t v=i?1:0;memcpy(recipe+32+slots[i]*4,&v,4);}
#if defined(_WIN32)
 _putenv_s("RECOMP_FIGHTER_CAF_FACES",argv[1]);_putenv_s("RECOMP_FIGHTER_CAF_FACES_SHA256",argv[2]);
#else
 setenv("RECOMP_FIGHTER_CAF_FACES",argv[1],1);setenv("RECOMP_FIGHTER_CAF_FACES_SHA256",argv[2],1);
#endif
 if(!strcmp(mode,"bad-read")) {assert(!defjam_caf_faces_start(lookup));return 0;}
 assert(defjam_caf_faces_start(lookup));assert(s_count==1);
 make_head(0x10000,0x100000,s_data+16);make_head(0x30000,0x200000,s_data+16);
 g_esp=0xB00000;g_eax=123;g_ecx=456;
 defjam_caf_faces_apply(0x10000,0,101,0,recipe);assert(!calls);
 uint32_t control=s_live[0][1],before=hash_bytes(control,s_sizes[0][1]);
 if(!strcmp(mode,"reference"))MEMF(0x200000+0x1000)=.01f;
 if(!strcmp(mode,"alias"))MEM32(0x200100+12+12)=s_live[0][0];
 wrong_result=!strcmp(mode,"result");
 defjam_caf_faces_apply(0x30000,1,100,0,recipe);
 assert(!strcmp(mode,"good")&&calls==1);
 assert(hash_bytes(control,s_sizes[0][1])==before&&MEM32(0x200000+0xd4)==0xABCD);
 assert(g_esp==0xB00000&&g_eax==123&&g_ecx==456);
 defjam_caf_faces_clear();assert(!s_live[0][1]&&!s_live[1][1]);return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else shutil.which('cc') or shutil.which('clang')
    if not cc:pytest.skip('native C compiler unavailable')
    folder=tmp_path_factory.mktemp('caf-face-native');(folder/'recomp/gen').mkdir(parents=True)
    (folder/'recomp/gen/recomp_types.h').write_text(TYPES)
    source=ROOT/'src/patches/fighter_caf_face.c'
    driver=folder/'driver.c';driver.write_text(DRIVER.replace('@SOURCE@',source.as_posix()))
    exe=folder/('face.exe' if os.name=='nt' else 'face')
    if os.name=='nt':
        command=[cc,'/nologo','/W4','/WX','/wd5105','/D_CRT_SECURE_NO_WARNINGS','/I'+str(folder),'/I'+str(ROOT/'src'),str(driver),'/Fe:'+str(exe)]
    else:
        command=[cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror','-I',str(folder),'-I',str(ROOT/'src'),str(driver),'-lm','-o',str(exe)]
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


def raw():
    value,recipe=fixture()
    return encode({'a/b':{'outfits':[dict(recipe=recipe,face=value)]}},{'bindings':{'a/b':{'selection_key':100}}})


@pytest.mark.parametrize('mode,error',[('good',None),('reference','template differs'),('alias','alias another'),('result','result differs')])
def test_real_native_adapter_bounds_reference_output_isolation_and_lifetime(tool,tmp_path,mode,error):
    payload=raw();path=tmp_path/'faces.bin';path.write_bytes(payload)
    result=subprocess.run([str(tool),str(path),hashlib.sha256(payload).hexdigest(),mode],capture_output=True,text=True)
    assert result.returncode==(1 if error else 0),result.stdout+result.stderr
    if error:assert error in result.stderr
    else:assert 'peer-buffers=unchanged' in result.stderr


@pytest.mark.parametrize('offset,value',[(0,0),(4,2),(8,50000),(12,8),(16,999),(20,3),(24,5),(48,0x7fc00000),(60,0x3f800000)])
def test_real_native_reader_rejects_invalid_or_unbound_rows(tool,tmp_path,offset,value):
    payload=bytearray(raw());struct.pack_into('<I',payload,offset,value)
    path=tmp_path/'bad.bin';path.write_bytes(payload)
    result=subprocess.run([str(tool),str(path),hashlib.sha256(payload).hexdigest(),'bad-read'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
