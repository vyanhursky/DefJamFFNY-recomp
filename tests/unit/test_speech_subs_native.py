"""Native checks for the voice-subtitle table (src/hooks/pc_speech_subs.c, PR #259).

The parser, the speech-archive triggers and the timing window are compiled from the real source with a
test clock, so no game or sleep is needed.
"""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]

DRIVER = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "recomp_settings.h"
#include "pc_speech_subs.h"

size_t pc_language_settings(RecompSetting *out, size_t max);

static uint64_t g_now = 100000;
uint64_t pc_speech_subs_test_now_ms(void) { return g_now; }

static void show(const char *label)
{
    char text[256];
    int on = pc_speech_subs_current(text, sizeof text);
    printf("%s %d [%s]\n", label, on, text);
}

static const char SCHL[8] = { 'S', 'C', 'H', 'l', 0, 0, 0, 0 };
static const char OTHER[8] = { 'S', 'C', 'C', 'l', 0, 0, 0, 0 };

int main(int argc, char **argv)
{
    RecompSetting settings[8];
    void *h2 = (void *)(uintptr_t)0x1002, *h3 = (void *)(uintptr_t)0x1003;
    uint64_t t0;
    size_t n = pc_language_settings(settings, 8);
    recomp_settings_register(settings, n);
    if (argc < 3) return 2;

    printf("sub_size_default %d\n", recomp_settings_get("language", "subtitle_size", 0));
    recomp_settings_set("language", "subtitle_size", 1);
    printf("sub_size_large %d\n", recomp_settings_get("language", "subtitle_size", 0));
    recomp_settings_set("language", "subtitle_size", 2);
    printf("sub_size_xl %d\n", recomp_settings_get("language", "subtitle_size", 0));
    recomp_settings_set("language", "subtitle_size", 0);

    pc_speech_subs_load(NULL);
    printf("null enabled %d\n", pc_speech_subs_enabled());
    show("null-show");
    pc_speech_subs_load(argv[2]);            /* folder without a table */
    printf("empty enabled %d\n", pc_speech_subs_enabled());

    pc_speech_subs_load(argv[1]);
    printf("loaded enabled %d\n", pc_speech_subs_enabled());
    show("idle");

    /* Reads only trigger on a tracked speech archive and an SCHl header. */
    xbox_speech_notify_open("D:\\AUDIO\\SPEECH2.VIV", h2);
    xbox_speech_notify_open("D:\\AUDIO\\MUSIC.VIV", h3);
    xbox_speech_notify_read(h2, 5000, OTHER, sizeof OTHER);
    show("not-schl");
    xbox_speech_notify_read(h3, 5000, SCHL, sizeof SCHL);
    show("untracked");
    xbox_speech_notify_read(h2, 5000, SCHL, 3);
    show("short");

    /* Two timed segments of one clip: 0.0-1.0 and 1.2-2.0 s, shown up to 250 ms past their end. */
    t0 = g_now;
    xbox_speech_notify_read(h2, 5000, SCHL, sizeof SCHL);
    g_now = t0 + 100;  show("seg@100");
    g_now = t0 + 200;  xbox_speech_notify_read(h2, 5000, SCHL, sizeof SCHL);   /* debounced re-read */
    g_now = t0 + 1100; show("seg@1100");
    g_now = t0 + 1300; show("seg@1300");
    g_now = t0 + 2300; show("seg@2300");
    g_now = t0 + 2400; show("seg@2400");

    /* A missing end time lasts 2.5 s. */
    t0 = g_now;
    xbox_speech_notify_read(h2, 7000, SCHL, sizeof SCHL);
    g_now = t0 + 2700; show("noend@2700");
    g_now = t0 + 2800; show("noend@2800");

    /* After close the handle no longer counts. */
    xbox_speech_notify_close(h2);
    g_now += 1000;
    xbox_speech_notify_read(h2, 5000, SCHL, sizeof SCHL);
    show("closed");

    /* Intro rows never trigger from an archive read, only when the cutscene plays them. */
    xbox_speech_notify_open("D:\\AUDIO\\SPEECH2.VIV", h2);
    xbox_speech_notify_read(h2, 9000, SCHL, sizeof SCHL);
    show("intro-read");
    xbox_speech_notify_path("D:\\SPEECH\\STREAMS\\INTRO\\000.STR");
    show("intro-registered");
    t0 = g_now;
    pc_speech_subs_play_intro(0);
    g_now = t0 + 50; show("intro-played");
    pc_speech_subs_reset();
    show("reset");

    /* Opening a loose stream by path triggers it; the key was normalised from INTRO\\ style. */
    t0 = g_now;
    xbox_speech_notify_path("d:/speech/streams/Shop/Greet01.mus");
    g_now = t0 + 10; show("path");

    /* voice_subtitles = off hides the line; auto shows it again. */
    recomp_settings_set("language", "voice_subtitles", 2);
    show("off");
    recomp_settings_set("language", "voice_subtitles", 0);
    show("auto");

    /* A clip left active for more than 20 s is dropped. */
    g_now = t0 + 20001; show("stale");
    return 0;
}
'''

TABLE = (
    '\ufeff# clip_key\tviv_id\toffset\tstart_sec\tend_sec\ttext\r\n'
    '\r\n'
    'career/voice01\t2\t5000\t0.00\t1.00\tPrimeira linha\r\n'
    'career/voice01\t2\t5000\t1.20\t2.00\tSegunda linha \r\n'
    'only\tfour\tcolumns\there\r\n'
    'career/voice02\t2\t7000\t0\t0\tSem fim\n'
    'INTRO\\000\t2\t9000\t0.00\t2.50\tVOCÊ VAI SER DESTRUÍDO!\n'
    '# a comment\n'
    'shop/greet01\t0\t0\t0.00\t1.50\tBem-vindo\n'
)


@pytest.fixture(scope='module')
def subs_tool(tmp_path_factory):
    if not (ROOT / 'tools/xboxrecomp/src/settings/recomp_settings.c').is_file():
        pytest.skip('native subtitle fixture needs the initialized toolkit submodule')
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler:
        pytest.skip('native subtitle fixture needs a C compiler')
    folder = tmp_path_factory.mktemp('speech-subs-native')
    if os.name == 'nt':
        host = '#include <windows.h>\n#define HOST_SEP "\\\\"\n'
    else:
        host = '#define HOST_SEP "/"\n'
    (folder / 'host.h').write_text(host)
    driver = folder / 'driver.c'
    driver.write_text(DRIVER, encoding='utf-8')
    exe = folder / ('subs.exe' if os.name == 'nt' else 'subs')
    includes = [folder, ROOT / 'src/hooks', ROOT / 'tools/xboxrecomp/src/settings']
    sources = [driver, ROOT / 'src/hooks/pc_speech_subs.c', ROOT / 'src/hooks/pc_language_settings.c',
               ROOT / 'tools/xboxrecomp/src/settings/recomp_settings.c']
    if os.name == 'nt':
        cmd = [compiler, '/nologo', '/O2', '/TC', '/W4', '/DPC_SPEECH_SUBS_TEST_CLOCK',
               *['/I' + str(p) for p in includes], *map(str, sources), '/Fe:' + str(exe)]
    else:
        cmd = [compiler, '-O2', '-Wall', '-DPC_SPEECH_SUBS_TEST_CLOCK', *['-I' + str(p) for p in includes],
               *map(str, sources), '-o', str(exe), '-pthread']
    result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def run(tool, tmp_path, table=TABLE, name='speech_subtitles.txt'):
    pack = tmp_path / 'pack'
    empty = tmp_path / 'empty'
    pack.mkdir()
    empty.mkdir()
    (pack / name).write_bytes(table.encode('utf-8'))
    env = {k: v for k, v in os.environ.items() if not k.startswith('RECOMP_')}
    env['RECOMP_SETTINGS'] = 'none'
    result = subprocess.run([str(tool), str(pack), str(empty)], env=env, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.decode('utf-8').splitlines()
    return {line.split(' ', 1)[0]: line.split(' ', 1)[1] for line in lines}, result.stderr.decode('utf-8', 'replace')


def test_no_table_is_inert(subs_tool, tmp_path):
    out, _ = run(subs_tool, tmp_path)
    assert out['null'] == 'enabled 0' and out['null-show'] == '0 []'
    assert out['empty'] == 'enabled 0'


def test_table_parsing_and_timing(subs_tool, tmp_path):
    out, err = run(subs_tool, tmp_path)
    # BOM, CRLF, blank lines, comments and the short row are skipped: five segments remain.
    assert 'loaded 5 voice subtitle segment(s)' in err
    assert out['loaded'] == 'enabled 1'
    assert out['idle'] == '0 []'
    assert out['not-schl'] == '0 []' and out['untracked'] == '0 []' and out['short'] == '0 []'
    assert out['seg@100'] == '1 [Primeira linha]'
    assert out['seg@1100'] == '1 [Primeira linha]'      # 250 ms grace after 1.0 s; debounce kept t0
    assert out['seg@1300'] == '1 [Segunda linha]'       # trailing space trimmed
    assert out['seg@2300'] == '0 []'
    assert out['seg@2400'] == '0 []'
    assert out['noend@2700'] == '1 [Sem fim]'           # no end time: 2.5 s (+250 ms)
    assert out['noend@2800'] == '0 []'
    assert out['closed'] == '0 []'


def test_intro_waits_for_the_cutscene(subs_tool, tmp_path):
    out, err = run(subs_tool, tmp_path)
    assert out['intro-read'] == '0 []'
    assert out['intro-registered'] == '0 []'
    assert 'registered match intro[0]: intro/000' in err
    assert out['intro-played'] == '1 [VOCÊ VAI SER DESTRUÍDO!]'
    assert out['reset'] == '0 []'


def test_path_trigger_setting_and_expiry(subs_tool, tmp_path):
    out, _ = run(subs_tool, tmp_path)
    assert out['path'] == '1 [Bem-vindo]'
    assert out['off'] == '0 []'
    assert out['auto'] == '1 [Bem-vindo]'
    assert out['stale'] == '0 []'


def test_tsv_name_is_also_read(subs_tool, tmp_path):
    out, err = run(subs_tool, tmp_path, name='speech_subtitles.tsv')
    assert out['loaded'] == 'enabled 1'
    assert 'speech_subtitles.tsv' in err


def test_subtitle_size_setting(subs_tool, tmp_path):
    out, _ = run(subs_tool, tmp_path)
    assert out['sub_size_default'] == '0'
    assert out['sub_size_large'] == '1'
    assert out['sub_size_xl'] == '2'
