"""Native full-graph seals, actual actor joins and generation reuse."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest
from test_fighter_animation_graphs import graph_template, motion, RIG
from test_fighter_ui_native import TYPES
from fighter_animation import AnimationIndex
from fighter_graph_proof import graph_proof, encode_graph_proofs

ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_graph_proof.h"
#include "patches/fighter_palette_context.h"
unsigned char memory[0x400000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
static uint32_t allocated;
unsigned defjam_fighter_cpu_film(uint32_t address){(void)address;return 0;}
int defjam_fighter_research_active(void){return 1;}
int defjam_fighter_cpu_range(uint32_t address,uint32_t bytes){
 return address>=0x10000 && address-0x10000<=allocated && bytes && bytes<=allocated-(address-0x10000);
}
void sub_000441C0(void){assert(MEM32(g_esp+4)==0);g_eax=0x200000;g_ecx=123;g_esp+=4;}
static size_t read(const char *path,void *out,size_t bound){
 FILE *f=fopen(path,"rb");assert(f);size_t n=fread(out,1,bound,f);assert(!ferror(f)&&feof(f));assert(!fclose(f));return n;
}
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void palette(uint32_t raw,uint32_t wrapper){
 uint32_t descriptor=0x1200,root=raw+64;
 memcpy(memory+raw,"\177ELF\1\1\1",7);MEM32(raw+0x20)=1024;memory[raw+0x2E]=40;memory[raw+0x30]=6;
 MEM32(raw+1024+44)=1;MEM32(raw+1024+40+0x10)=64;MEM32(raw+1024+40+0x14)=800;
 MEM32(descriptor+0x10)=raw;MEM32(descriptor+0x14)=2048;MEM32(wrapper)=root;memory[root+4]=2;
 for(unsigned s=0;s<2;++s){
  uint32_t p=root+32+32*s,samples=root+128+128*s,dest=root+96+4*s;
  MEM32(root+8+4*s)=p;MEM32(p)=samples;MEM32(p+4)=dest;memory[p+8]=2;memory[p+9]=1;memory[dest]=4;
  for(unsigned f=0;f<2;++f){float q[4]={0,0,0,1};memcpy(memory+samples+16*f,q,16);}
 }
 FighterPaletteScope previous=defjam_fighter_palette_begin(wrapper);
 defjam_fighter_palette_input(descriptor);defjam_fighter_palette_end(previous,1);
}
int main(int argc,char **argv){
 assert(argc==7);unsigned char proof[65536];size_t bytes=read(argv[1],proof,sizeof proof);
 allocated=(uint32_t)read(argv[2],memory+0x10000,65536);
 size_t skeleton_bytes=read(argv[3],memory+0x300000,65536);
 assert(skeleton_bytes==240);const char *mode=argv[6];
 int ok=defjam_fighter_graph_start(proof,bytes,166);
 if(!strcmp(mode,"reject")){assert(!ok);return 0;}assert(ok);
 assert(!defjam_fighter_graph_has(872)&&defjam_fighter_graph_has(873)&&!defjam_fighter_graph_has(874));
 assert(!defjam_fighter_graph_complete());assert(defjam_fighter_graph_known(873,"A"));assert(defjam_fighter_graph_complete());
 uint32_t relocs=word(proof+24),root=word(proof+20),bank=0x10000+root;
 for(unsigned i=0;i<relocs;++i){uint32_t f=word(proof+104+8*i),t=word(proof+108+8*i);MEM32(0x10000+f)=0x10000+t;}
 if(!strcmp(mode,"payload-byte"))memory[0x10000+allocated-1]^=1;
 if(!strcmp(mode,"relocation"))MEM32(0x10000+word(proof+104))++;
 if(!strcmp(mode,"cpu-range"))allocated--;
 uint32_t body=(uint32_t)strtoul(argv[4],NULL,10),root_index=(uint32_t)strtoul(argv[5],NULL,10);
 assert(!defjam_fighter_graph_bound(873,bank));
 ok=defjam_fighter_graph_preconstruct(bank);
 if(!strcmp(mode,"payload-byte")||!strcmp(mode,"relocation")||!strcmp(mode,"cpu-range")){assert(!ok);return 0;}assert(ok);
 assert(defjam_fighter_graph_bound(873,bank));
 if(!strcmp(mode,"table-root"))root_index=body;
 if(!strcmp(mode,"bank-offset"))bank++;
 if(!strcmp(mode,"constructor")){
  uint32_t records=MEM32(bank+16);
  for(unsigned i=0;i<MEM32(bank+4);++i){
   uint32_t parent=MEM32(records+4*i);
   for(unsigned j=0;j<MEM8(parent+8);++j){uint32_t child=MEM32(parent+12+4*j);
    if(MEM8(child)==25)MEM32(child-20)=0x2B6160;
   }
  }
 }
 ok=defjam_fighter_graph_bank(873,bank,body,root_index);
 if(!strcmp(mode,"payload-byte")||!strcmp(mode,"relocation")||!strcmp(mode,"cpu-range")
    ||!strcmp(mode,"table-root")||!strcmp(mode,"bank-offset")){assert(!ok);return 0;}assert(ok);
 uint32_t visual=0x200000,model=visual+0x30,face=visual+0x450,hands=0x330000;
 if(!strncmp(mode,"created",7)){memory[visual+0xABB4]=1;MEM32(visual+0x9D0)=0x2C0000;model=0x2C0000;face=visual+0xA6B0;}
 MEM32(visual+0xABB8)=hands;memory[model+0x138]=1;memory[model+0x158]=1;
 MEM32(model+0x144)=MEM32(model+0x16C)=0x300000;MEM32(model+0x15C)=2;
 MEM32(model+0x14C)=0x310000;MEM32(model+0x150)=0x310060;MEM32(model+0x154)=0x3100C0;
 palette(0x350000,face);palette(0x370000,hands);
 uint32_t empty_hands[2]={0,0};
 assert(defjam_fighter_graph_visual(visual,2,proof+104+8*relocs,word(proof+68),NULL,empty_hands));
 MEM32(visual+0xABB8)=0;
 assert(!defjam_fighter_graph_visual(visual,2,proof+104+8*relocs,word(proof+68),NULL,empty_hands));
 MEM32(visual+0xABB8)=hands;
 if(!strcmp(mode,"pose"))memory[0x300020]^=1;
 if(!strcmp(mode,"count"))MEM32(model+0x15C)=3;
 if(!strcmp(mode,"init"))memory[model+0x158]=0;
 if(!strcmp(mode,"type6"))MEM32(model+0x16C)=0x300004;
 if(!strcmp(mode,"face-lifetime"))defjam_fighter_palette_release(face);
 if(!strcmp(mode,"hands-lifetime"))defjam_fighter_palette_release(hands);
 if(!strcmp(mode,"samples"))memory[0x350040+32+8]=1;
 if(!strcmp(mode,"created-context"))MEM32(face)=MEM32(hands);
 g_eax=42;g_ecx=43;g_esp=0x3F0000;
 int pass=!strcmp(mode,"valid")||!strcmp(mode,"created")||!strcmp(mode,"rebind")||!strcmp(mode,"constructor");
 assert(defjam_fighter_graph_actor(873,0x3B92E0)==pass);
 assert(g_eax==42&&g_ecx==43&&g_esp==0x3F0000);
 if(!strcmp(mode,"rebind")){
  defjam_fighter_graph_release();assert(!defjam_fighter_graph_actor(873,0x3B92E0));
  assert(!defjam_fighter_graph_bound(873,bank));
  assert(defjam_fighter_graph_preconstruct(bank));
  assert(defjam_fighter_graph_bank(873,bank,body,root_index));assert(defjam_fighter_graph_actor(873,0x3B92E0));
 }
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder=tmp_path_factory.mktemp('graph-native')
    (folder/'recomp/gen').mkdir(parents=True)
    (folder/'recomp/gen/recomp_types.h').write_text(TYPES,encoding='utf-8')
    driver=folder/'driver.c';driver.write_text(DRIVER,encoding='utf-8')
    exe=folder/('graph.exe' if os.name=='nt' else 'graph')
    sources=[str(driver),str(ROOT/'src/patches/fighter_graph_proof.c'),str(ROOT/'src/patches/fighter_palette_context.c')]
    command=([cc,'/nologo','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS','/I'+str(folder),'/I'+str(ROOT/'src'),*sources,'/Fe:'+str(exe)]
             if os.name=='nt' else [cc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-I',str(folder),
                                    '-I',str(ROOT/'src'),*sources,'-lm','-o',str(exe)])
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    skeleton=struct.pack('<4I',0x03AC3F23,0,2,0)+bytes(224)
    rig=hashlib.sha256(skeleton).hexdigest()
    compiler=graph_template()
    envelope,_=compiler.compose('A',motion())
    proof=graph_proof(envelope,'A',RIG,2,[rig])
    model=envelope.model;section=model.sections[1]
    paths=[tmp_path/name for name in ('proof.bin','data.bin','skeleton.bin')]
    for path,data in zip(paths,[encode_graph_proofs({873:proof}),model.data[section[4]:section[4]+section[5]],skeleton]):
        path.write_bytes(data)
    index=AnimationIndex(envelope)
    return paths+[str(index.lookup['A_s']),str(index.lookup['A_t'])]


@pytest.mark.parametrize('mode',['valid','created','rebind','constructor','payload-byte','relocation','cpu-range','table-root',
    'bank-offset','pose','count','init','type6','face-lifetime','hands-lifetime','samples','created-context'])
def test_native_full_graph_and_actual_actor_proofs(tool,files,mode):
    result=subprocess.run([str(tool),*map(str,files),mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('offset,value',[(4,2),(8,8193),(12,872),(16,0xFFFFFFFF),(24,65537),
                                       (64,0),(68,0),(104,0xFFFFFFFC),(108,0xFFFFFFFF)])
def test_invalid_proof_tables_rejected(tool,files,offset,value):
    data=bytearray(files[0].read_bytes());struct.pack_into('<I',data,offset,value);files[0].write_bytes(data)
    result=subprocess.run([str(tool),*map(str,files),'reject'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
