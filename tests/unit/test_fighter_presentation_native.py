"""Loading/result UI IDs use participant bindings, never private bank portraits."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from test_fighter_match_teardown_native import definition
from test_fighter_ui_native import TYPES
from test_fighter_native import catalog, pack
from fighter_window import encode_window

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
unsigned char memory[0x10000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
static uint32_t formatted,loading_calls,result_calls,native_calls;
uint32_t defjam_fighter_loading_identity(uint32_t native) {
 loading_calls++;return native==102?257:native;
}
uint32_t defjam_fighter_result_identity(uint32_t slot,uint32_t native) {
 assert(slot==1);result_calls++;return native==101?118:native;
}
void sub_0005F810_gen(void) {
 assert(g_ecx==0x800&&g_ebp==0xDEAD&&g_ebx==1);
 formatted=MEM32(g_esp+8);native_calls++;
 // Simulate the real native formatter's ret8 and volatile return registers.
 g_esp+=12;g_eax=0x4321;g_ecx=0x9876;g_edx=0x2468;
}
@WRAPPER@
int main(int argc,char **argv) {
 assert(argc==5);
 uint32_t caller=(uint32_t)strtoul(argv[1],NULL,0),key=(uint32_t)strtoul(argv[2],NULL,0);
 uint32_t value=(uint32_t)strtoul(argv[3],NULL,0),expected=(uint32_t)strtoul(argv[4],NULL,0);
 g_esp=0x8000;g_ecx=0x800;g_ebp=0xDEAD;g_ebx=1;
 MEM32(g_esp)=caller;MEM32(g_esp+4)=key;MEM32(g_esp+8)=value;
 sub_0005F810();
 assert(formatted==expected&&native_calls==1&&g_esp==0x800C);
 assert(g_eax==0x4321&&g_ecx==0x9876&&g_edx==0x2468);
 assert(g_ebp==0xDEAD&&g_ebx==1&&MEM32(0x8008)==value);
 assert(loading_calls==(unsigned)(caller==0x46DA9));
 assert(result_calls==(unsigned)(caller==0x65653&&key==0x298C70));
 return 0;
}
'''


@pytest.fixture(scope='module')
def formatter(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('Native compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-presentation')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    wrapper = definition((ROOT / 'src/recomp_manual.c').read_text(encoding='utf-8'), 'sub_0005F810')
    source = folder / 'probe.c'
    source.write_text(DRIVER.replace('@WRAPPER@', wrapper), encoding='utf-8')
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    command = ([cc, '/nologo', '/W4', '/WX', '/I' + str(folder), str(source), '/Fe:' + str(exe)]
               if os.name == 'nt' else [cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                                       '-I', str(folder), str(source), '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.mark.parametrize('caller,key,value,expected', [
    (0x46DA9, 0x7000, 102, 257),
    (0x46DA9, 0x7000, 56, 56),
    (0x46DA9, 0x7000, 99, 99),
    (0x46DA9, 0x7000, 0xFFFFFFFF, 0xFFFFFFFF),
    (0x65653, 0x298C70, 101, 118),
    (0x65653, 0x298C74, 101, 101),
    (0x46DE7, 0x29314C, 102, 102),
    (0x46DFD, 0x293154, 102, 102),
    (0x12345, 0x298C70, 102, 102),
])
def test_actual_formatter_maps_only_loading_participants_and_result_fid(formatter, caller, key, value, expected):
    result = subprocess.run([str(formatter), *map(str, (caller, key, value, expected))],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


STATE = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fighter_window.h"
static FighterWindow s_window;
#ifdef _MSC_VER
__declspec(noreturn)
#else
_Noreturn
#endif
static void fighter_stop(const char *message) {fprintf(stderr,"%s\n",message);exit(23);}
@FUNCTIONS@
int main(int argc,char **argv) {
 assert(argc==3);FILE *file=fopen(argv[1],"rb");assert(file);
 uint8_t bytes[8192];size_t size=fread(bytes,1,sizeof bytes,file);fclose(file);
 assert(fighter_window_decode(&s_window,bytes,size));
 FighterWindowRow row;assert(fighter_window_bind(&s_window,0,257,&row));
 if(!strcmp(argv[2],"no-window")) {s_window.bytes=NULL;assert(defjam_fighter_loading_identity(100)==100);return 0;}
 assert(defjam_fighter_loading_identity(56)==56);
 assert(defjam_fighter_loading_identity(99)==99);
 assert(defjam_fighter_loading_identity(UINT32_MAX)==UINT32_MAX);
 assert(defjam_fighter_loading_identity(104)==104);
 if(!strcmp(argv[2],"wrong-native")) {s_window.banks[0].selection_key=101;defjam_fighter_loading_identity(100);return 1;}
 assert(defjam_fighter_loading_identity(100)==257&&!s_window.frozen);
 s_window.frozen=1;assert(defjam_fighter_loading_identity(100)==257);
 assert(defjam_fighter_result_identity(0,100)==257&&s_window.frozen);
 assert(fighter_window_finish(&s_window));
 assert(fighter_window_clear(&s_window,0));
 assert(defjam_fighter_loading_identity(100)==100);
 return 0;
}
'''


@pytest.fixture(scope='module')
def binding_state(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('Native compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-loading-binding')
    runtime = (ROOT / 'src/patches/fighter_runtime.c').read_text(encoding='utf-8')
    functions = '\n'.join(definition(runtime, name) for name in
                          ('defjam_fighter_loading_identity', 'defjam_fighter_result_identity'))
    source = folder / 'probe.c'
    source.write_text(STATE.replace('@FUNCTIONS@', functions), encoding='utf-8')
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    inputs = [str(source), str(ROOT / 'src/hooks/fighter_window.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                '/I' + str(ROOT / 'src/hooks'), *inputs, '/Fe:' + str(exe)] if os.name == 'nt'
               else [cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                     '-I', str(ROOT / 'src/hooks'), *inputs, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    _, report = catalog(menu=True)[0].compile([pack(count=300)], binding_window=True)
    window = folder / 'window.bin'
    window.write_bytes(encode_window(report['window']))
    return exe, window


@pytest.mark.parametrize('mode', ['good', 'no-window', 'wrong-native'])
def test_loading_queries_live_selection_before_and_after_freeze(binding_state, mode):
    exe, window = binding_state
    result = subprocess.run([str(exe), str(window), mode], capture_output=True, text=True, timeout=10)
    assert result.returncode == (23 if mode == 'wrong-native' else 0), result.stdout + result.stderr
