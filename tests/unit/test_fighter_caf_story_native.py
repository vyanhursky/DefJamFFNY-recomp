"""Profile-owned CAFs borrow retail motion without borrowing another profile."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from test_fighter_match_teardown_native import definition
from test_fighter_motion_native import TYPES

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hooks/guest_call.h"
#include "patches/fighter_caf_layout.h"
unsigned char memory[0xC00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
static uint8_t s_story_rows[4][CAF_ROW_STRIDE];
static uint32_t s_story_profiles[4],constructed;
static uint32_t s_service,s_contexts[4];
static const uint8_t *s_recipes[4];
static const uint32_t test_service=0x10000,test_manager=0x20000,test_game=0x90000,participants=0xA0000;
static int profile_index;
static int runtime_active=1;
int defjam_fighter_runtime_active(void) {return runtime_active;}
static int guest_span(uint32_t p,uint32_t n) {return p && p<sizeof memory && n<=sizeof memory-p;}
void sub_0001E8F0(void) {
 assert(g_ecx==test_service && MEM32(g_esp+4)==0);
 /* Original function returns a signed byte, with unrelated upper bits. */
 g_eax=0xABCD0000u|(uint8_t)profile_index;g_esp+=8;
}
void sub_0001E410_gen(void) {
 assert(g_ecx==test_service && MEM32(g_esp+4)==0);
 ++constructed;g_eax=0xB0000;g_esp+=8;
}
@STORY@
int main(int argc,char **argv) {
 assert(argc==2);const char *mode=argv[1];uint32_t profile=test_manager+0x177c;
 MEM32(test_service)=test_game;MEM32(test_service+4)=test_manager;MEM32(test_service+0x344)=1;
 MEM8(test_service+0x1aaa)=99;MEM32(participants)=0x07000042; /* Packed SODB handle, not selection99. */
 for(unsigned i=1;i<4;++i)MEM32(participants+i*4)=UINT32_MAX;
 MEM32(test_service+0x168)=5;MEM8(profile+0x143)=5;MEM8(profile+0x4d93)=109;
 MEM8(profile+0x140)=0;MEM8(profile+0x141)=255;MEM8(profile+0x142)=255;
 memset(XBOX_PTR(profile+0x5564),37,152);memset(XBOX_PTR(profile+0x55fc),17,38);
 int expected=1;
 if(!strcmp(mode,"story")){MEM32(test_service+0x344)=0;MEM32(test_game+0x14)=0;MEM8(test_game+0x18)=1;}
 if(!strcmp(mode,"retail")){MEM8(test_service+0x1aaa)=5;expected=0;}
 if(!strcmp(mode,"caf")){MEM32(test_service+0x168)=87;expected=0;}
 if(!strcmp(mode,"guest")){profile_index=-1;expected=0;}
 if(!strcmp(mode,"inactive")){runtime_active=0;expected=0;}
 int degraded=0;
 if(!strcmp(mode,"career")){MEM8(profile+0x4d93)=5;expected=0;}
 if(!strcmp(mode,"mismatch")){MEM8(profile+0x143)=6;degraded=1;}
 if(!strcmp(mode,"styles")){MEM8(profile+0x140)=5;degraded=1;}
 if(!strcmp(mode,"no-styles")){MEM8(profile+0x140)=255;degraded=1;}
 if(degraded)expected=0;
 uint8_t before[0x5950];memcpy(before,XBOX_PTR(profile),sizeof before);
 g_esp=0xB00000;g_eax=123;g_ecx=456;
 defjam_fighter_caf_story(test_service,participants);
 assert(constructed==(uint32_t)expected && !memcmp(before,XBOX_PTR(profile),sizeof before));
 /* The adapter could not take the slot: the participant gets its career core and nothing else changes. */
 if(degraded)assert(MEM32(test_service+0x168)==109 && !s_story_profiles[0] && !s_recipes[0]);
 /* Save contents alone (no profile, no career) and no pack at all leave the slot to the game. */
 if(!strcmp(mode,"guest")||!strcmp(mode,"career")||!strcmp(mode,"inactive"))
  assert(MEM32(test_service+0x168)==5 && !s_story_profiles[0] && !s_recipes[0] && !s_service);
 assert(g_esp==0xB00000 && g_eax==123 && g_ecx==456);
 assert(!expected || s_story_profiles[0]==profile);
 if(expected) {
  assert(s_service==test_service && s_contexts[0]==0xB0000 && s_recipes[0]==s_story_rows[0]);
  uint32_t value;memcpy(&value,s_recipes[0]+CAF_ROW_CORE,4);assert(value==5);
  memcpy(&value,s_recipes[0]+CAF_ROW_VOICE,4);assert(value==109);
  assert(!memcmp(s_recipes[0]+CAF_ROW_VALUES,XBOX_PTR(profile+0x5564),152));
  assert(!memcmp(s_recipes[0]+CAF_ROW_COLORS,XBOX_PTR(profile+0x55fc),38));
 }
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('caf-story-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES)
    source = (ROOT / 'src/patches/fighter_caf.c').read_text()
    driver = folder / 'driver.c'
    driver.write_text(DRIVER.replace('@STORY@', definition(source, 'story_fallback') + '\n' + definition(source, 'defjam_fighter_caf_story')))
    exe = folder / ('story.exe' if os.name == 'nt' else 'story')
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS', '/I'+str(folder), '/I'+str(ROOT/'src'), str(driver), '/Fe:'+str(exe)]
        if os.name == 'nt' else [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(folder), '-I', str(ROOT/'src'), str(driver), '-o', str(exe)])
    result = subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode == 0,result.stdout+result.stderr
    return exe


@pytest.mark.parametrize('mode', ['battle','story','retail','caf','guest','career','mismatch','styles','no-styles','inactive'])
def test_story_profile_context_bounds_and_preservation(tool,mode):
    result = subprocess.run([tool,mode],capture_output=True,text=True)
    # Review E3: nothing a save holds may close the game here, and with no pack it does nothing.
    assert result.returncode == 0,result.stdout+result.stderr
    if mode in ('guest','career'):
        assert 'left to the game' in result.stderr
    if mode in ('mismatch','styles','no-styles'):
        assert 'playing its career moveset 109' in result.stderr
