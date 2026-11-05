"""Native core-to-bank map, separate namespaces and immutable receipt checks."""
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_ui_native import TYPES
from test_fighter_animation_archive import baseline, resource
from fighter_animation_archive import encode_animation_bindings

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "patches/fighter_animation.h"
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
 environment("RECOMP_FIGHTER_ANIMATIONS",argv[1]);
 environment("RECOMP_FIGHTER_ANIMATION_BINDINGS",argv[2]);
 environment("RECOMP_FIGHTER_ANIMATIONS_SHA256",argv[3]);
 if(!strcmp(argv[4],"inactive"))enabled=0;
 int ok=defjam_fighter_animation_start();
 if(strcmp(argv[4],"good")){assert(!ok);return 0;}
 assert(ok&&!strcmp(defjam_fighter_animation_path(),argv[1]));
 assert(defjam_fighter_animation_bank(257,5)==1001);
 assert(defjam_fighter_animation_bank(258,6)==1002);
 assert(defjam_fighter_animation_bank(1001,7)==1001);
 assert(defjam_fighter_animation_bank(5,5)==5);
 assert(defjam_fighter_animation_bank(0,0)==0);
 assert(defjam_fighter_animation_bank(259,8)==8);
 assert(defjam_fighter_animation_bank(0xffffffffu,9)==9);
 enabled=0;assert(defjam_fighter_animation_bank(257,5)==5);
 return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-animation-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER, encoding='utf-8')
    exe = folder / ('animation.exe' if os.name == 'nt' else 'animation')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_animation.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
               if os.name == 'nt' else [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra',
                    '-Werror', '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    _, compiler = baseline()
    data, report = compiler.compose({'alpha/motion': resource(), 'beta/motion': resource()})
    path, table = tmp_path / 'animation.viv', tmp_path / 'bindings.bin'
    path.write_bytes(data)
    table.write_bytes(encode_animation_bindings(data, report, {256: 'alpha/motion', 257: 'beta/motion', 1000: 'alpha/motion'}))
    return path, table, report['sha256']


@pytest.mark.parametrize('mode', ['good', 'inactive'])
def test_native_bank_mapping_retains_full_core_and_independent_resource_ids(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('offset,value', [(0, 0), (4, 2), (8, 0), (8, 16384), (12, 0),
                                        (48, 140), (48, 16384), (56, 256), (52, 999), (52, 100000)])
def test_invalid_animation_receipt_never_activates(tool, files, offset, value):
    path, table, digest = files
    data = bytearray(table.read_bytes()); struct.pack_into('<I', data, offset, value)
    table.write_bytes(data)
    result = subprocess.run([tool, path, table, digest, 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
