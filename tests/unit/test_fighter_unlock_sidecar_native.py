"""The game's own custom-unlock sidecar: read, keep unknown names, write atomically.

Compiles the real functions from src/patches/fighter_runtime.c against stub
bindings. Saves stay in save/; this file is the only place custom unlocks go.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
METADATA = 0x00800000

FUNCTIONS = ['open_utf8', 'read_small_file', 'sidecar_name', 'load_identities', 'identity_name', 'identity_handle',
             'sidecar_path', 'set_aside', 'load_sidecar', 'open_write_utf8', 'make_state_dir', 'write_sidecar',
             'remember_custom']

DRIVER = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#if defined(_WIN32)
#include <windows.h>
#include <io.h>
#include <direct.h>
#else
#include <unistd.h>
#include <sys/stat.h>
#endif
#define FIGHTER_BINDINGS_MAX_COUNT 64u
#define FIGHTER_UNLOCK_METADATA 0x00800000u
typedef enum { FIGHTER_BINDING_STABLE, FIGHTER_BINDING_NATIVE, FIGHTER_BINDING_SELECTION } FighterBindingKey;
typedef struct { const uint8_t *bytes; uint32_t count; } FighterBindings;
typedef struct { uint32_t stable_handle, flags; } FighterBinding;
static FighterBindings s_bindings;
static char s_state_dir[2048];
static uint32_t s_custom_count;
static int s_custom_dirty;
static uint8_t *s_identity_bytes;
static uint32_t s_identity_count;
static uint32_t s_identity_handles[FIGHTER_BINDINGS_MAX_COUNT];
static const char *s_identity_names[FIGHTER_BINDINGS_MAX_COUNT];
static char *s_unknown_lines;
static size_t s_unknown_size;
static uint32_t s_custom_keys[FIGHTER_BINDINGS_MAX_COUNT], s_custom_metadata[FIGHTER_BINDINGS_MAX_COUNT];
static int remember_custom(uint32_t mark);
static FILE *open_write_utf8(const char *path);
static int write_sidecar(void);
/* Custom fighters are 0x01000100..0x010001FF; anything else is retail. */
static int fighter_bindings_find(const FighterBindings *bindings, FighterBindingKey domain, uint32_t key, FighterBinding *out) {
    (void)bindings; assert(domain == FIGHTER_BINDING_STABLE);
    out->stable_handle = key; out->flags = (key & 0xFFFFFF00u) == 0x01000100u;
    return 1;
}
/* The bindings hold three custom fighters (mode "unnamed" adds a fourth with no name). */
static uint32_t s_custom_bindings[4] = {0x01000101u, 0x01000102u, 0x01000103u, 0x01000104u};
static int fighter_bindings_at(const FighterBindings *bindings, uint32_t index, FighterBinding *out) {
    (void)bindings; out->stable_handle = s_custom_bindings[index]; out->flags = 1; return 1;
}
@FUNCTIONS@
int main(int argc, char **argv) {
    const char *mode = argv[3];
    assert(argc == 4);
    strcpy(s_state_dir, argv[2]);
    s_bindings.count = !strcmp(mode, "unnamed") ? 4 : 3;
    if (!load_identities(argv[1])) return 3;
    if (!load_sidecar()) return 4;
    printf("loaded=%u dirty=%d\n", s_custom_count, s_custom_dirty);
    for (uint32_t i = 0; i < s_custom_count; ++i) printf("mark=%08X %u\n", s_custom_keys[i], s_custom_metadata[i] ? 1 : 0);
    if (!strcmp(mode, "unlock")) {
        assert(remember_custom(0x01000102u | FIGHTER_UNLOCK_METADATA));
        assert(s_custom_dirty);
        assert(!remember_custom(0x00000005u)); /* retail marks never go to the sidecar */
    }
    if (!strcmp(mode, "unlock") || !strcmp(mode, "rewrite")) {
        if (!write_sidecar()) return 5;
        assert(!s_custom_dirty);
    }
    return 0;
}
'''


def extract(text, name):
    match = re.search(r'^(?:static )?[A-Za-z_][\w ]*[\s\*]' + re.escape(name) + r'\([^)]*\)\s*\{', text, re.M)
    assert match, name
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]


@pytest.fixture(scope='module')
def sidecar_exe(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('Native compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-sidecar')
    runtime = (ROOT / 'src/patches/fighter_runtime.c').read_text(encoding='utf-8')
    limit = re.search(r'#define FIGHTER_SIDECAR_MAX .*', runtime).group(0)
    functions = limit + '\n' + '\n'.join(extract(runtime, name) for name in FUNCTIONS)
    source = folder / 'sidecar.c'
    source.write_text(DRIVER.replace('@FUNCTIONS@', functions), encoding='utf-8')
    exe = folder / ('sidecar.exe' if os.name == 'nt' else 'sidecar')
    command = ([cc, '/nologo', '/W4', '/WX', '/wd4996', '/D_CRT_SECURE_NO_WARNINGS', str(source), '/Fe:' + str(exe)] if os.name == 'nt'
               else [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def setup_files(tmp_path, sidecar=None):
    identities = tmp_path / 'fighter-identities.txt'
    identities.write_text('# stable-handle pack/fighter\n01000101 alpha/one\n01000102 alpha/two\n01000103 beta/three\n')
    state = tmp_path / 'fighter-state'
    if sidecar is not None:
        state.mkdir()
        (state / 'unlocks.ini').write_text(sidecar, newline='\n')
    return identities, state


def run(exe, identities, state, mode):
    return subprocess.run([str(exe), str(identities), str(state), mode], capture_output=True, text=True, timeout=10)


def test_missing_sidecar_means_no_custom_unlocks_and_first_unlock_creates_it(sidecar_exe, tmp_path):
    identities, state = setup_files(tmp_path)
    result = run(sidecar_exe, identities, state, 'unlock')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == 'loaded=0 dirty=0'
    text = (state / 'unlocks.ini').read_text()
    assert '[fighter-unlocks]\nschema=1\nalpha/two=1\n' in text
    assert not (state / 'unlocks.ini.tmp').exists()


def test_names_of_packs_not_installed_are_kept_on_rewrite(sidecar_exe, tmp_path):
    identities, state = setup_files(tmp_path, '# comment\n[fighter-unlocks]\nschema=1\nalpha/one=0\ngone/fighter=1\nbeta/three=1\n')
    result = run(sidecar_exe, identities, state, 'unlock')
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == 'loaded=2 dirty=0'
    assert lines[1:] == ['mark=01000101 0', 'mark=01000103 1']
    text = (state / 'unlocks.ini').read_text()
    body = text.split('schema=1\n', 1)[1].splitlines()
    assert body == ['alpha/one=0', 'beta/three=1', 'alpha/two=1', 'gone/fighter=1']
    # Reading what the game wrote gives the same set back.
    again = run(sidecar_exe, identities, state, 'read')
    assert again.returncode == 0 and again.stdout.splitlines()[0] == 'loaded=3 dirty=0'
    assert not list(state.glob('unlocks.ini.bad-*'))


@pytest.mark.parametrize('text,loaded', [
    ('alpha/one=1\n', 0),                                                  # outside the section
    ('[fighter-unlocks]\nalpha/one=2\nbeta/three=1\n', 1),               # bad value; the good line stays
    ('[fighter-unlocks]\nno-slash=1\nalpha/one=0\n', 1),
    ('[fighter-unlocks]\nalpha/one\nbeta/three=0\n', 1),
])
def test_a_damaged_sidecar_keeps_its_good_lines_and_is_set_aside(sidecar_exe, tmp_path, text, loaded):
    """Review feedback F1: a damaged file must never turn fighter packs off for good."""
    identities, state = setup_files(tmp_path, text)
    result = run(sidecar_exe, identities, state, 'read')
    assert result.returncode == 0, result.stderr
    # The clean file is written at once, so the good lines survive a session with no save.
    assert result.stdout.splitlines()[0] == f'loaded={loaded} dirty=0'
    aside = list(state.glob('unlocks.ini.bad-*'))
    assert len(aside) == 1 and aside[0].read_text() == text
    assert 'could not be read' in (state / 'notice.txt').read_text()
    clean = run(sidecar_exe, identities, state, 'read')
    assert clean.returncode == 0 and clean.stdout.splitlines()[0] == f'loaded={loaded} dirty=0'


def test_a_sidecar_from_a_newer_version_is_set_aside_not_read(sidecar_exe, tmp_path):
    identities, state = setup_files(tmp_path, '[fighter-unlocks]\nschema=2\nalpha/one=1\n')
    result = run(sidecar_exe, identities, state, 'read')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == 'loaded=0 dirty=0'
    assert 'newer version' in (state / 'notice.txt').read_text()
    assert len(list(state.glob('unlocks.ini.bad-*'))) == 1


def test_identity_names_must_match_the_bindings(sidecar_exe, tmp_path):
    identities, state = setup_files(tmp_path)
    identities.write_text('00000005 retail/not-custom\n')
    assert run(sidecar_exe, identities, state, 'read').returncode == 3
    identities.write_text('0100010 alpha/short\n')
    assert run(sidecar_exe, identities, state, 'read').returncode == 3
    # Review feedback S3: a custom fighter with no name could never have its unlock recorded.
    identities, state = setup_files(tmp_path)
    result = run(sidecar_exe, identities, state, 'unnamed')
    assert result.returncode == 3 and 'has no name' in result.stderr
