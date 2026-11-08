"""Cinematic relocation seals, actual member joins and teardown reuse."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import pytest
from test_fighter_ui_native import TYPES
ROOT=Path(__file__).resolve().parents[2]

DRIVER=r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_film_proof.h"
unsigned char memory[0x400000];
static const char *mode;
static unsigned current;
int defjam_fighter_cinematic_proofs(void){return !strcmp(mode,"missing-required")||!strcmp(mode,"required")?defjam_fighter_film_complete("FV00000",0):1;}
unsigned defjam_fighter_cpu_film(uint32_t address){(void)address;return current;}
int defjam_fighter_cpu_range(uint32_t address,uint32_t bytes){return address>=0x10000&&address<0x40000&&bytes<=64;}
int defjam_fighter_events_has(const char *name,unsigned flags){return !strcmp(name,"FV00000")&&flags==0;}
int defjam_fighter_graph_visual(uint32_t visual,uint32_t bones,const uint8_t *rigs,unsigned count,const uint32_t *face,const uint32_t *hands){
 assert(bones==1&&rigs[0]==0xaa&&count==1&&!face&&hands[0]==0&&hands[1]==0);return visual==0x200000;
}
static void env(const char *key,const char *value){
#ifdef _WIN32
 assert(!_putenv_s(key,value));
#else
 assert(!setenv(key,value,1));
#endif
}
int main(int argc,char **argv){
 assert(argc==5);mode=argv[4];env("RECOMP_FIGHTER_FILM_PROOFS",strcmp(argv[1],"none")?argv[1]:"");env("RECOMP_FIGHTER_CINEMATIC_BANKS",argv[2]);env("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256",argv[3]);
 int ok=defjam_fighter_film_start();if(!strcmp(mode,"reject")||!strcmp(mode,"missing-required")){assert(!ok);return 0;}assert(ok);
 if(!strcmp(mode,"required")){assert(defjam_fighter_film_complete("FV00000",0));assert(!defjam_fighter_film_complete("FI00000",1));return 0;}
 assert(defjam_fighter_film_known("FV00000"));assert(!defjam_fighter_film_known("FV00001"));
 assert(defjam_fighter_film_file("assets/v2ta.viv|FV00000.viv|FV00000.o")==1);
 assert(defjam_fighter_film_file("assets/v2ta.viv|FV00000.viv")==1);
 assert(defjam_fighter_film_file("ASSETS\\V2TA.VIV|fv00000.VIV|FV00000_F.O")==2);
 assert(!defjam_fighter_film_file("assets/v2ta.viv|FV00001.viv|FV00000.o"));
 assert(!defjam_fighter_film_file("assets/v2ta.viv|FV00000.viv|../FV00000.o"));
 for(unsigned i=1;i<=3;++i){
  unsigned base=i*0x10000;current=i;MEM32(base)=base+40;MEM32(base+4)=i;
  if(i==1&&!strcmp(mode,"payload"))memory[base+8]=1;
  if(i==1&&!strcmp(mode,"relocation"))MEM32(base)=base+44;
  ok=defjam_fighter_film_preconstruct(base+16);
  if(i==1&&(!strcmp(mode,"payload")||!strcmp(mode,"relocation"))){assert(!ok);return 0;}assert(ok);
 }
 uint32_t entry=0x1000,descriptor=0x2000;MEM32(entry+0x24)=0x10010;MEM32(entry+0x30)=0x20010;MEM32(entry+0x3c)=0x30010;
 memory[descriptor]=8;MEM32(descriptor+0xA4)=2;MEM32(descriptor+0xD4)=3;
 if(!strcmp(mode,"wrong-bank"))MEM32(entry+0x30)=0x10010;
 if(!strcmp(mode,"wrong-camera-policy"))MEM32(descriptor+0xD4)=2;
 assert(defjam_fighter_film_bind("FV00000",entry,0x200000,descriptor)==(!strcmp(mode,"good")));
 if(!strcmp(mode,"good")){
  defjam_fighter_film_release();assert(!defjam_fighter_film_bind("FV00000",entry,0x200000,descriptor));
  for(unsigned i=1;i<=3;++i){current=i;assert(defjam_fighter_film_preconstruct(i*0x10000+16));}
  assert(defjam_fighter_film_bind("FV00000",entry,0x200000,descriptor));
 }
 return 0;
}
'''

@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:pytest.skip('native C compiler unavailable')
    folder=tmp_path_factory.mktemp('film-native');(folder/'recomp/gen').mkdir(parents=True)
    (folder/'recomp/gen/recomp_types.h').write_text(TYPES,encoding='utf-8')
    driver=folder/'driver.c';driver.write_text(DRIVER,encoding='utf-8')
    exe=folder/('film.exe' if os.name=='nt' else 'film')
    sources=[str(driver),str(ROOT/'src/patches/fighter_film_proof.c')]
    command=([cc,'/nologo','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS','/I'+str(folder),'/I'+str(ROOT/'src'),*sources,'/Fe:'+str(exe)]
             if os.name=='nt' else [cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror',
                                    '-I',str(folder),'-I',str(ROOT/'src'),*sources,'-o',str(exe)])
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    archive=tmp_path/'banks.viv';archive.write_bytes(b'compiler-owned-archive-for-proof-test')
    digest=hashlib.sha256(archive.read_bytes()).digest()
    data=b'FCP1'+struct.pack('<4I',1,3,len(archive.read_bytes()),0)+digest
    payload=bytearray(64);struct.pack_into('<I',payload,0,40)
    for role,suffix in enumerate(('.o','_f.o','_h.o'),1):
        struct.pack_into('<I',payload,4,role)
        data+=struct.pack('<32s8I',('FV00000'+suffix).encode(),64,16,1,1,0,0,role,0)
        data+=bytes.fromhex('aa'*32)+hashlib.sha256(payload).digest()+struct.pack('<2I',0,40)
    proof=tmp_path/'proof.bin';proof.write_bytes(data)
    return [proof,archive,digest.hex()]

@pytest.mark.parametrize('mode',['good','payload','relocation','wrong-bank','wrong-camera-policy'])
def test_cinematic_seals_and_actual_member_joins(tool,files,mode):
    result=subprocess.run([str(tool),*map(str,files),mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr

@pytest.mark.parametrize('offset,value',[(4,2),(8,0),(8,8193),(12,0),(16,1),(20,0),(84,0),(88,64),(92,0),(96,0),(100,33),(104,33),(108,0),(112,2),(180,62)])
def test_cinematic_invalid_proof_metadata(tool,files,offset,value):
    data=bytearray(files[0].read_bytes());struct.pack_into('<I',data,offset,value);files[0].write_bytes(data)
    result=subprocess.run([str(tool),*map(str,files),'reject'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


def complete_proof(files):
    data=files[0].read_bytes();rows=[data[at:at+136] for at in range(52,len(data),136)]
    for suffix in ('_EYE.o','_TARGET.o'):
        row=bytearray(rows[0]);row[:32]=('FV00000'+suffix).encode().ljust(32,b'\0');struct.pack_into('<I',row,56,4);rows.append(row)
    header=bytearray(data[:52]);struct.pack_into('<I',header,8,len(rows))
    return header,rows


@pytest.mark.parametrize('missing',[None,'.o','_f.o','_h.o','_EYE.o','_TARGET.o','entire-file'])
def test_required_bundle_cannot_omit_a_member_or_the_proof_file(tool,files,missing):
    header,rows=complete_proof(files)
    if missing and missing!='entire-file':rows=[row for row in rows if bytes(row[:32]).rstrip(b'\0')!=('FV00000'+missing).encode()]
    struct.pack_into('<I',header,8,len(rows));files[0].write_bytes(header+b''.join(sorted(rows)))
    arguments=['none' if missing=='entire-file' else str(files[0]),str(files[1]),files[2],
               'missing-required' if missing else 'required']
    result=subprocess.run([str(tool),*arguments],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
