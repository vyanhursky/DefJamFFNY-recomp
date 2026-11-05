"""Native core-to-bank map, separate namespaces and immutable receipt checks."""
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_ui_native import TYPES
from test_fighter_ai import source, profile
from fighter_ai import encode_ai_bindings

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "patches/fighter_ai.h"
unsigned char memory[0x400000];
static int enabled=1;
int defjam_fighter_research_active(void) {return enabled;}
static void environment(const char *key,const char *value) {
#ifdef _WIN32
 assert(!_putenv_s(key,value));
#else
 assert(!setenv(key,value,1));
#endif
}
int main(int argc,char **argv) {
 assert(argc==5);
 environment("RECOMP_FIGHTER_AI",argv[1]);
 environment("RECOMP_FIGHTER_AI_BINDINGS",argv[2]);
 environment("RECOMP_FIGHTER_AI_SHA256",argv[3]);
 if(!strcmp(argv[4],"inactive"))enabled=0;
 int ok=defjam_fighter_ai_start();
 if(strcmp(argv[4],"good")){assert(!ok);return 0;}
 assert(ok&&!strcmp(defjam_fighter_ai_path(),argv[1]));
 memset(memory,0xCD,sizeof(memory));
 uint32_t config=0x1000,self=0x2000;
 const uint32_t cores[]={256,257,1000,4};
 memcpy(memory+0x3B90B8,cores,sizeof(cores));
 memset(memory+config+0x24,'x',128);
 defjam_fighter_ai_bind(config);
 for(unsigned i=0;i<3;i++) {
  assert(!memcmp(memory+config+0x24+i*32,"fma",3));
  assert(!memory[config+0x24+i*32+27]);
 }
 assert(!memcmp(memory+config+0x24,memory+config+0x64,32));
 assert(memcmp(memory+config+0x24,memory+config+0x44,32));
 assert(memory[config+0x84]=='x' && memory[config+0xA4]==0xCD);
 assert(memory[config+0x23]==0xCD && memory[config+0xC4]==0xCD);
 defjam_fighter_ai_loaded(self,config);
 enabled=0;memset(memory+config+0x24,'y',128);
 defjam_fighter_ai_bind(config);assert(memory[config+0x24]=='y');
 enabled=1;MEM32(0x3B90B8)=0xffffffffu;MEM32(0x3B90BC)=259;
 MEM32(0x3B90C0)=16384;MEM32(0x3B90C4)=256;MEM8(config+0x84)=0;
 defjam_fighter_ai_bind(config);
 assert(memory[config+0x24]=='y' && memory[config+0x44]=='y' && memory[config+0x64]=='y');
 assert(!memory[config+0x84]);
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-ai-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER, encoding='utf-8')
    exe = folder / ('ai.exe' if os.name == 'nt' else 'ai')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_ai.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
               if os.name == 'nt' else [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra',
                    '-Werror', '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    _, compiler = source()
    data, report = compiler.compose({'alpha/motion': profile(), 'beta/motion': profile()})
    path, table = tmp_path / 'ai.viv', tmp_path / 'bindings.bin'
    path.write_bytes(data)
    table.write_bytes(encode_ai_bindings(data, report, {256: 'alpha/motion', 257: 'beta/motion', 1000: 'alpha/motion'}))
    return path, table, report['sha256']


@pytest.mark.parametrize('mode', ['good', 'inactive'])
def test_native_bank_mapping_retains_full_core_and_independent_resource_ids(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('offset,value', [(0, 0), (4, 2), (8, 0), (8, 16384), (12, 0),
                                        (48, 140), (48, 16384), (84, 256), (52, 0), (52, 0x2f)])
def test_invalid_ai_receipt_never_activates(tool, files, offset, value):
    path, table, digest = files
    data = bytearray(table.read_bytes()); struct.pack_into('<I', data, offset, value)
    table.write_bytes(data)
    result = subprocess.run([tool, path, table, digest, 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
