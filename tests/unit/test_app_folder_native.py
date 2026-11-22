"""The one-folder Windows install's file operations, run for real in throwaway folders.

The fixture links the app's own app_os.cpp and has no game code or data.
"""
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='the one-folder install is Windows only')

DRIVER = r"""
#include "app_os.h"
#include <windows.h>
#include <string>
int wmain(int argc, wchar_t **argv)
{
    std::wstring mode = argc > 1 ? argv[1] : L"";
    std::string error;
    if (mode == L"remove" && argc == 5) {
        if (!app::os::remove_after_exit(app::os::program(), argv[2], argv[3], &error)) return 2;
        Sleep(_wtoi(argv[4]));                          // the app's window closing
        return 0;
    }
    return 10;
}
"""


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    compiler = shutil.which('cl')
    if not compiler:
        pytest.skip('native C++ compiler required')
    folder = tmp_path_factory.mktemp('app-folder-native')
    (folder / 'fixture.cpp').write_text(DRIVER)
    binary = folder / 'fixture.exe'
    built = subprocess.run([compiler, '/nologo', '/std:c++17', '/EHsc', '/utf-8', '/I' + str(ROOT / 'src/app'),
                            'fixture.cpp', str(ROOT / 'src/app/app_os.cpp'), '/Fe:' + str(binary),
                            'shell32.lib', 'ole32.lib', 'uuid.lib'], cwd=folder, capture_output=True)
    assert built.returncode == 0, (built.stdout + built.stderr).decode(errors='replace')
    return binary


def write(path, text='x'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def wait_until(condition, seconds=20):
    end = time.monotonic() + seconds
    while not condition() and time.monotonic() < end:
        time.sleep(0.2)
    return condition()


NAMES = {
    'spaces': 'Def Jam Recompiled',
    'accents': 'Café DJ',
    'outside-code-page': 'Łódź 格闘',
    'percent': 'Jam %DJPROBE% x',
    'percent-tokens': '100% %~dp0 %%i %1',
    'percent-loop-variable': 'Jam %i %n x',
    'exclamation': 'Jam !DJPROBE! x',
    'cmd-specials': "A&B (x86) ^c; d=e,f 'g'",
}


@pytest.mark.parametrize('name', NAMES.values(), ids=NAMES.keys())
@pytest.mark.parametrize('portable', [True, False], ids=['one-folder', 'older-home'])
@pytest.mark.parametrize('others', [True, False], ids=['other-files', 'only-the-app'])
def test_uninstall_removes_only_the_apps_files(native, tmp_path, name, portable, others):
    home = tmp_path / name
    program = home / 'DefJamRecompiled.exe'
    home.mkdir()
    shutil.copy2(native, program)
    write(home / 'DefJamRecompiled.exe.old')
    write(home / 'payload/deep/manifest.json')
    write(home / 'payload.old/manifest.json')
    write(home / 'payload.sha256')
    if portable:
        write(home / '.defjam-portable')
        (home / 'game').mkdir()
    kept = []
    if others:
        kept = [write(home / 'data/save/profile.sav'), write(home / 'my notes.txt'), write(home / 'game/mine.txt')]
    # Where the path would lead if cmd expanded it: none of this may be touched.
    decoy = tmp_path / name.replace('%DJPROBE%', 'OTHER').replace('!DJPROBE!', 'OTHER')
    if decoy != home:
        kept += [write(decoy / 'payload/precious.txt'), write(decoy / 'payload.sha256'),
                 write(decoy / 'DefJamRecompiled.exe')]
    link = write(tmp_path / 'Desk %DJPROBE% !top' / 'Def Jam Recompiled.lnk')
    user = tmp_path / ('user ' + name) / 'DefJamRecompiled'
    write(user / 'logs/setup.log')
    # The script's own folder is hostile too.
    temp = tmp_path / ('temp ' + name)
    temp.mkdir()
    env = dict(os.environ, DJPROBE='OTHER', TEMP=str(temp), TMP=str(temp))
    subprocess.run([str(program), 'remove', str(link), str(user), '300'], env=env, cwd=tmp_path, check=True, timeout=30)

    assert wait_until(lambda: not user.exists() and not list(temp.iterdir())), 'clean-up did not finish'
    for gone in ('DefJamRecompiled.exe', 'DefJamRecompiled.exe.old', 'payload', 'payload.old', 'payload.sha256',
                 '.defjam-portable'):
        assert not (home / gone).exists(), gone
    assert not link.exists()
    assert home.exists() == others
    for path in kept:
        assert path.read_text() == 'x', path


def test_uninstall_waits_for_the_app_to_exit(native, tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    program = home / 'DefJamRecompiled.exe'
    shutil.copy2(native, program)
    payload = write(home / 'payload/manifest.json')
    env = dict(os.environ, TEMP=str(tmp_path), TMP=str(tmp_path))
    with subprocess.Popen([str(program), 'remove', '', str(tmp_path / 'user'), '6000'], env=env, cwd=tmp_path) as app:
        time.sleep(4.5)
        assert app.poll() is None and program.exists() and payload.exists()
    assert wait_until(lambda: not home.exists())
