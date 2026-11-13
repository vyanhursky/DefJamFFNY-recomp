"""Closing the window waits for a save in progress (review 2026-11-12, P5)."""
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
#include "save_activity.h"
#if defined(_WIN32)
#include <windows.h>
static DWORD WINAPI closer(LPVOID unused) { (void)unused; Sleep(150); save_activity_close(7); return 0; }
#else
#include <pthread.h>
#include <unistd.h>
static void *closer(void *unused) { (void)unused; usleep(150000); save_activity_close(7); return NULL; }
#endif
void host_request_close(void) {}
int main(int argc, char **argv) {
    assert(argc == 2);
    assert(!save_activity_busy() && save_activity_wait_idle(10));   /* nothing open: no wait */
    save_activity_write(7); save_activity_write(7); save_activity_write(9);
    assert(save_activity_busy());
    save_activity_close(9); save_activity_close(1234);                /* unrelated close: no effect */
    assert(save_activity_busy());
    if (!strcmp(argv[1], "timeout")) return save_activity_wait_idle(100) ? 1 : 0;
#if defined(_WIN32)
    HANDLE thread = CreateThread(NULL, 0, closer, NULL, 0, NULL);
#else
    pthread_t thread; pthread_create(&thread, NULL, closer, NULL);
#endif
    assert(save_activity_wait_idle(5000));                             /* returns once the game closes the file */
    assert(save_activity_exit_requested() && !save_activity_busy());
#if defined(_WIN32)
    WaitForSingleObject(thread, INFINITE);
#else
    pthread_join(thread, NULL);
#endif
    for (unsigned i = 0; i < 40; ++i) save_activity_write(100 + i);    /* more than the table holds */
    for (unsigned i = 0; i < 40; ++i) save_activity_close(100 + i);
    assert(!save_activity_busy());
    return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('native C compiler unavailable')
    folder = tmp_path_factory.mktemp('save-activity')
    driver = folder / 'driver.c'
    driver.write_text(DRIVER)
    exe = folder / ('activity.exe' if os.name == 'nt' else 'activity')
    sources = [str(driver), str(ROOT / 'src/hooks/save_activity.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/I' + str(ROOT / 'src/hooks'), *sources, '/Fe:' + str(exe)] if os.name == 'nt'
               else [cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra', '-Werror', '-pthread',
                     '-I', str(ROOT / 'src/hooks'), *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def test_close_waits_until_the_open_save_is_closed(tool):
    result = subprocess.run([str(tool), 'wait'], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'waited' in result.stderr


def test_close_gives_up_after_its_timeout(tool):
    result = subprocess.run([str(tool), 'timeout'], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'exiting anyway' in result.stderr
