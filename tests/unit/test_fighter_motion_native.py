"""Core sidecar and native ABI contracts against invented guest data."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from test_fighter_motion import stream, table
from fighter_motion import MotionIndex
from fighter_motion_compile import MotionCoreTemplates, encode_core_bindings
from test_fighter_ui_native import TYPES

ROOT = Path(__file__).resolve().parents[2]
TYPES = TYPES.replace('#define MEM32', '#define MEM16(a) (*(uint16_t *)(memory+(a)))\n'
                      '#define MEMF(a) (*(float *)(memory+(a)))\n#define MEM32')
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_motion.h"
unsigned char memory[0xC00000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top, enabled=1;
static uint32_t parameters_calls, move_calls, scale_calls, log_calls;
static uint32_t decoded_source, logged_format;
static uint32_t audio_calls;
#define SOURCE 0x500000u
#define STACK 0xB00000u
#define OUTPUT 0x10000u
#define CONTEXT 0x14000u
int defjam_fighter_research_active(void) { return enabled; }
static void entry(void) {
    g_esp=STACK; g_eax=101; g_ecx=102; g_edx=103;
    g_ebx=104; g_esi=105; g_edi=106; g_ebp=107; g_fp_top=3;
}
static void preserved(void) {
    assert(g_esp==STACK+4 && g_ebx==104 && g_esi==105 && g_edi==106 && g_ebp==107 && g_fp_top==3);
}
void sub_001A3AD0(void) {
    uint32_t out=MEM32(g_esp+4);
    decoded_source=MEM32(g_esp+8);
    memset(XBOX_PTR(out),0x22,232); parameters_calls++;
    g_esp+=4; g_ebx=g_esi=g_edi=g_ebp=0xBAD;
}
void sub_001A3630(void) {
    uint32_t out=MEM32(g_esp+4);
    decoded_source=MEM32(g_esp+8);
    memset(XBOX_PTR(out),0,64); MEM16(out)=0xFFFD; MEM8(out+5)=1;
    move_calls++; g_esp+=4; g_ebx=g_esi=g_edi=g_ebp=0xBAD;
}
void sub_001C60D0(void) {
    assert(MEM32(g_esp+4)==OUTPUT); g_eax=77; g_esp+=4;
}
void sub_000444E0(void) {
    assert(MEM32(g_esp+4)<4 && MEM32(g_esp+8)==0x3F800000);
    scale_calls++; g_esp+=4;
}
void sub_00011520(void) {
    logged_format=MEM32(g_esp+4);
    assert(MEM32(g_esp+8)>=1 && MEM32(g_esp+8)<=4);
    log_calls++; g_esp+=4;
}
void sub_0003E170_gen(void) {
    uint32_t input=MEM32(g_esp+4);
    assert(input==STACK-0x90 && MEM32(input)==0xA5A5A5A5 && MEM8(input+0x81)==0xA5);
    for (uint32_t slot=0;slot<4;++slot) {
        uint32_t expected=(uint32_t[]){5,3,UINT32_MAX,5}[slot];
        assert(MEM32(input+0x20+slot*0x18)==expected);
    }
    audio_calls++; g_eax=0xA5000001; g_esp+=4; g_ebx=g_esi=g_edi=g_ebp=0xBAD;
}
static void environment(const char *key,const char *value) {
#ifdef _WIN32
    assert(!_putenv_s(key,value));
#else
    assert(!setenv(key,value,1));
#endif
}
int main(int argc,char **argv) {
    if (argc!=5) return 2;
    const char *mode=argv[4];
    environment("RECOMP_FIGHTER_MOTION",argv[1]);
    environment("RECOMP_FIGHTER_MOTION_BINDINGS",argv[2]);
    environment("RECOMP_FIGHTER_MOTION_SHA256",argv[3]);
    if (!strcmp(mode,"inactive")) enabled=0;
    int started=defjam_fighter_motion_start();
    if (!strcmp(mode,"reject") || !strcmp(mode,"inactive")) { assert(!started); return 0; }
    assert(started && !strcmp(defjam_fighter_motion_path(),argv[1]));
    if (!strcmp(mode,"selected")) {
        FILE *selected_file=fopen(argv[1],"rb"); assert(selected_file);
        assert(fread(XBOX_PTR(SOURCE),1,0x100000,selected_file)); fclose(selected_file);
        defjam_fighter_motion_register(SOURCE);
        MEM32(CONTEXT+0x2C)=141; MEM32(OUTPUT+0x28)=0;
        MEM32(0x3B85DC)=32; MEM32(0x3B85E0)=3; MEM32(0x3B85EC)=0x400000;
        MEM32(0x3B85F8)=4; MEM32(0x3B92E0+0x2C)=141;
        entry(); assert(defjam_fighter_motion_state(OUTPUT,CONTEXT,2)); preserved();
        assert(MEM32(OUTPUT+0xF54)==0 && MEM32(OUTPUT+0xFB4)==1 && decoded_source==0x400000);
        entry(); assert(defjam_fighter_motion_frame(1)); preserved(); assert(g_eax==0);
        return 0;
    }
    /* Audio initializes before the source generation exists. */
    memset(XBOX_PTR(0x2000),0xA5,0x84);
    for (uint32_t i=0;i<4;++i) MEM32(0x2020+i*0x18)=(uint32_t[]){257,3,UINT32_MAX,260}[i];
    if (!strcmp(mode,"audio-unknown")) {
        MEM32(0x2020)=1000; entry(); defjam_fighter_motion_audio(0x2000); return 3;
    }
    entry(); assert(defjam_fighter_motion_audio(0x2000)); preserved();
    assert(audio_calls==1 && g_eax==0xA5000001 && MEM32(0x2020)==257 && MEM32(0x2068)==260);
    MEM8(0x340540)=1; entry(); assert(!defjam_fighter_motion_audio(0) && g_esp==STACK);
    MEM8(0x340540)=0;
    for (uint32_t i=0;i<4;++i) MEM32(0x2020+i*0x18)=i;
    entry(); assert(!defjam_fighter_motion_audio(0x2000) && g_esp==STACK);
    FILE *file=fopen(argv[1],"rb"); assert(file);
    size_t got=fread(XBOX_PTR(SOURCE),1,0x100000,file); assert(got && !ferror(file)); fclose(file);
    if (!strcmp(mode,"changed")) MEM8(SOURCE+9)^=1;
    defjam_fighter_motion_register(SOURCE);
    MEM32(OUTPUT+0x28)=2; MEM32(OUTPUT+0x2C)=256;
    MEM32(CONTEXT+0x28)=1; MEM32(CONTEXT+0x2C)=257;
    /* Invented original registration values; decoder calls are observable. */
    MEM32(0x3B85DC)=MEM32(0x3B8614)=32;
    MEM32(0x3B85E0)=MEM32(0x3B8618)=200;
    MEM32(0x3B85EC)=0x400000; MEM32(0x3B8624)=0x410000; MEM32(0x3B85F8)=100000;
    for (uint32_t i=0;i<4;i++) { uint32_t a=0x3B92E0+i*0x12E8; MEM32(a+0x28)=i; MEM32(a+0x2C)=256+i; }
    assert(defjam_fighter_motion_bank(257)==5 && defjam_fighter_motion_bank(258)==5);
    assert(defjam_fighter_motion_bank(5)==5 && !defjam_fighter_motion_bank(0));
    if (!strcmp(mode,"expired")) {
        MEM32(0x2000)=SOURCE; defjam_fighter_motion_release(0x2000);
        defjam_fighter_motion_bank(257); return 3;
    }
    if (!strcmp(mode,"unknown")) { defjam_fighter_motion_bank(1000); return 3; }
    if (!strcmp(mode,"absent")) { entry(); defjam_fighter_motion_state(OUTPUT,CONTEXT,4); return 3; }
    if (!strcmp(mode,"outside")) { entry(); defjam_fighter_motion_present(CONTEXT,130); return 3; }
    entry(); MEM32(STACK+4)=OUTPUT;
    assert(defjam_fighter_motion_parameters(OUTPUT)); preserved();
    assert(parameters_calls==1 && MEM32(STACK+4)==0 && MEM32(OUTPUT+0xB34)==0x22222222);
    for (uint32_t i=0;i<7;i++) MEM32(0x3B9128+2*28+i*4)=i+1;
    entry(); MEM32(STACK+4)=OUTPUT; assert(defjam_fighter_motion_parameters(OUTPUT)); preserved();
    assert(MEM32(STACK+4)==28 && MEM32(OUTPUT+0xB34)==1 && MEM32(OUTPUT+0xB4C)==7);
    memset(XBOX_PTR(0x3B9128+56),0,28); MEM32(0x3B9128+56)=UINT32_MAX; MEM32(0x3B9128+60)=1;
    entry(); assert(defjam_fighter_motion_parameters(OUTPUT)); assert(!MEM32(STACK+4) && MEM32(OUTPUT+0xB34)==0x22222222);
    entry(); assert(!defjam_fighter_motion_present(0,0) && g_esp==STACK);
    assert(defjam_fighter_motion_present(CONTEXT,1) && g_eax==1); preserved();
    entry(); assert(defjam_fighter_motion_present(CONTEXT,4) && g_eax==0); preserved();
    for (unsigned i=0;i<4;i++) {
        uint32_t id=(uint32_t[]){1,31,38,10002}[i];
        entry(); MEM8(OUTPUT+0x926)=0xA6; MEM32(OUTPUT+0xBB8)=3;
        assert(defjam_fighter_motion_state(OUTPUT,CONTEXT,id)); preserved();
        assert(MEM32(OUTPUT+0xFAC)==OUTPUT && MEM32(OUTPUT+0xFB0)==CONTEXT);
        assert(MEM32(OUTPUT+0xF50)==id && MEM32(OUTPUT+0xF58)==77);
        assert(MEM32(OUTPUT+0x3C0)==0xFFFFFFFD && MEM8(OUTPUT+0xF68)==1);
        assert(!MEM8(OUTPUT+0xF69) && !MEM8(OUTPUT+0xF6A));
        assert(MEM8(OUTPUT+0x926)==(i==1 || i==2 ? 0xA7 : 0xA6));
        assert(decoded_source==(i==0 ? 0x400000u+2*32 : i==3 ? 0x410000u+2*32 : 0x410000u+145*32));
        assert(MEM32(OUTPUT+0xFB4)==(i==0 ? 2000u : 0u));
        assert(MEM32(OUTPUT+0xF54)==(i==0 ? 2u : UINT32_MAX));
    }
    assert(move_calls==4 && MEM32(CONTEXT+0x2C)==257 && MEM32(OUTPUT+0x2C)==256);
    for (uint32_t slot=0;slot<4;slot++) for (uint32_t local=0;local<1000;local++) {
        uint32_t a=0x3B92E0+slot*0x12E8, delta=local<10 ? local : local<20 ? local-10 : local-20;
        uint32_t ordinary=local<10 ? 100+delta : local<20 ? 200+delta : 300+delta;
        for (uint32_t correction=2;correction<=3;correction++) {
            MEM32(a+0x30)=0; entry(); assert(defjam_fighter_motion_frame(slot*1000+local)); preserved(); assert(g_eax==ordinary);
            MEM32(a+0x30)=0x41; MEM16(a+0xFA6)=500; MEM8(a+0x91A)=correction==3 ? 4 : 0;
            entry(); assert(defjam_fighter_motion_frame(slot*1000+local)); preserved(); assert(g_eax==(delta>=2 ? 500-correction+delta : ordinary));
        }
    }
    MEMF(0x2C9348)=1.05f; MEMF(0x289478)=1.0f; MEMF(0x2A2C38)=0.95f; MEMF(0x292378)=0.01f;
    MEMF(0x2F0088+4*4)=0.95f;
    entry(); assert(defjam_fighter_motion_scale()); preserved(); assert(scale_calls==4 && log_calls==4 && logged_format==0x2C92E8);
    MEM32(0x3B930C)=3; MEMF(0x2F0088+3*4)=1.05f;
    entry(); assert(defjam_fighter_motion_scale()); preserved(); assert(scale_calls==8 && logged_format==0x2C9308);
    MEM32(0x3B930C+0x12E8)=5; MEMF(0x2F0088+5*4)=1.0f;
    entry(); assert(defjam_fighter_motion_scale()); preserved(); assert(scale_calls==12 && logged_format==0x2C9324);
    MEM32(0x2000)=SOURCE; defjam_fighter_motion_release(0x2000); defjam_fighter_motion_register(SOURCE);
    assert(defjam_fighter_motion_bank(257)==5);
    enabled=0; entry(); assert(!defjam_fighter_motion_parameters(OUTPUT) && g_esp==STACK);
    puts("core ABI, 16000 frame cases, mixed scale and reload passed"); return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-motion-native')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES)
    driver = folder / 'driver.c'; driver.write_text(DRIVER)
    exe = folder / ('motion.exe' if os.name == 'nt' else 'motion')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_motion.c')]
    if os.name == 'nt':
        command = [cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                   '/I' + str(folder), '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
    else:
        command = [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra', '-Werror',
                   '-I', str(folder), '-I', str(ROOT / 'src'), *sources, '-lm', '-o', str(exe)]
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    original = bytearray(stream(table(moves=200) + table(moves=200), cores=141))
    start = MotionIndex(bytes(original)).core_spans[4] + 72
    for i in range(130):
        struct.pack_into('<3H', original, start + i * 6, 0xffff, 0, 0)
    for i, value, boundary, base in [(1, 0x8002, 0, 100), (2, 2, 10, 200), (3, 2, 20, 300),
                                      (31, 0x8002, 0, 0), (38, 0x8002, 0, 0)]:
        struct.pack_into('<3H', original, start + i * 6, value, boundary, base)
    original = bytes(original)
    data, report = MotionCoreTemplates(original, hashlib.sha256(original).hexdigest()).compose(
        {f'pack/core-{i:03}': 4 for i in range(119)})
    path = tmp_path / 'main.dat'; path.write_bytes(data)
    bindings = tmp_path / 'cores.bin'; bindings.write_bytes(encode_core_bindings(data, report))
    return path, bindings, report['sha256']


@pytest.mark.parametrize('mode', ['good', 'inactive'])
def test_owned_core_abi_branches_and_full_width_identity(tool, files, mode):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode,message', [('expired', 'expired'), ('unknown', 'unregistered'),
    ('absent', 'absent action'), ('outside', 'exceeds core'), ('changed', 'differs from validated'),
    ('audio-unknown', 'unknown audio template')])
def test_invalid_motion_access_fails_before_native_indexing(tool, files, mode, message):
    result = subprocess.run([tool, *files, mode], capture_output=True, text=True)
    assert result.returncode == 1 and message in result.stderr, result.stdout + result.stderr


@pytest.mark.parametrize('offset,value', [(4, 2), (8, 140), (12, 99999), (16, 0), (20, 1),
                                        (56, 140), (60, 0), (64, 0), (68, 1), (68, 142)])
def test_invalid_motion_receipt_is_rejected_atomically(tool, files, offset, value):
    path, bindings, digest = files
    data = bytearray(bindings.read_bytes()); struct.pack_into('<I', data, offset, value); bindings.write_bytes(data)
    result = subprocess.run([tool, path, bindings, digest, 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('partition', [0, 1])
@pytest.mark.parametrize('damage', ['move-stride', 'move-count', 'move-groups', 'group-population',
                                  'parameter-stride', 'parameter-count', 'padding',
                                  'name-count', 'name-offset', 'name-character', 'name-terminator'])
def test_native_start_rejects_malformed_shared_tables_even_with_matching_digest(tool, files, partition, damage):
    path, bindings, _ = files
    data = bytearray(path.read_bytes())
    chunks, cursor = [], 0
    for _ in range(6):
        size, = struct.unpack_from('<I', data, cursor + 4)
        chunks.append((cursor + 8, size)); cursor += 8 + size
    move, parameter, name = chunks[partition * 3:partition * 3 + 3]
    if damage.startswith('move-'):
        offset, value = {'move-stride': (0, 31), 'move-count': (4, 65536), 'move-groups': (8, 0)}[damage]
        struct.pack_into('<I', data, move[0] + offset, value)
    elif damage == 'group-population':
        struct.pack_into('<I', data, move[0] + 12, 201)
    elif damage.startswith('parameter-'):
        struct.pack_into('<I', data, parameter[0] + (4 if damage.endswith('count') else 0), 0)
    elif damage == 'padding':
        data[parameter[0] + parameter[1] - 1] = 1
    elif damage == 'name-count':
        struct.pack_into('<I', data, name[0], 0xffffffff)
    elif damage == 'name-offset':
        struct.pack_into('<H', data, name[0] + 4, 1)
    elif damage == 'name-character':
        data[name[0] + 6] = 31
    else:
        data[name[0] + name[1] - 1] = 65
    digest = hashlib.sha256(data).digest()
    receipt = bytearray(bindings.read_bytes()); receipt[24:56] = digest
    path.write_bytes(data); bindings.write_bytes(receipt)
    result = subprocess.run([tool, path, bindings, digest.hex(), 'reject'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
