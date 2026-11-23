"""Execute the real ControllerSetup shim, including moved banks and native argument parsing."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from test_fighter_match_teardown_native import definition
from test_fighter_ui_native import TYPES

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
unsigned char memory[0x10000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
static uint32_t selected, calls;
uint32_t defjam_fighter_controller_submission(uint32_t arguments) {
 assert(arguments==0x7000);return selected;
}
void sub_000558E0_gen(void) {
 uint32_t args=MEM32(g_esp+4);char *end;
 assert(MEM32(g_esp)==0x12345678&&MEM32(g_esp+8)==0xABC);
 assert(MEM32(args)==0x7100&&MEM32(args+4)==0x7200&&MEM32(args+12)==0x7400);
 assert(g_ecx==0x800&&g_ebx==0xBEEF);
 char *text=(char *)memory+MEM32(args+8);
 unsigned long parsed=strtoul(text,&end,10);
 assert(!*end&&parsed==(selected==UINT32_MAX?56:selected));
 if(selected==UINT32_MAX)assert(args==0x7000);else assert(args!=0x7000);
 calls++;g_esp+=12;g_eax=0x4321;g_ecx=0x9876;g_edx=0x2468;
}
@WRAPPER@
int main(int argc,char **argv) {
 assert(argc==2);selected=(uint32_t)strtoul(argv[1],NULL,10);
 g_esp=0x8000;g_ecx=0x800;g_ebx=0xBEEF;
 MEM32(g_esp)=0x12345678;MEM32(g_esp+4)=0x7000;MEM32(g_esp+8)=0xABC;
 for(uint32_t i=0;i<4;i++)MEM32(0x7000+i*4)=0x7100+i*0x100;
 strcpy((char *)memory+0x7300,"56");
 sub_000558E0();
 assert(calls==1&&g_esp==0x800C&&g_ebx==0xBEEF);
 assert(g_eax==0x4321&&g_ecx==0x9876&&g_edx==0x2468);
 assert(MEM32(0x7008)==0x7300&&!strcmp((char *)memory+0x7300,"56"));
 return 0;
}
'''


@pytest.fixture(scope='module')
def controller_shim(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('Native compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-controller-shim')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    wrapper = definition((ROOT / 'src/recomp_manual.c').read_text(encoding='utf-8'), 'sub_000558E0')
    source = folder / 'probe.c'
    source.write_text(DRIVER.replace('@WRAPPER@', wrapper), encoding='utf-8')
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS', '/I' + str(folder),
                str(source), '/Fe:' + str(exe)] if os.name == 'nt' else
               [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(folder), str(source), '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.mark.parametrize('bank', [100, 101, 102, 103, 124, 125, 126, 127, 0xffffffff])
def test_controller_shim_preserves_frame_and_passes_decimal_bank(controller_shim, bank):
    result = subprocess.run([str(controller_shim), str(bank)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
