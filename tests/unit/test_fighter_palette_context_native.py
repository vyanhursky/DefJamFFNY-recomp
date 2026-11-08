"""Native palette provenance, borrowed spans and resource replacement."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from test_fighter_ui_native import TYPES

ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <math.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_palette_context.h"
unsigned char memory[0x20000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
int defjam_fighter_research_active(void){return 1;}
static void elf(uint32_t raw,uint32_t descriptor,uint32_t wrapper){
 memset(memory+raw,0,2048);memcpy(memory+raw,"\177ELF\1\1\1",7);
 MEM32(raw+0x20)=1024;memory[raw+0x2E]=40;memory[raw+0x30]=6;
 MEM32(raw+1024+40+4)=1;MEM32(raw+1024+40+0x10)=64;MEM32(raw+1024+40+0x14)=800;
 MEM32(descriptor+0x10)=raw;MEM32(descriptor+0x14)=2048;MEM32(descriptor+0x18)=0;
 uint32_t root=raw+64;
 MEM32(wrapper)=root;memory[root+4]=2;
 for(unsigned s=0;s<2;++s){
  uint32_t palette=root+32+32*s,samples=root+128+128*s,dest=root+96+4*s;
  MEM32(root+8+4*s)=palette;MEM32(palette)=samples;MEM32(palette+4)=dest;
  memory[palette+8]=2;memory[palette+9]=1;memory[dest]=4;
  for(unsigned f=0;f<2;++f){float identity[4]={0,0,0,1};memcpy(memory+samples+16*f,identity,16);}
 }
}
int main(int argc,char **argv){
 assert(argc==2);const char *mode=argv[1];
 uint32_t w=0x1000,d=0x1100,r=0x2000,root=r+64,need[2]={2,2};
 elf(r,d,w);
 FighterPaletteScope outer=defjam_fighter_palette_begin(w);
 if(!strcmp(mode,"bad-header"))memory[r+0x30]=7;
 if(!strcmp(mode,"bad-span"))MEM32(r+1024+40+0x14)=2048;
 if(!strcmp(mode,"overflow"))MEM32(d+0x10)=0xFFFFFFFE;
 defjam_fighter_palette_input(d);
 if(!strcmp(mode,"failed"))defjam_fighter_palette_end(outer,0);
 else defjam_fighter_palette_end(outer,1);
 if(!strcmp(mode,"unload"))defjam_fighter_palette_release(w);
 if(!strcmp(mode,"changed-root"))MEM32(w)=root+4;
 if(!strcmp(mode,"samples"))need[1]=3;
 if(!strcmp(mode,"escaped-samples"))MEM32(root+32)=r+860;
 if(!strcmp(mode,"escaped-dest"))MEM32(root+32+4)=r+864;
 if(!strcmp(mode,"bad-dest"))memory[root+96]=15;
 if(!strcmp(mode,"bone-bound"))memory[root+96]=28;
 if(!strcmp(mode,"nan")){float v=NAN;memcpy(memory+root+128,&v,4);}
 if(!strcmp(mode,"nonunit")){float v=2;memcpy(memory+root+128,&v,4);}
 int pass=!strcmp(mode,"valid")||!strcmp(mode,"replace")||!strcmp(mode,"nested");
 assert(defjam_fighter_palette_check(w,root,2,need)==pass);
 if(!strcmp(mode,"replace")){
  defjam_fighter_palette_release(w);assert(!defjam_fighter_palette_check(w,root,2,need));
  elf(0x4000,d,w);FighterPaletteScope previous=defjam_fighter_palette_begin(w);
  defjam_fighter_palette_input(d);defjam_fighter_palette_end(previous,1);
  assert(!defjam_fighter_palette_check(w,root,2,need));
  assert(defjam_fighter_palette_check(w,0x4040,2,need));
 }
 if(!strcmp(mode,"nested")){
  elf(0x6000,0x1200,0x1300);FighterPaletteScope previous=defjam_fighter_palette_begin(0x1300);
  defjam_fighter_palette_input(0x1200);
  elf(0x8000,0x1400,0x1500);FighterPaletteScope nested=defjam_fighter_palette_begin(0x1500);
  defjam_fighter_palette_input(0x1400);defjam_fighter_palette_end(nested,1);defjam_fighter_palette_end(previous,1);
  assert(defjam_fighter_palette_check(0x1300,0x6040,2,need));
  assert(defjam_fighter_palette_check(0x1500,0x8040,2,need));
 }
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder=tmp_path_factory.mktemp('palette-native')
    (folder/'recomp/gen').mkdir(parents=True)
    (folder/'recomp/gen/recomp_types.h').write_text(TYPES,encoding='utf-8')
    driver=folder/'driver.c';driver.write_text(DRIVER,encoding='utf-8')
    exe=folder/('palette.exe' if os.name=='nt' else 'palette')
    sources=[str(driver),str(ROOT/'src/patches/fighter_palette_context.c')]
    command=([cc,'/nologo','/W4','/WX','/I'+str(folder),'/I'+str(ROOT/'src'),*sources,'/Fe:'+str(exe)]
             if os.name=='nt' else [cc,'-std=c11','-Wall','-Wextra','-Werror','-I',str(folder),
                                    '-I',str(ROOT/'src'),*sources,'-lm','-o',str(exe)])
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


@pytest.mark.parametrize('mode',['valid','replace','nested','bad-header','bad-span','overflow','failed',
    'unload','changed-root','samples','escaped-samples','escaped-dest','bad-dest','bone-bound','nan','nonunit'])
def test_palette_context_lifetime_and_actual_bounds(tool,mode):
    result=subprocess.run([str(tool),mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
