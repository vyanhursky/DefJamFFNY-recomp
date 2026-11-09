"""Pause Quit must thaw selection only after native/adapter destruction returns."""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def definition(text, name):
    match = re.search(r'(?:static )?(?:void|uint32_t) ' + re.escape(name) + r'\([^)]*\)\s*\{', text)
    assert match, name
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]


DRIVER = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fighter_window.h"
static FighterWindow s_window;
static int s_immutable_reuse, stage, validates, expected_frozen, fail_pool;
static uint8_t live;
uint32_t g_ecx = 0x349760;
static void still_owned(void) {
    assert(s_window.frozen == expected_frozen);
    if (expected_frozen) assert(!fighter_window_clear(&s_window, UINT32_MAX));
}
void defjam_fighter_motion_release(uint32_t owner) {
    assert(owner == g_ecx && stage == 0); still_owned(); stage = 1;
}
void defjam_fighter_cinematic_cache_release(uint32_t owner) {
    assert(owner == g_ecx && stage == 1); still_owned(); stage = 2;
}
void sub_00089310_gen(void) { assert(stage == 2); still_owned(); stage = 3; }
void defjam_fighter_finishers_release(uint32_t owner) {
    assert(owner == g_ecx && stage == 3); still_owned(); stage = 4;
}
void defjam_fighter_film_release(void) { assert(stage == 4); still_owned(); stage = 5; }
void defjam_fighter_cpu_released(void) {
    assert(stage == 5); still_owned(); stage = 6;
    if (fail_pool) exit(23);
}
static void validate_immutable_banks(void) { assert(stage == 6); still_owned(); ++validates; }
static void fighter_stop(const char *message) { (void)message; abort(); }
static unsigned xbox_HeapLiveBytes(void) { return 10; }
static unsigned xbox_ContiguousLiveBytes(void) { return 20; }
@DEFINITIONS@
int main(int argc, char **argv) {
    assert(argc == 2);
    s_window.bytes = strcmp(argv[1], "no-window") ? &live : NULL;
    s_immutable_reuse = strcmp(argv[1], "immutable-off") != 0;
    expected_frozen = strcmp(argv[1], "not-frozen") != 0;
    fail_pool = !strcmp(argv[1], "pool-live");
    for (unsigned cycle = 0; cycle < 2; ++cycle) {
        s_window.frozen = expected_frozen;
        s_window.selected[0] = cycle + 1;
        s_window.selected[1] = cycle + 3;
        stage = validates = 0;
        sub_00089310();
        assert(stage == 6);
        assert(s_window.selected[0] == cycle + 1 && s_window.selected[1] == cycle + 3);
        if (s_window.bytes && s_immutable_reuse && expected_frozen) {
            assert(validates == 1 && !s_window.frozen);
            assert(fighter_window_clear(&s_window, UINT32_MAX));
            assert(!s_window.selected[0] && !s_window.selected[1]);
        } else assert(!validates && s_window.frozen == expected_frozen);
    }
    return 0;
}
'''


@pytest.fixture(scope='module')
def teardown_probe(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('Native C compiler unavailable')
    manual = (ROOT / 'src/recomp_manual.c').read_text(encoding='utf-8')
    runtime = (ROOT / 'src/patches/fighter_runtime.c').read_text(encoding='utf-8')
    definitions = '\n'.join([definition(runtime, 'finish_selection'),
                              definition(runtime, 'defjam_fighter_match_unloaded'),
                              definition(manual, 'sub_00089310')])
    folder = tmp_path_factory.mktemp('fighter-match-teardown')
    source = folder / 'probe.c'
    source.write_text(DRIVER.replace('@DEFINITIONS@', definitions), encoding='utf-8')
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    inputs = [str(source), str(ROOT / 'src/hooks/fighter_window.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS',
                '/I' + str(ROOT / 'src/hooks'), *inputs, '/Fe' + str(exe)] if os.name == 'nt'
               else [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(ROOT / 'src/hooks'),
                     *inputs, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.mark.parametrize('mode', ['active', 'immutable-off', 'no-window', 'not-frozen', 'pool-live'])
def test_pause_quit_keeps_ownership_until_verified_destruction(teardown_probe, mode):
    result = subprocess.run([str(teardown_probe), mode], capture_output=True, text=True, timeout=10)
    assert result.returncode == (23 if mode == 'pool-live' else 0), result.stdout + result.stderr
