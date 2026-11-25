"""Production Story compositor adapter against invented guest bitmaps only."""
from pathlib import Path
import os
import shutil
import subprocess
import pytest
from test_fighter_motion_native import TYPES
from test_fighter_match_teardown_native import definition

ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "hooks/guest_call.h"
#include "patches/fighter_caf_layout.h"
unsigned char memory[0x4000000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;int g_fp_top;
static int allocation_failure;
static void *allocate(size_t n){return allocation_failure?NULL:malloc(n);}
#define malloc allocate
#include "@CORE@"
#include "@ADAPTER@"
#undef malloc
static uint32_t s_contexts[4],s_story_profiles[4];
static const uint8_t *s_recipes[4];
static uint32_t word(const uint8_t *p){uint32_t n;memcpy(&n,p,4);return n;}
static void stop(const char *why){(void)why;abort();}
static void face_trace(uint32_t visual,uint32_t participant){(void)visual;(void)participant;abort();}
@OWNERSHIP@
static unsigned calls,clears,scale=3,hashes;static int enabled=1,missing=0,indexed;
int texture_pack_active(void){return enabled;}
int texture_pack_compositor(const char *kind){assert(!strcmp(kind,"story-caf-v1"));return enabled;}
int texture_pack_hash(const RecompTextureSource *s,char id[65]){assert(s->bytes && s->width<=256);memset(id,'a',64);id[63]="0123456789abcdef"[(((const uint8_t *)s->data)[0]+(s->palette?((const uint8_t *)s->palette)[0]:0))&15];id[64]=0;hashes++;return 1;}
uint8_t *texture_pack_source_png(const char *id,uint32_t nw,uint32_t nh,uint32_t *w,uint32_t *h){
 assert(id[0]=='a');if(missing)return NULL;*w=nw*scale;*h=nh*scale;
 uint8_t *p=allocate((size_t)*w**h*4);if(!p)return NULL;
 for(unsigned i=0;i<*w**h;i++){p[i*4]=40;p[i*4+1]=80;p[i*4+2]=120;p[i*4+3]=0;}return p;
}
uint32_t xbox_PhysRamName(uint32_t p){return p+0x4000000;}
void texture_pack_memory_clear(uint32_t owner){assert(owner>=0x1A234 && owner<=0x1A248);clears++;}
int texture_pack_memory_register(uint32_t owner,uint32_t address,uint32_t format,uint32_t nw,uint32_t nh,const uint8_t *p,uint32_t w,uint32_t h){
 assert(owner==0x1A234 && address==(indexed?0x4300010u:0x4280000u) && format==(indexed?0x0bu:0x12u) && nw==256 && nh==256 && w==256*scale && h==w);
 for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++){
  size_t i=((size_t)y*w+x)*4,n=(y/scale)*256+x/scale;
  assert(p[i]==40 && p[i+1]==80 && p[i+2]==120 && p[i+3]==(uint8_t)n);
 }
 calls++;return 1;
}
static void bitmap(uint32_t p,unsigned w,unsigned h){MEM8(p)=0x7d;MEM16(p+4)=w;MEM16(p+6)=h;MEM32(p+12)=0;}
int main(int argc,char **argv){
 assert(argc==3);scale=(unsigned)atoi(argv[1]);indexed=atoi(argv[2]);
 enabled=0;assert(!story_caf_begin(0x10000));enabled=1;
 assert(!story_caf_begin(0));assert(!story_caf_begin(0xfffffff0));
 bitmap(0x100000,256,256);bitmap(0x200000,256,256);bitmap(0x300000,256,256);
 MEM32(0x30000c)=0x1000;MEM32(0x300010)=0x280000u-0x300000u;
 for(unsigned i=0;i<256*256;i++)MEM8(0x280000+i*4+3)=(uint8_t)i;
 if(indexed){
  MEM32(0x30000c)=0;MEM32(0x300000)=0x7b|((0x2e0000u-0x300000u)<<8);
  MEM8(0x2e0000)=0x2a;MEM16(0x2e0004)=256;
  MEM32(0x2e000c)=0x1000;MEM32(0x2e0010)=0x2d0000u-0x2e0000u;
  for(unsigned i=0;i<256*256;i++)MEM8(0x300010+i)=(uint8_t)i;
  for(unsigned i=0;i<256;i++)MEM8(0x2d0000+i*4+3)=(uint8_t)i;
 }
 MEM32(0x1A234)=0x300000;
 assert(story_caf_begin(0x10000));
 story_caf_lookup(0x100000,0,0);story_caf_convert(0x100000,0x200000);
 story_caf_convert(0x200000,0x300000);story_caf_destroy(0x200000);story_caf_end();assert(calls==1);
 /* Unchanged native slots are not re-registered or cleared on a no-op rebuild. */
 unsigned old_clears=clears;assert(story_caf_begin(0x10000));story_caf_end();assert(calls==1 && clears==old_clears);
 story_caf_invalidate(0x10000,0);assert(clears==old_clears+1);
 /* The real authored-CAF classifier is valid during construction, before
  * context+1. Generic Story registrations must not precede authored atlas
  * replacement or compete for its 32 renderer slots. Native Story profiles
  * tracked for moveset compatibility must still receive Story HD. */
 uint8_t authored[CAF_ROW_STRIDE]={0};uint32_t context=0x720000;
 s_contexts[1]=context;s_recipes[1]=authored;MEM8(context)=1;MEM8(context+1)=0;
 MEM32(context+8)=0x10000-0x8b0;old_clears=clears;
 assert(!story_caf_begin(0x10000) && !s_visual && calls==1 && clears==old_clears+6);
 s_story_profiles[1]=0x730000;assert(story_caf_begin(0x10000));story_caf_end();
 s_contexts[1]=s_story_profiles[1]=0;s_recipes[1]=NULL;
 /* A palette swap cannot change the source identity. Native delta and coverage
  * are applied to the approved source-aligned detail, not baked profile RGB. */
 uint32_t raw=0x400000,pal=raw+32;MEM8(raw)=0x7b;MEM16(raw+4)=MEM16(raw+6)=1;
 MEM32(raw)=0x7b|(32u<<8);MEM8(raw+16)=0;MEM8(pal)=0x2a;MEM16(pal+4)=1;
 MEM32(pal+16)=0x5a3c2814;
 assert(story_caf_begin(0x10000));story_caf_lookup(raw,0,0);unsigned before=hashes;
 MEM32(pal+16)=0x6e46321e;story_caf_convert(raw,0x200000);Shadow *s=find(0x200000);
 assert(s && !s->failed && hashes==before);
 for(unsigned i=0;i<scale*scale;i++){assert(s->image.pixels[i*4]==50 && s->image.pixels[i*4+1]==90 && s->image.pixels[i*4+2]==130 && s->image.pixels[i*4+3]==110);}
 story_caf_end();
 /* Reusing a painted borrowed archive across builds must retain the original
  * source hash and original palette baseline. Handle/pointer reuse by another
  * resource must not inherit it. */
 uint32_t view=0x710000,name=0x710010,output=0x710020,path=0x710030;
 MEM32(0x700000)=0x58504853;MEM32(view)=MEM32(output)=0x700000;MEM32(name)=0x30303030;
 strcpy((char *)XBOX_PTR(path),"assets/v2cp_0.viv|V2CP_TEST.xsh");MEM32(pal+16)=0x5a3c2814;
 assert(story_caf_begin(0x10000));story_caf_resource_open(777,3,path);story_caf_resource_data(777,3,output);
 story_caf_lookup(raw,view,name);assert(s_memo_count==1 && find(raw)->id[63]=='4');story_caf_end();
 MEM32(pal+16)=0x6e46321e;
 assert(story_caf_begin(0x10000));story_caf_resource_data(777,3,output);story_caf_lookup(raw,view,name);
 assert(s_memo_count==1 && find(raw)->id[63]=='4' && find(raw)->image.pixels[0]==20);
 story_caf_convert(raw,0x200000);assert(find(0x200000)->image.pixels[0]==50);story_caf_end();
 strcpy((char *)XBOX_PTR(path),"assets/v2cp_1.viv|V2CP_TEST.xsh");
 assert(story_caf_begin(0x10000));story_caf_resource_open(778,3,path);story_caf_resource_data(778,3,output);story_caf_lookup(raw,view,name);
 assert(s_memo_count==2 && find(raw)->id[63]=='e' && find(raw)->image.pixels[0]==30);story_caf_end();
 assert(s_handle_count==2);story_caf_resource_close(777,3);assert(s_handle_count==1);
 assert(story_caf_begin(0x10000));story_caf_resource_data(777,3,output);assert(!s_archive_count);
 story_caf_resource_data(778,3,output);assert(s_archive_count==1);story_caf_end();
 story_caf_resource_reset(778);assert(!s_handle_count);
 /* A real native operation must agree with the independently replayed witness.
  * An unexpected write fails this atlas closed instead of publishing HD RGB. */
 uint32_t layer=0x500000,place=0x510000;bitmap(layer,1,1);
 MEM32(layer)=0x7d|((0x4f0000u-layer)<<8);MEM32(layer+16)=0x801e140a;MEM8(0x4f0000)=0x7c;
 MEM32(0x4f0008)=1;MEM32(0x4f000c)=2;MEM8(place+8)='b';
 assert(story_caf_begin(0x10000));story_caf_lookup(0x100000,0,0);story_caf_convert(0x100000,0x200000);
 story_caf_lookup(layer,0,0);story_caf_layer(0x200000,layer,place);
 StoryCafImage coverage={0};assert(materialize(find(layer),&coverage));
 for(unsigned i=0;i<scale*scale;i++)assert(coverage.pixels[i*4+3]==128);
 story_caf_image_free(&coverage);
 MEM32(0x200010+(2*256+1)*4)=0x800f0a05;
 story_caf_layer_done(0x200000);assert(s_verified==1 && !find(0x200000)->failed);
 MEM8(0x200010)=99;story_caf_layer_done(0x200000);assert(find(0x200000)->failed);
 story_caf_end();
 /* Missing images keep native layers. A failed allocation never publishes
  * an incomplete HD atlas or changes any byte of the native fallback. */
 missing=1;assert(story_caf_begin(0x10000));story_caf_lookup(0x100000,0,0);story_caf_convert(0x100000,0x300000);story_caf_end();assert(calls==1);missing=0;
 assert(story_caf_begin(0x10000));story_caf_lookup(0x100000,0,0);allocation_failure=1;
 story_caf_convert(0x100000,0x300000);story_caf_end();allocation_failure=0;assert(calls==1);
 for(unsigned i=0;i<256*256;i++)assert(MEM8(indexed?0x300010+i:0x280000+i*4+3)==(uint8_t)i);
 /* Invalid image/coordinate input and source-address reuse fail closed. */
 assert(story_caf_begin(0x10000));story_caf_lookup(0xffffffff,0,0);story_caf_lookup(0x3fffff0,0,0);
 story_caf_lookup(raw,0,0);story_caf_lookup(raw,0,0);assert(find(raw));story_caf_destroy(raw);assert(!find(raw));
 story_caf_layer(0x500000,raw,0xfffffff0);assert(s_failed);story_caf_end();
 s_contexts[1]=context;s_recipes[1]=authored;MEM32(context+8)=0x20000-0x8b0;
 assert(story_caf_begin(0x10000));story_caf_lookup(0x100000,0,0);story_caf_convert(0x100000,0x300000);
 assert(story_caf_begin(0x20000)==-1);story_caf_lookup(0xffffffff,0,0);story_caf_end();
 assert(s_visual==0x10000 && s_failed && !s_nested);story_caf_end();assert(!s_visual && calls==1);
 story_caf_invalidate(0x10000,-1);
 assert(story_caf_begin(0x10000));story_caf_lookup(0x100000,0,0);story_caf_convert(0x100000,0x300000);story_caf_end();
 assert(calls==2);old_clears=clears;
 assert(story_caf_evict()==1 && clears==old_clears+1 && !story_caf_evict());
 return 0;
}
'''

@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cc') or shutil.which('clang')
    if not cc:pytest.skip('C compiler unavailable')
    if not (ROOT/'tools/xboxrecomp/src/nv2a/texture_pack.h').is_file():
        pytest.skip('native Story compositor fixture needs the initialized toolkit submodule')
    p=tmp_path_factory.mktemp('story-caf-native');(p/'recomp/gen').mkdir(parents=True)
    (p/'recomp/gen/recomp_types.h').write_text(TYPES)
    (p/'kernel').mkdir();(p/'kernel/xbox_memory_layout.h').write_text('#include <stdint.h>\nuint32_t xbox_PhysRamName(uint32_t);\n')
    header=(ROOT/'tools/xboxrecomp/src/nv2a/texture_pack.h').read_text()
    header=header.replace('#include "../d3d/d3d8_xbox.h"','typedef struct IDirect3DDevice8 IDirect3DDevice8;\ntypedef struct IDirect3DBaseTexture8 IDirect3DBaseTexture8;')
    (p/'texture_pack.h').write_text(header)
    ownership=definition((ROOT/'src/patches/fighter_caf.c').read_text(),'defjam_fighter_caf_visual')
    (p/'main.c').write_text(DRIVER.replace('@CORE@',(ROOT/'src/patches/story_caf_pixels.c').as_posix()).replace('@ADAPTER@',(ROOT/'src/patches/story_caf_hd.c').as_posix()).replace('@OWNERSHIP@',ownership))
    exe=p/'test'
    cmd=[cc,'-std=c11','-Wall','-Wextra','-Werror','-I',str(p),'-I',str(ROOT/'src'),str(p/'main.c'),'-o',str(exe)]
    if os.name!='nt':cmd[1:1]=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
    return exe

@pytest.mark.parametrize('scale',[2,3,4])
@pytest.mark.parametrize('indexed',[0,1])
def test_native_alpha_palette_lifecycle_and_fallback(tool,scale,indexed):
    r=subprocess.run([str(tool),str(scale),str(indexed)],capture_output=True,text=True)
    assert r.returncode==0,r.stdout+r.stderr
