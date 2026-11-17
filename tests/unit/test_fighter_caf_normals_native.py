"""Real packed-normal adapter on invented guest models with shared source buffers."""
import os
from pathlib import Path
import shutil
import subprocess
import struct
import pytest
from test_fighter_motion_native import TYPES
from test_fighter_caf_normals import normal_entries
from fighter_caf_face import encode_normals

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
static uint8_t recipe[240];
static const uint8_t *lookup(uint32_t selection,uint32_t outfit) {return selection==100&&outfit==0?recipe:NULL;}
void sub_000296B0(void) {assert(MEM32(g_esp+4)==NORMAL_ARENA);g_eax=0x800000;g_esp+=4;}
static void model(uint32_t visual,uint32_t base) {
 uint32_t part=visual+0x140+3u*0x420,group=base+0x100,rm=base+0x500,program=base+0x800;
 MEM32(part+0x12c)=base;MEM32(base+0xcc)=group;MEM32(base+0x9c)=1;
 MEM32(group)=0;MEM32(group+4)=1;MEM32(group+8)=rm+0x38;
 MEM32(rm)=program;MEM32(rm+8)=program+36;MEM32(rm+0x38)=rm;
 MEM32(program)=(9u<<16)|4;MEM32(program+4)=0;MEM32(program+8)=0;MEM32(program+12)=12;
 MEM32(program+16)=(9u<<16)|4;MEM32(program+20)=0;MEM32(program+24)=3;MEM32(program+28)=4;
 MEM32(program+32)=0;
 MEM32(rm+0x3c)=3;MEM32(rm+0x40)=base+0x1000;
 MEM32(rm+0x44)=3;MEM32(rm+0x48)=0x700000;
 for(unsigned i=0;i<3;i++){MEMF(base+0x1000+i*12)=0;MEMF(base+0x1000+i*12+4)=19.5f;MEMF(base+0x1000+i*12+8)=1;}
 for(unsigned i=0;i<3;i++)MEM32(0x700000+i*4)=1023;
}
int main(int argc,char **argv) {
 assert(argc==3);const char *mode=argv[2];FILE *file=fopen(argv[1],"rb");assert(file);
 static uint8_t rows[CAF_NORMAL_STRIDE*4];size_t bytes=fread(rows,1,sizeof rows,file);fclose(file);
 uint32_t count=(uint32_t)(bytes/CAF_NORMAL_STRIDE);
 if(!strcmp(mode,"bad-read")){assert(!defjam_caf_normals_start(lookup,rows,count));return 0;}
 assert(defjam_caf_normals_start(lookup,rows,count));
 model(0x10000,0x100000);model(0x30000,0x200000);g_esp=0xB00000;
 if(!strcmp(mode,"alias"))MEM32(0x30000+0x140+3u*0x420+0x12c)=0x100000;
 defjam_caf_normals_apply(0x30000,1,101,0);
 if(!strcmp(mode,"position"))MEMF(0x10100c)=.1f;
 if(!strcmp(mode,"source"))MEM32(0x700004)=1023u<<22;
 defjam_caf_normals_apply(0x10000,0,100,0);
 if(strcmp(mode,"good")){assert(MEM32(0x1000cc)==0x100100);return 0;}
 assert(!strcmp(mode,"good"));
 assert(MEM32(0x700004)==1023&&MEM32(0x2000cc)==0x200100);
 uint32_t group=MEM32(0x1000cc),resource=MEM32(MEM32(group+8)),private_data=MEM32(resource+0x48);
 assert(group!=0x100100&&private_data!=0x700000&&MEM32(private_data+4)==1023u<<11);
 assert(MEM32(private_data)==1023&&MEM32(private_data+8)==1023);
 defjam_caf_normals_detach(0x10000,0);assert(MEM32(0x1000cc)==0x100100);
 defjam_caf_normals_clear();defjam_caf_normals_apply(0x10000,0,100,0);
 assert(MEM32(0x700004)==1023);defjam_caf_normals_detach(0x10000,0);
 assert(MEM32(0x1000cc)==0x100100);defjam_caf_normals_release();assert(!n_count&&!n_rows);return 0;
}
'''


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else shutil.which('cc')
    if not cc:pytest.skip('Native C compiler unavailable')
    root=tmp_path_factory.mktemp('caf-normals-native');(root/'recomp/gen').mkdir(parents=True)
    (root/'recomp/gen/recomp_types.h').write_text(TYPES)
    driver=root/'driver.c';driver.write_text(DRIVER.replace('@SOURCE@',(ROOT/'src/patches/fighter_caf_normals.c').as_posix()))
    exe=root/('normals.exe' if os.name=='nt' else 'normals')
    extra=[str(ROOT/'src/patches/fighter_fatal.c'),str(ROOT/'src/patches/fighter_config.c'),str(ROOT/'tests/unit/native_stubs/host_fatal.c')]
    command=[cc,'/nologo','/W4','/WX','/wd5105','/D_CRT_SECURE_NO_WARNINGS','/I'+str(root),'/I'+str(ROOT/'src'),str(driver),*extra,'/Fe:'+str(exe)] if os.name=='nt' else [cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror','-I',str(root),'-I',str(ROOT/'src'),str(driver),*extra,'-lm','-o',str(exe)]
    result=subprocess.run(command,cwd=root,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


@pytest.mark.parametrize('mode,error',[('good',None),('position','position differs'),('source','source differs'),('alias','aliases another')])
def test_private_normal_copies_reference_binding_detach_and_peer_isolation(native,tmp_path,mode,error):
    entries,report=normal_entries();count,raw=encode_normals(entries,report);assert count==1
    path=tmp_path/'normal.bin';path.write_bytes(raw)
    run=subprocess.run([str(native),str(path),mode],capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    assert (error or 'source-buffers=unchanged') in run.stderr


@pytest.mark.parametrize('offset,value',[(0,999),(4,3),(8,2),(12,16),(16,65535),(24,0x7fc00000),(32,0),(36,0)])
def test_native_reader_refuses_unbound_or_malformed_records(native,tmp_path,offset,value):
    entries,report=normal_entries();_,raw=encode_normals(entries,report)
    raw=bytearray(raw);struct.pack_into('<I',raw,offset,value)
    path=tmp_path/'bad.bin';path.write_bytes(raw)
    run=subprocess.run([str(native),str(path),'bad-read'],capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
