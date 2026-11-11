"""The shared fighter stop: log line, player-visible dialog, harness opt-out, exit status."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <stdio.h>
#include <string.h>
#include "patches/fighter_fatal.h"
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "quiet")) defjam_fighter_fatal_dialog(0);
    if (!strcmp(argv[1], "plain")) defjam_fighter_fatal(NULL, "no area");
    if (!strcmp(argv[1], "null-message")) defjam_fighter_fatal("CAF", NULL);
    defjam_fighter_fatal("CAF", "multi-outfit fighter was not confirmed");
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('Native compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-fatal')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER, encoding='utf-8')
    exe = folder / ('fatal.exe' if os.name == 'nt' else 'fatal')
    sources = [str(driver), str(ROOT / 'src/patches/fighter_fatal.c'), str(ROOT / 'tests/unit/native_stubs/host_fatal.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS', '/I' + str(ROOT / 'src'), *sources, '/Fe:' + str(exe)]
               if os.name == 'nt' else [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(ROOT / 'src'), *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def run(tool, mode):
    return subprocess.run([str(tool), mode], capture_output=True, text=True, timeout=10)


def test_stop_logs_shows_the_player_a_dialog_and_exits(tool):
    result = run(tool, 'dialog')
    assert result.returncode == 1
    assert '[FIGHTERS] CAF stopped: multi-outfit fighter was not confirmed' in result.stderr
    assert '[HOST_FATAL] Fighter Mod Support stopped the game.' in result.stderr
    assert 'multi-outfit fighter was not confirmed' in result.stderr.split('[HOST_FATAL]')[1]


def test_harness_runs_skip_the_dialog_but_still_exit_and_log(tool):
    result = run(tool, 'quiet')
    assert result.returncode == 1
    assert '[FIGHTERS] CAF stopped:' in result.stderr
    assert '[HOST_FATAL]' not in result.stderr


def test_area_is_optional_and_a_missing_message_is_survivable(tool):
    plain = run(tool, 'plain')
    assert plain.returncode == 1 and '[FIGHTERS] stopped: no area' in plain.stderr
    missing = run(tool, 'null-message')
    assert missing.returncode == 1 and 'unknown reason' in missing.stderr
