"""The music engine's song names (src/patches/song_store.c, issue #230) against synthetic guest memory.

At start-up the game copies every Song row's entity, title, artist and album into a table of 36
fixed 0xA0-byte entries at 0x33EC98; its own audio state follows at 0x340318. With more than 36
rows (the 32 retail songs, Holler and the player's songs) the copies ran over that state. Checked
here: 60 songs added with names as long as the fields allow leave everything past the table as it
was, the first 36 stay where the game keeps them, the lookup by entity finds every one, and the
random pick takes the game's rand() over all of them.
"""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]

DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/song_store.h"

unsigned char memory[0x1000000];
uint32_t g_eax, g_ecx, g_edx, g_ebx, g_esp, g_ebp, g_esi, g_edi;
int g_fp_top;
static uint32_t heap = 0x00900000u, allocs, rand_value = 1234567u, rand_calls;

/* The guest routines song_store.c calls (cdecl: the callee pops its return address). */
void sub_00029680(void) { uint32_t n = MEM32(g_esp + 4); g_eax = heap; heap += (n + 15) & ~15u; allocs++; g_esp += 4; }
void sub_00029740(void) { g_esp += 4; }
void sub_0002A770(void) { g_eax = rand_value; rand_calls++; g_esp += 4; }
void sub_0004EEC0(void) { g_esp += 12; }

/* What song_store.c reads from pc_songs.c. */
int pc_songs_retail_rows(void) { return 32; }
int pc_songs_rows(void) { return 32; }
const char *pc_songs_data_root(void) { return "."; }
const char *pc_songs_entity_for_rank(uint32_t r) { (void)r; return NULL; }
const char *pc_songs_id_for_rank(uint32_t r) { (void)r; return NULL; }
const char *pc_songs_label_for_rank(uint32_t r) { (void)r; return NULL; }

static uint32_t text_at = 0x00200000u;
static uint32_t put(const char *s)
{
    uint32_t at = text_at;
    memcpy(memory + at, s, strlen(s) + 1);
    text_at += (uint32_t)strlen(s) + 16;
    return at;
}

/* fn(args...) the way the game calls it: arguments pushed, a return address, the caller pops. */
static void call(void (*fn)(void), int argc, const uint32_t *args)
{
    uint32_t esp0 = g_esp;
    for (int i = argc - 1; i >= 0; i--) { g_esp -= 4; MEM32(g_esp) = args[i]; }
    g_esp -= 4;
    MEM32(g_esp) = 0x0003CEEFu;
    fn();
    assert(g_esp == esp0 - 4u * (uint32_t)argc);    /* `ret`: only the return address went */
    g_esp = esp0;
}

static uint32_t find(const char *entity)
{
    uint32_t args[1] = { put(entity) };
    g_eax = 0xDEADBEEFu;
    call(song_info_find, 1, args);
    return g_eax;
}

int main(int argc, char **argv)
{
    char entity[32], title[64], artist[64], album[64];
    int total = argc > 1 ? atoi(argv[1]) : 60;
    g_esp = 0x00100000u;
    memset(memory + 0x340318, 0xAB, 0x342000 - 0x340318);     /* the engine's own state after the table */
    MEM32(0x33EA20) = 0;
    for (int i = 0; i < total; i++) {
        uint32_t args[4];
        snprintf(entity, sizeof entity, i < 33 ? "song%02d" : "u%08x", i < 33 ? i : 0x1234500u + (unsigned)i);
        /* as long as the game's fields hold (47 characters), and one past them */
        snprintf(title, sizeof title, "Title %02d %s", i, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV");
        snprintf(artist, sizeof artist, "Artist %02d %s", i, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP");
        snprintf(album, sizeof album, "Album %02d %s", i, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRST");
        title[i % 2 ? 47 : 48] = 0; artist[47] = 0; album[47] = 0;
        args[0] = put(entity); args[1] = put(title); args[2] = put(artist); args[3] = put(album);
        call(song_info_add, 4, args);
    }
    printf("count %u allocs %u\n", MEM32(0x33EA20), allocs);
    int damaged = 0;
    for (uint32_t a = 0x340318; a < 0x342000; a++) damaged += MEM8(a) != 0xAB;
    printf("after-table bytes changed %d\n", damaged);
    int found = 0, fixed = 0, fields = 0;
    for (int i = 0; i < total; i++) {
        snprintf(entity, sizeof entity, i < 33 ? "song%02d" : "u%08x", i < 33 ? i : 0x1234500u + (unsigned)i);
        uint32_t e = find(entity);
        found += e != 0;
        if (i < 36) fixed += e == 0x33EC98u + (uint32_t)i * 0xA0u;
        if (e) {
            snprintf(title, sizeof title, "Title %02d %s", i, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV");
            title[47] = 0;
            fields += !strcmp((char *)memory + e, entity) && !strcmp((char *)memory + e + 0x10, title)
                      && strlen((char *)memory + e + 0x40) == 47 && strlen((char *)memory + e + 0x70) == 47;
        }
    }
    printf("found %d fixed %d fields %d missing %u\n", found, fixed, fields, find("nosuchsong"));

    /* The random pick (before sub_0003BE50): given no entry and more than 36, it is made here. */
    uint32_t arg[1] = { 0 };
    MEM8(0x340540) = 0;                             /* the engine is not busy */
    g_esp = 0x00100000u;
    g_esp -= 4; MEM32(g_esp) = 0; g_esp -= 4; MEM32(g_esp) = 0x0003C2F5u;
    song_info_before_random();
    uint32_t picked = MEM32(g_esp + 4);
    uint32_t expect = total > 36 ? 1234567u % (uint32_t)total : 0;
    printf("random %s rand_calls %u\n",
           total <= 36 ? (picked == 0 ? "left to the game" : "WRONG")
                       : (picked == find(expect < 33 ? (snprintf(entity, sizeof entity, "song%02u", expect), entity)
                                                    : (snprintf(entity, sizeof entity, "u%08x", 0x1234500u + expect), entity))
                          ? "same pick" : "WRONG"),
           rand_calls);
    MEM32(g_esp + 4) = 0x33EC98u;                   /* given an entry: left alone */
    song_info_before_random();
    printf("given %s\n", MEM32(g_esp + 4) == 0x33EC98u ? "kept" : "WRONG");
    MEM32(g_esp + 4) = 0; MEM8(0x340540) = 1;       /* the function returns before it picks */
    song_info_before_random();
    printf("busy %s rand_calls %u\n", MEM32(g_esp + 4) == 0 ? "untouched" : "WRONG", rand_calls);
    (void)arg;
    return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler:
        pytest.skip('native song names fixture needs a C compiler')
    folder = tmp_path_factory.mktemp('song-info-native')
    inc = folder / 'recomp/gen'
    inc.mkdir(parents=True)
    (inc / 'recomp_types.h').write_text(
        '#include <stdint.h>\n#include <stdlib.h>\nextern unsigned char memory[];\n'
        'extern uint32_t g_eax, g_ecx, g_edx, g_ebx, g_esp, g_ebp, g_esi, g_edi;\nextern int g_fp_top;\n'
        '#define MEM32(a) (*(uint32_t *)(memory + (uint32_t)(a)))\n'
        '#define MEM8(a) (*(uint8_t *)(memory + (uint32_t)(a)))\n')
    (folder / 'host.h').write_text('#define HOST_SEP "/"\n')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER)
    exe = folder / ('songinfo.exe' if os.name == 'nt' else 'songinfo')
    includes = [folder, ROOT / 'src', ROOT / 'src/hooks']
    sources = [driver, ROOT / 'src/patches/song_store.c']
    if os.name == 'nt':
        cmd = [compiler, '/nologo', '/O2', '/TC', *['/I' + str(p) for p in includes], *map(str, sources),
               '/Fe:' + str(exe)]
    else:
        cmd = [compiler, '-O2', *['-I' + str(p) for p in includes], *map(str, sources), '-o', str(exe)]
    result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def run(tool, total):
    result = subprocess.run([str(tool), str(total)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.splitlines()


def test_sixty_songs_leave_the_engine_state_alone(tool):
    out = run(tool, 60)
    assert out[0] == 'count 60 allocs 1'
    assert out[1] == 'after-table bytes changed 0'
    assert out[2] == 'found 60 fixed 36 fields 60 missing 0'
    assert out[3] == 'random same pick rand_calls 1'
    assert out[4] == 'given kept'
    assert out[5] == 'busy untouched rand_calls 1'


def test_the_games_own_songs_use_only_its_table(tool):
    out = run(tool, 33)                 # retail and Holler: no block, no pick of our own
    assert out[0] == 'count 33 allocs 0'
    assert out[1] == 'after-table bytes changed 0'
    assert out[2] == 'found 33 fixed 33 fields 33 missing 0'
    assert out[3] == 'random left to the game rand_calls 0'
