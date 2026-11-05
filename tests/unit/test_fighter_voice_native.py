"""Native voice adapter against invented guest tables and owned archive bytes."""
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_ui_native import TYPES
from test_fighter_voice_compile import source, voice
from fighter_voice_compile import encode_voice_bindings

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_voice.h"
unsigned char memory[0xC00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top, enabled=1;
static uint32_t calls,bank601,bank602,bank22;
static char previous[96];
static int fail_load;
int defjam_fighter_research_active(void) {return enabled;}
static void entry(void) {
 g_esp=0xB00000;g_eax=101;g_ecx=102;g_edx=103;
 g_ebx=104;g_esi=105;g_edi=106;g_ebp=107;g_fp_top=3;
}
void sub_0001C960(void) {
 uint32_t path=MEM32(g_esp+4);
 assert(path==0xAFFF00&&MEM32(g_esp+8)==0x290E24);
 const char *name=(const char*)XBOX_PTR(path);
 assert(strlen(name)<96&&strcmp(previous,name)<=0);
 strcpy(previous,name);
 if (strstr(name,"/601")) bank601++;
 if (strstr(name,"/602")) bank602++;
 if (strstr(name,"/022")) bank22++;
 assert(!strstr(name,"/005"));
 g_eax=fail_load?UINT32_MAX:calls;calls++;
 g_esp+=4;g_ebx=g_esi=g_edi=g_ebp=0xBAD;
}
static void environment(const char *key,const char *value) {
#ifdef _WIN32
 assert(!_putenv_s(key,value));
#else
 assert(!setenv(key,value,1));
#endif
}
int main(int argc,char **argv) {
 assert(argc==5);const char *mode=argv[4];
 environment("RECOMP_FIGHTER_VOICES",argv[1]);
 environment("RECOMP_FIGHTER_VOICE_BINDINGS",argv[2]);
 environment("RECOMP_FIGHTER_VOICES_SHA256",argv[3]);
 if (!strcmp(mode,"inactive")) enabled=0;
 int started=defjam_fighter_voice_start();
 if (!strcmp(mode,"reject")||!strcmp(mode,"inactive")) {assert(!started);return 0;}
 assert(started&&!strcmp(defjam_fighter_voice_path(),argv[1]));
 entry();assert(!defjam_fighter_voice_load(1)&&g_esp==0xB00000);
 for(uint32_t slot=0;slot<4;slot++) {
  MEM32(0x2020+slot*0x18)=(uint32_t[]){257,258,3,260}[slot];
  MEM32(0x3403A4+slot*0x64)=5;
  MEM32(0x3403B4+slot*0x64)=slot==2?22:5;
 }
 for(uint32_t i=0;i<256;i++) MEM32(0x332330+i*0x88)=UINT32_MAX;
 memset(XBOX_PTR(0x33EA78),0xA5,200);
 MEM32(0x2DD8B8)=0x4000;MEM32(0x2DD8BC)=0x4020;
 strcpy((char*)XBOX_PTR(0x4000),"Zeta");strcpy((char*)XBOX_PTR(0x4020),"Alpha");
 MEM32(0x2DD6E0)=0x4040;strcpy((char*)XBOX_PTR(0x4040),"One");
 if (!strcmp(mode,"capacity")) for(uint32_t i=0;i<256;i++) MEM32(0x332330+i*0x88)=0;
 if (!strcmp(mode,"load-failure")) fail_load=1;
 entry();defjam_fighter_voice_select(0x2000);assert(g_esp==0xB00000);
 assert(defjam_fighter_voice_load(1));
 assert(g_esp==0xB00004&&g_ebx==104&&g_esi==105&&g_edi==106&&g_ebp==107&&g_fp_top==3);
 assert(calls==11&&bank601==3&&bank602==3&&bank22==3);
 assert(MEM32(0x3403B4)==601&&MEM32(0x340418)==601&&MEM32(0x34047C)==22&&MEM32(0x3404E0)==602);
 for(uint32_t slot=0;slot<4;slot++) assert(MEM8(0x3403B9+slot*0x64)==1&&MEM32(0x3403A4+slot*0x64)==5);
 for(uint32_t i=0;i<200;i++) assert(MEM8(0x33EA78+i)==0xA5);
 // Reload must rebuild its local set; no stale 'already loaded' state.
 previous[0]=0;MEM8(0x33EBC0)=1;entry();assert(defjam_fighter_voice_load(0));
 assert(calls==21&&bank601==6&&bank602==6&&bank22==6);
 // Empty participant clears only native loaded status; absent voice preserves it.
 MEM32(0x340408)=UINT32_MAX;MEM32(0x34047C)=UINT32_MAX;MEM8(0x340481)=42;
 previous[0]=0;entry();assert(defjam_fighter_voice_load(0));
 assert(calls==28&&MEM8(0x34041D)==0&&MEM8(0x340481)==42);
 // Native early-out retains the current selection; a new retail setup clears it.
 MEM8(0x340540)=1;defjam_fighter_voice_select(0);MEM8(0x340540)=0;
 for(uint32_t slot=0;slot<4;slot++) MEM32(0x2020+slot*0x18)=3;
 defjam_fighter_voice_select(0x2000);entry();assert(!defjam_fighter_voice_load(1)&&g_esp==0xB00000);
 puts("voice namespaces, shared IDs, mixed retail, reload and ABI passed");return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-voice-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER, encoding='utf-8')
    exe = folder / ('voice.exe' if os.name == 'nt' else 'voice')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_voice.c')]
    if os.name == 'nt':
        command = [cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                   '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
    else:
        command = [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra', '-Werror',
                   '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-o', str(exe)]
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    _, compiler = source()
    data, report = compiler.compose({'alpha/voice': voice(1), 'beta/voice': voice(2)})
    path, bindings = tmp_path / 'speech.viv', tmp_path / 'voices.bin'
    path.write_bytes(data)
    bindings.write_bytes(encode_voice_bindings(data, report,
                         {256: 'alpha/voice', 257: 'alpha/voice', 259: 'beta/voice'}))
    return path, bindings, report['sha256']


@pytest.mark.parametrize('mode', ['good', 'inactive'])
def test_voice_loader_abi_and_namespace(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode,message', [('capacity', 'insufficient free slots'),
                                         ('load-failure', 'registration failed')])
def test_native_loader_failures_stop_before_invalid_playback(tool, files, mode, message):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 1 and message in result.stderr


@pytest.mark.parametrize('offset,value', [(0, 0), (4, 2), (8, 0), (8, 16384), (12, 0),
                                        (48, 140), (48, 16384), (56, 256), (52, 599), (52, 65535)])
def test_invalid_voice_receipt_is_rejected(tool, files, offset, value):
    path, bindings, digest = files
    data = bytearray(bindings.read_bytes())
    struct.pack_into('<I', data, offset, value)
    bindings.write_bytes(data)
    result = subprocess.run([tool, path, bindings, digest, 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
