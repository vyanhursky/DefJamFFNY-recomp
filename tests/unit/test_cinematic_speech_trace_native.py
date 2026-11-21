"""Speech probes must preserve native effects, stay opt-in and bound recorder work."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_speech_probe_delegation_and_budget(tmp_path):
    compiler = shutil.which("cl") if os.name == "nt" else shutil.which("cc")
    if not compiler:
        pytest.skip("native C compiler unavailable")
    source = (ROOT / "src/recomp_manual.c").read_text(encoding='utf-8')
    probes = source.split("static int cinematic_speech_trace(void)", 1)[1]
    probes = "static int cinematic_speech_trace(void)" + probes.split("extern void sub_00135CB0_gen", 1)[0]
    prefix = r"""
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static unsigned char memory[0x400000];
#define MEM8(p) memory[(p)]
#define MEM32(p) (*(uint32_t *)(memory + (p)))
static uint32_t g_eax, g_esp;
static const char *option;
#define getenv(key) test_environment(key)
static const char *test_environment(const char *key) {
    assert(!strcmp(key, "RECOMP_CAF_SPEECH_TRACE")); return option;
}
static unsigned events, calls, dispatch_calls;
static char phases[4][32];
static void recorder_event(const char *kind, const char *fields) {
    assert(!strcmp(kind,"cinematic_speech"));
    if (events < 4) snprintf(phases[events],32,"%.31s",fields);
    events++;
}
"""
    driver = r"""
void sub_0001D1F0_gen(void) {
    dispatch_calls++; MEM32(0x331E90)=123; g_eax=0x11223301; g_esp+=4;
}
void sub_00034CF0_gen(void) {
    calls++; MEM8(0x3403BC)=1;
    uint32_t saved=g_esp;
    g_esp=0x1100; MEM32(g_esp)=0x34DAA;MEM32(g_esp+4)=0;
    sub_0001D1F0();assert(g_eax==0x11223301&&g_esp==0x1104);
    g_esp=saved+4;g_eax=0xAABBCCDD;
}
static void run(void) {
    g_esp=0x1000;g_eax=42; MEM32(g_esp)=0x3456;
    MEM32(g_esp+8)=0x1200;MEM32(0x1200)=0;
    sub_00034CF0();assert(g_esp==0x1004&&g_eax==0xAABBCCDD);
    assert(MEM8(0x3403BC)==1&&MEM32(0x331E90)==123);
}
int main(void) {
    option=NULL;run(); assert(events==0&&calls==1&&dispatch_calls==1);
    option="0";run();assert(events==0&&calls==2&&dispatch_calls==2);
    option="yes";run();assert(events==0&&calls==3&&dispatch_calls==3);
    option="1";run();assert(events==4&&calls==4&&dispatch_calls==4);
    assert(strstr(phases[0],"event_enter")&&strstr(phases[1],"dispatch_enter"));
    assert(strstr(phases[2],"dispatch_return")&&strstr(phases[3],"event_return"));
    for(unsigned i=0;i<70;i++) run();
    assert(events==128&&calls==74&&dispatch_calls==74);
    return 0;
}
"""
    path, output = tmp_path / "speech.c", tmp_path / "speech-probe"
    path.write_text(prefix + probes + driver)
    if os.name == "nt":
        command = [compiler, "/nologo", "/W4", "/WX", "/D_CRT_SECURE_NO_WARNINGS", str(path), "/Fe:" + str(output)]
    else:
        command = [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", str(path), "-o", str(output)]
    built = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    result = subprocess.run([output], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
