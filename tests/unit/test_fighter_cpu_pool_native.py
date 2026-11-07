"""Owned-file routing, ABI preservation, bounds and native release invariants."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from test_fighter_ui_native import TYPES

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_cpu_pool.h"
unsigned char memory[48u*1024u*1024u];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp,g_seh_ebp;
int g_fp_top;
static unsigned reservations,registrations;
static int enabled=1;
static const char *mode;
static uint32_t first=0x500200,root=0x500110,free_bytes=32u*1024u*1024u-768;
int defjam_fighter_finisher_cpu_file(const char *path) {
 return enabled&&!strcmp(path,"motion/blazin.viv|P0000_A.ord");
}
uint32_t xbox_HeapAlloc(uint32_t bytes,uint32_t alignment) {
 assert(bytes==32u*1024u*1024u&&alignment==128);reservations++;
 return !strcmp(mode,"reserve")?0:0x500000;
}
void sub_001E9640(void) {
 assert(MEM32(g_esp+4)==63&&MEM32(g_esp+8)==0x500000);
 assert(MEM32(g_esp+12)==0x500100&&MEM32(g_esp+16)==32u*1024u*1024u-256);
 assert(MEM32(g_esp+20)==16&&MEM32(g_esp+24)==128);
 assert(!MEM32(g_esp+28)&&!MEM32(g_esp+32)&&!MEM32(g_esp+36)&&MEM32(g_esp+40)==1);
 assert(!strcmp((char*)memory+0x500000,"Fighter CPU animation"));
 MEM32(0x3C9254)=root;MEM32(root+0x20)=MEM32(root+0x24)=first;
 MEM16(first)=0x4246;MEM32(first+4)=free_bytes;
 MEM32(first+0x10)=MEM32(first+0x14)=root+0x10;
 registrations++;g_eax=7;g_ecx=8;g_ebx=9;g_seh_ebp=10;g_esp+=4;
}
void sub_00029500(void) {
 assert(MEM32(g_esp+12)==0x8000003F);
 g_eax=first+16;MEM8(g_eax-14)=63;g_ecx=0xBAD;g_esp+=4;
}
/*BRIDGE*/
int main(int argc,char **argv) {
 assert(argc==2);mode=argv[1];g_esp=0x4F0000;g_eax=42;g_ecx=43;g_ebx=44;g_seh_ebp=45;
 strcpy((char*)memory+0x1000,"motion/blazin.viv|P0000_A.ord");
 strcpy((char*)memory+0x1100,"motion/blazin.viv|N0304_A.ord");
 assert(defjam_fighter_cpu_flags(0x123,0x1000,512,0)==0);
 assert(defjam_fighter_cpu_flags(0x1E43E8,0x1000,512,0)==0);
 assert(defjam_fighter_cpu_flags(0x1E4453,0x1100,512,0)==0);
 assert(!reservations&&!defjam_fighter_cpu_contains(0x500200));
 if(!strcmp(mode,"inactive")){enabled=0;assert(!defjam_fighter_cpu_flags(0x1E4453,0x1000,512,0));return 0;}
 if(!strcmp(mode,"occupied"))MEM32(0x3C9254)=0x1234;
 uint32_t bytes=!strcmp(mode,"budget")?32u*1024u*1024u:512;
 uint32_t flags=!strcmp(mode,"flags")?2:0;
 assert(defjam_fighter_cpu_flags(0x1E4453,0x1000,bytes,flags)==0x8000003F);
 assert(reservations==1&&registrations==1&&g_eax==42&&g_ecx==43&&g_ebx==44&&g_esp==0x4F0000&&g_seh_ebp==45);
 uint32_t callers[]={0x1E3F20,0x1E4057,0x1E4453,0x1E473D,0x1E477A};
 for(unsigned i=0;i<sizeof(callers)/sizeof(callers[0]);++i)
  assert(defjam_fighter_cpu_flags(callers[i],0x1000,512,256)==0x8000013F);
 MEM32(g_esp)=0x1E4057;MEM32(g_esp+4)=0x1000;MEM32(g_esp+8)=512;MEM32(g_esp+12)=0;
 fighter_archive_allocate();
 assert(g_esp==0x4F0004&&g_eax==first+16&&g_ecx==0xBAD&&MEM32(0x4F000C)==0);
 if(!strcmp(mode,"null"))defjam_fighter_cpu_result(0,512);
 if(!strcmp(mode,"escape"))defjam_fighter_cpu_result(0x24FFFF0,512);
 if(!strcmp(mode,"owner")){MEM8(first+2)=0;defjam_fighter_cpu_result(first+16,512);}
 if(!strcmp(mode,"leak"))MEM32(first+4)--;
 if(!strcmp(mode,"registry"))MEM32(0x3C9254)=0;
 defjam_fighter_cpu_released();defjam_fighter_cpu_released();
 assert(defjam_fighter_cpu_flags(0x1E477A,0x1000,512,0)==0x8000003F);
 assert(reservations==1&&registrations==1);defjam_fighter_cpu_released();
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-cpu-pool')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES + '\nextern uint32_t g_seh_ebp;\n'
        '#define MEM16(a) (*(uint16_t *)(memory+(a)))\n', encoding='utf-8')
    manual = (ROOT / 'src/recomp_manual.c').read_text(encoding='utf-8')
    start = manual.index('static void fighter_archive_allocate(void) {')
    bridge = manual[start:manual.index('\n}', start) + 2]
    driver = folder / 'driver.c'
    driver.write_text(DRIVER.replace('/*BRIDGE*/', bridge), encoding='utf-8')
    exe = folder / ('pool.exe' if os.name == 'nt' else 'pool')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_cpu_pool.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS', '/I' + str(folder),
                '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)] if os.name == 'nt' else
               [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(folder), '-I', str(ROOT / 'src'),
                *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.mark.parametrize('mode', ['good', 'inactive'])
def test_owned_routing_native_abi_and_pool_reuse(tool, mode):
    result = subprocess.run([tool, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode', ['reserve', 'occupied', 'budget', 'flags', 'null', 'escape', 'owner', 'leak', 'registry'])
def test_bad_memory_requests_and_incomplete_native_release_stop(tool, mode):
    result = subprocess.run([tool, mode], capture_output=True, text=True)
    assert result.returncode == 1 and 'CPU animation storage stopped:' in result.stderr, result.stdout + result.stderr
