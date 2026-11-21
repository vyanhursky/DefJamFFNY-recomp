"""UI capacity adapter against an invented guest and native-call stand-ins."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
TYPES = r'''
#ifndef TEST_GUEST_TYPES
#define TEST_GUEST_TYPES
#include <stdint.h>
#define RECOMP_TLS
extern unsigned char memory[];
extern uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
extern int g_fp_top;
#define MEM8(a) (*(uint8_t *)(memory+(a)))
#define MEM32(a) (*(uint32_t *)(memory+(a)))
#define XBOX_PTR(a) (memory+(a))
#endif
'''
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_ui.h"
unsigned char memory[0xB00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top, enabled=1;
static uint32_t population, visited, calls;
int defjam_fighter_research_active(void) { return enabled; }
void sub_0010A970(void) {
    uint32_t cursor=MEM32(g_esp+8), result=MEM32(g_esp+12), index=MEM32(cursor);
    assert(g_ecx==0x2000 && MEM32(g_esp+4)==0x2B7230);
    if (index<population) {
        uint32_t ordinal=(population-1-index)%4000;
        MEM32(result)=0x10000+ordinal*256;
        MEM32(cursor)=index+1;
        g_eax=1;
    } else g_eax=0;
    g_esi=0xBAD; g_edi=0xBAD; g_ebp=0xBAD;
    g_esp+=16;
}
void sub_001813E0_gen(void) {
    assert(g_esp==0xA00000 && MEM32(g_esp+4)==0x1000);
    assert(MEM32(g_esp+8)==777 && MEM32(g_esp+12)==888);
    assert(g_ecx==42 && g_esi==43 && g_edi==44 && g_ebp==45);
    MEM32(0x8FFFFC)=MEM32(0x900800)=0xFEED;
    assert(defjam_fighter_ui_model_batch(0x1000,0x900000,512));
    assert(MEM32(0x8FFFFC)==0xFEED && MEM32(0x900800)==0xFEED);
    int empty=0;
    for (uint32_t i=0;i<512;i++) {
        uint32_t model=MEM32(0x900000+i*4);
        if (!model) { empty=1; continue; }
        assert(!empty && model==0x10000+visited*256);
        assert(MEM32(model+4)==0);
        MEM32(model+4)++;
        visited++;
    }
    calls++; g_eax=99; g_ecx=100; g_esp+=4;
}
int main(int argc,char **argv) {
    if (argc!=3) return 2;
    population=(uint32_t)atoi(argv[1]); enabled=atoi(argv[2]);
    for (uint32_t i=0;i<4000;i++) {
        uint32_t model=0x10000+i*256;
        MEM32(model+0xB4)=model+0xC0;
        sprintf((char *)XBOX_PTR(model+0xC0),"%u",i*2+3);
    }
    MEM32(0x1094)=0x2000;
    g_esp=0xA00000; MEM32(g_esp+4)=0x1000;
    MEM32(g_esp+8)=777; MEM32(g_esp+12)=888;
    g_ecx=42; g_esi=43; g_edi=44; g_ebp=45;
    assert(!defjam_fighter_ui_model_batch(0x1000,0x900000,512));
    int handled=defjam_fighter_ui_normalize(0x1000);
    assert(handled==enabled);
    assert(!defjam_fighter_ui_model_batch(0x1000,0x900000,512));
    if (enabled) {
        assert(visited==population && calls==(population ? (population+511)/512 : 1));
        assert(g_esp==0xA00004 && g_eax==99);
    } else assert(!calls && !visited && g_esp==0xA00000 && g_ecx==42);
    printf("visited=%u calls=%u\n",visited,calls);
    return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-ui')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES)
    (folder / 'host.h').write_text('')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER)
    exe = folder / ('ui.exe' if os.name == 'nt' else 'ui')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_ui.c'), str(ROOT / 'src/patches/fighter_fatal.c'), str(ROOT / 'src/patches/fighter_config.c'), str(ROOT / 'tests/unit/native_stubs/host_fatal.c')]
    if os.name == 'nt':
        command = [cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                   '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
    else:
        command = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                   '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-o', str(exe)]
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.mark.parametrize('count', [0, 1, 511, 512, 513, 1100])
def test_each_sparse_model_is_visited_once_without_stack_overflow(tool, count):
    result = subprocess.run([tool, str(count), '1'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'visited={count}' in result.stdout


def test_retail_calls_bypass_and_excessive_enumeration_fails(tool):
    result = subprocess.run([tool, '1100', '0'], capture_output=True, text=True)
    assert result.returncode == 0 and 'visited=0 calls=0' in result.stdout
    result = subprocess.run([tool, '16385', '1'], capture_output=True, text=True)
    assert result.returncode == 1 and 'exceeds its budget' in result.stderr
