"""Real CAF/motion/voice audio composition on invented guest memory and resources."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from test_fighter_match_teardown_native import definition
from test_fighter_motion_native import TYPES, files as motion_files
from test_fighter_voice_compile import source, voice
from fighter_voice_compile import encode_voice_bindings

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hooks/guest_call.h"
#include "patches/fighter_motion.h"
#include "patches/fighter_voice.h"
unsigned char memory[0xC00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
static uint32_t s_service,s_contexts[4],expected[4],calls,owned_voice;
static const uint8_t *s_recipes[4];
static uint8_t recipes[2][232];
static uint32_t word(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void put(uint8_t *p,uint32_t n) { for(unsigned j=0;j<4;++j) p[j]=(uint8_t)(n>>(8*j)); }
static void stop(const char *message) { fprintf(stderr,"CAF stopped: %s\n",message);exit(1); }
int defjam_fighter_research_active(void) { return 1; }
void sub_001A3AD0(void) { abort(); }
void sub_001A3630(void) { abort(); }
void sub_001C60D0(void) { abort(); }
void sub_000444E0(void) { abort(); }
void sub_00011520(void) { abort(); }
void sub_0001C960(void) { abort(); } /* Rematch must not reload a voice bank. */
void sub_0003E170_gen(void) {
 if(MEM8(0x340540)) {g_esp+=4;return;}
 uint32_t input=MEM32(g_esp+4);
 assert(MEM32(input)==0xA5A5A5A5 && MEM8(input+0x81)==0xA5);
 for(unsigned i=0;i<4;++i) {
  uint32_t core=MEM32(input+0x20+i*0x18);assert(core==expected[i]);
  MEM32(0x3403A4+i*0x64)=core;
  MEM32(0x3403B4+i*0x64)=core;
 }
 ++calls;g_eax=0xA5000001;g_esp+=4;g_ebx=g_esi=g_edi=g_ebp=0xBAD;
}
@CAF_AUDIO@
@CAF_CLEAR@
@AUDIO_WRAPPER@
static void environment(const char *key,const char *value) {
#ifdef _WIN32
 assert(!_putenv_s(key,value));
#else
 assert(!setenv(key,value,1));
#endif
}
static void entry(void) {
 g_esp=0xB00000;MEM32(g_esp+4)=0x2000;
 g_eax=101;g_ecx=102;g_edx=103;g_ebx=104;g_esi=105;g_edi=106;g_ebp=107;g_fp_top=3;
}
static void run(const uint32_t *cores,int adapted) {
 uint8_t before[0x84];memset(XBOX_PTR(0x2000),0xA5,sizeof before);
 for(unsigned i=0;i<4;++i) {
  MEM32(0x2020+i*0x18)=cores[i];MEM32(0x3B90B8+i*4)=cores[i];
 }
 memcpy(before,XBOX_PTR(0x2000),sizeof before);
 for(unsigned repeat=0;repeat<2;++repeat) {
  entry();uint32_t previous=calls;sub_0003E170();
  assert(calls==previous+1 && g_eax==0xA5000001 && g_esp==0xB00004);
  if(adapted) assert(g_ebx==104&&g_esi==105&&g_edi==106&&g_ebp==107&&g_ecx==102&&g_fp_top==3);
  assert(!memcmp(before,XBOX_PTR(0x2000),sizeof before));
  for(unsigned i=0;i<4;++i) {
   assert(MEM32(0x3B90B8+i*4)==cores[i]);
   assert(MEM32(0x3403B4+i*0x64)==(cores[i]==142?owned_voice:expected[i]));
  }
 }
}
int main(int argc,char **argv) {
 assert(argc==9);owned_voice=(uint32_t)strtoul(argv[8],NULL,10);
 const char *keys[]={"RECOMP_FIGHTER_MOTION","RECOMP_FIGHTER_MOTION_BINDINGS","RECOMP_FIGHTER_MOTION_SHA256",
 "RECOMP_FIGHTER_VOICES","RECOMP_FIGHTER_VOICE_BINDINGS","RECOMP_FIGHTER_VOICES_SHA256"};
 for(unsigned i=0;i<6;++i) environment(keys[i],argv[i+1]);
 assert(defjam_fighter_motion_start()&&defjam_fighter_voice_start());
 put(recipes[0]+4,87);put(recipes[0]+228,63);
 put(recipes[1]+4,87);put(recipes[1]+228,5);
 for(unsigned rotate=0;rotate<4;++rotate) {
  uint32_t cores[4];defjam_fighter_caf_clear();
  for(unsigned i=0;i<4;++i) {
   unsigned role=(i+rotate)%4;
   cores[i]=(uint32_t[]){87,142,3,87}[role];expected[i]=(uint32_t[]){63,5,3,5}[role];
   if(role==0||role==3) s_recipes[i]=recipes[role==3];
  }
  if(!strcmp(argv[7],"mismatch")) {cores[0]=88;expected[0]=63;}
  if(!strcmp(argv[7],"unknown")) cores[1]=1000;
  run(cores,1);
  // Native early-out may pass no usable input; retain live participant state.
  entry();MEM32(g_esp+4)=0;MEM8(0x340540)=1;uint32_t previous=calls;
  sub_0003E170();assert(calls==previous&&g_esp==0xB00004);MEM8(0x340540)=0;
 }
 // A CAF with no owned motion takes the native fallback; empty slots survive.
 defjam_fighter_caf_clear();s_recipes[0]=recipes[0];
 uint32_t caf_only[]={87,3,3,UINT32_MAX};
 expected[0]=63;expected[1]=expected[2]=3;expected[3]=UINT32_MAX;run(caf_only,1);
 uint32_t sparse[]={87,142,3,UINT32_MAX};expected[1]=5;run(sparse,1);
 // Clear followed by owned/retail setup must not retain either CAF donor.
 defjam_fighter_caf_clear();
 assert(!s_service);for(unsigned i=0;i<4;++i) assert(!s_contexts[i]&&!s_recipes[i]);
 for(unsigned i=0;i<4;++i) expected[i]=i?3:5;
 uint32_t owned[]={142,3,3,3};run(owned,1);
 for(unsigned i=0;i<4;++i) expected[i]=3;
 uint32_t retail[]={3,3,3,3};run(retail,0);
 puts("mixed CAF/owned/retail audio, four slots, Rematch, clear and ABI passed");return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('caf-mixed-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES)
    caf = (ROOT / 'src/patches/fighter_caf.c').read_text(encoding='utf-8')
    manual = (ROOT / 'src/recomp_manual.c').read_text(encoding='utf-8')
    text = DRIVER.replace('@CAF_AUDIO@', definition(caf, 'defjam_fighter_caf_audio'))
    text = text.replace('@CAF_CLEAR@', definition(caf, 'defjam_fighter_caf_clear'))
    text = text.replace('@AUDIO_WRAPPER@', definition(manual, 'sub_0003E170'))
    driver = folder / 'driver.c'; driver.write_text(text)
    exe = folder / ('mixed.exe' if os.name == 'nt' else 'mixed')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_motion.c'), str(ROOT / 'src/patches/fighter_voice.c')]
    if os.name == 'nt':
        command = [cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS', '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
    else:
        command = [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra', '-Werror', '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-lm', '-o', str(exe)]
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.fixture
def voice_files(tmp_path):
    _, compiler = source()
    data, receipt = compiler.compose({'owned/voice': voice(1)})
    path, bindings = tmp_path / 'speech.viv', tmp_path / 'voices.bin'
    path.write_bytes(data); bindings.write_bytes(encode_voice_bindings(data, receipt, {141: 'owned/voice'}))
    return path, bindings, receipt['sha256'], receipt['bindings']['owned/voice']['voice_id']


@pytest.mark.parametrize('mode,message', [('mixed', None), ('mismatch', 'CAF audio core differs'), ('unknown', 'unknown audio template core')])
def test_mixed_audio_composes_once_and_preserves_owned_voices(tool, motion_files, voice_files, mode, message):
    result = subprocess.run([tool, *motion_files, *voice_files[:3], mode, str(voice_files[3])], capture_output=True, text=True)
    assert result.returncode == (1 if message else 0), result.stdout + result.stderr
    assert (message or 'mixed CAF/owned/retail audio') in (result.stderr if message else result.stdout)
