"""Actual CAF extras admission, RGB/alpha ownership and finisher slot routing."""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

import pytest

from test_fighter_match_teardown_native import definition
from test_fighter_motion_native import TYPES
from fighter_caf_extras import encode

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hooks/guest_call.h"
unsigned char memory[0xC00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
#define CAF_ROW 232u
#define CAF_MAX 16384u
#define EXTRA_ROW 48u
#define ATLAS_BYTES (256u*256u*4u)
#define EXTRA_MAX (16u*1024u*1024u)
static uint8_t *s_rows,*s_extras;
static uint32_t s_count,s_extra_count,s_service,s_contexts[4];
static uint32_t s_row_stride=CAF_ROW,s_extra_stride=EXTRA_ROW;
static const uint8_t *s_recipes[4];
static uint32_t s_finisher_before[4][4],s_finisher_applied[4][4];
static uint8_t s_finisher_live[4];
static unsigned converted,rebound,freed;
static int test_linear;
static void defjam_caf_faces_clear(void) {} /* Sculpt lifetime is tested separately. */
static uint32_t test_visual=0x10000;
static void stop(const char *why) {fprintf(stderr,"CAF stopped: %s\n",why);exit(1);}
void sub_00092BE0(void) {
 uint32_t old=MEM32(g_esp+4),clone=0x300000+converted*0x50000;
 assert(MEM16(old+4)==256 && MEM16(old+6)==256 && MEM32(g_esp+8)==0x7D);
 MEM32(clone)=0x7D;MEM16(clone+4)=MEM16(clone+6)=256;
 MEM32(clone+12)=test_linear?0:0x2000;
 memset(XBOX_PTR(clone+16),219,ATLAS_BYTES);
 for(uint32_t i=0;i<256u*256u;++i) MEM8(clone+16+i*4+3)=(uint8_t)i;
 ++converted;g_eax=clone;g_esp+=12;
}
void sub_00098270(void) {assert(!freed && g_ecx==test_visual);++rebound;g_esp+=4;}
void sub_001DE887(void) {assert(rebound==1 && MEM32(g_esp+4)==0x100000);++freed;g_esp+=4;}
@DEFINITIONS@
int main(int argc,char **argv) {
 assert(argc==3);const char *mode=argv[2];
 s_rows=(uint8_t *)calloc(1,16+CAF_ROW);assert(s_rows);s_count=1;
 uint32_t value=100;memcpy(s_rows+16,&value,4);value=101;memcpy(s_rows+20,&value,4);
 FILE *file=fopen(argv[1],"rb");assert(file);
 s_extras=(uint8_t *)malloc(EXTRA_MAX+1);assert(s_extras);
 size_t size=fread(s_extras,1,EXTRA_MAX+1,file);fclose(file);
 if(!strcmp(mode,"invalid")) {assert(!extras_valid(s_extras,size));return 0;}
 assert(extras_valid(s_extras,size));s_extra_count=word(s_extras+8);
 const uint8_t *extra=extra_row(100,0);assert(extra);
 g_esp=0xB00000;g_ecx=123;g_eax=456;g_ebx=789;
 if(!strcmp(mode,"art") || !strcmp(mode,"art-linear")) {
  test_linear=!strcmp(mode,"art-linear");
  MEM32(0x100000)=0x7B;MEM16(0x100004)=MEM16(0x100006)=256;
  MEM32(0x110000)=0x7B;MEM16(0x110004)=MEM16(0x110006)=256;
  MEM32(test_visual+0xA234)=0x100000; /* owned output */
  MEM32(test_visual+0xA240)=MEM32(test_visual+0xA258)=0x110000; /* borrowed base */
  MEM32(test_visual+0xA238)=0xABCD1234;
  apply_atlases(test_visual,extra);
  assert(converted==2 && rebound==1 && freed==1);
  assert(MEM32(test_visual+0xA238)==0xABCD1234 && MEM32(test_visual+0xA258)==0x110000);
  for(unsigned atlas=0;atlas<2;++atlas) {
   uint32_t p=MEM32(test_visual+0xA234+(atlas?3:0)*4)+16;
   for(uint32_t y=0;y<256;++y) for(uint32_t x=0;x<256;++x) {
    uint32_t at=y*256+x;
    if(!test_linear) {at=0;for(unsigned bit=0;bit<8;++bit) at|=((x>>bit)&1)<<(bit*2)|((y>>bit)&1)<<(bit*2+1);}
    assert(MEM8(p+at*4)==x && MEM8(p+at*4+1)==y && MEM8(p+at*4+2)==(x^y) && MEM8(p+at*4+3)==(uint8_t)at);
   }
  }
 } else if(!strcmp(mode,"finishers") || !strcmp(mode,"mismatch") || !strcmp(mode,"no-caf") || !strcmp(mode,"new-owner")) {
  s_service=0x50000;MEM32(s_service+0x1A9C)=0x60000;
  s_contexts[0]=0x60000;MEM8(0x60000)=MEM8(0x60001)=1;MEM32(0x60008)=0x70000;
  if(strcmp(mode,"no-caf")) s_recipes[0]=s_rows+16;
  MEM32(0x3B92E0+0x28)=100;MEM32(0x3B92E0+0x2C)=!strcmp(mode,"mismatch")?4:100;
  for(unsigned i=0;i<16;++i) MEM32(0x3B9288+i*4)=0xA5A5A5A5;
  defjam_fighter_caf_finishers();
  defjam_fighter_caf_finishers(); /* Repeated setup must not replace the journal. */
  for(unsigned i=0;i<16;++i) {
   uint32_t expected=i<4 && strcmp(mode,"no-caf")?word(extra+8+i*4):0xA5A5A5A5;
   assert(MEM32(0x3B9288+i*4)==expected);
  }
  if(!strcmp(mode,"new-owner")) {
   /* A native profile may initialize its choices before our next clear. */
   for(unsigned i=0;i<4;++i) MEM32(0x3B9288+i*4)=77+i;
  }
  defjam_fighter_caf_clear();
  for(unsigned i=0;i<16;++i) {
   uint32_t expected=i<4 && !strcmp(mode,"new-owner")?77+i:0xA5A5A5A5;
   assert(MEM32(0x3B9288+i*4)==expected);
  }
  assert(!s_service && !s_contexts[0] && !s_recipes[0]);
 } else return 2;
 assert(g_esp==0xB00000 && g_ecx==123 && g_eax==456 && g_ebx==789);
 puts("CAF extras native boundaries passed");return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('caf-extras-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES)
    text = (ROOT / 'src/patches/fighter_caf.c').read_text(encoding='utf-8')
    match = re.search(r'static const uint8_t \*extra_row\([^)]*\)\s*\{', text)
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    pointer = text[match.start():end]
    names = ('word', 'row_outfit', 'extras_valid', 'guest_span', 'swizzle8', 'defjam_fighter_caf_context', 'apply_atlases', 'restore_finishers', 'defjam_fighter_caf_finishers', 'defjam_fighter_caf_clear')
    definitions = '\n'.join([pointer, *(definition(text, name) for name in names)])
    # extra_row uses word, so the real word definition precedes it.
    match = re.search(r'static const uint8_t \*recipe_row\([^)]*\)\s*\{', text)
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    helpers = definition(text, 'word') + '\n' + definition(text, 'row_outfit') + '\n' + text[match.start():end]
    definitions = helpers + '\n' + definitions.replace(definition(text, 'word'), '').replace(definition(text, 'row_outfit'), '')
    driver = folder / 'driver.c'; driver.write_text(DRIVER.replace('@DEFINITIONS@', definitions))
    exe = folder / ('extras.exe' if os.name == 'nt' else 'extras')
    if os.name == 'nt':
        command = [cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS', '/I' + str(folder), '/I' + str(ROOT / 'src'), str(driver), '/Fe:' + str(exe)]
    else:
        command = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(folder), '-I', str(ROOT / 'src'), str(driver), '-o', str(exe)]
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def sidecar():
    pixels = bytes(component for y in range(256) for x in range(256) for component in (x, y, x ^ y, 0))
    return encode({'p/f': {'extras': {'finishers': [3, 5, 7, 11], 'atlases': {'a': pixels, 'd': pixels}}}},
                  {'bindings': {'p/f': {'selection_key': 100}}})


@pytest.mark.parametrize('mode', ['art', 'art-linear', 'finishers', 'no-caf', 'mismatch', 'new-owner'])
def test_native_rgb_alpha_ownership_and_finisher_routing(tool, tmp_path, mode):
    path = tmp_path / 'extras.bin'; path.write_bytes(sidecar())
    result = subprocess.run([tool, path, mode], capture_output=True, text=True)
    assert result.returncode == (1 if mode == 'mismatch' else 0), result.stdout + result.stderr
    assert ('actor differs' if mode == 'mismatch' else 'boundaries passed') in (result.stderr if mode == 'mismatch' else result.stdout)


@pytest.mark.parametrize('offset,value', [(0, 0), (4, 2), (12, 44), (16, 999), (20, 2), (24, 82), (40, 1), (40, 65)])
def test_native_reader_rejects_malformed_or_unbound_sidecars(tool, tmp_path, offset, value):
    raw = bytearray(sidecar()); struct.pack_into('<I', raw, offset, value)
    path = tmp_path / 'bad.bin'; path.write_bytes(raw)
    result = subprocess.run([tool, path, 'invalid'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
