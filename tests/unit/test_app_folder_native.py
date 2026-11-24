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
    if (mode == L"relink" && argc == 4) return 20 + (int)app::os::relink_game(argv[2], argv[3]);
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


UNNEEDED, RELINKED, FAILED = 20, 21, 22


def relink(native, link, target):
    return subprocess.run([str(native), 'relink', str(link), str(target)], timeout=30).returncode


def junction(link, target):
    link.parent.mkdir(parents=True, exist_ok=True)
    import _winapi
    _winapi.CreateJunction(str(target), str(link))


def installation(folder, dump):
    write(folder / 'data/extracted/default.xbe', dump)
    link = folder / 'game/versions/v/source/game'
    junction(link, folder / 'data/extracted')
    return link


def copy_installation(old, new):
    """The folder copied with its junction kept as one, still naming the old folder."""
    write(new / 'data/extracted/default.xbe', 'copy')
    link = new / 'game/versions/v/source/game'
    junction(link, old / 'data/extracted')
    return link


@pytest.mark.parametrize('name', ['copy', 'Café DJ', 'Łódź', 'Jam %PATH% !x'])
def test_a_copy_is_repointed_while_the_original_still_exists(native, tmp_path, name):
    original = installation(tmp_path / 'original', 'original')
    link = copy_installation(tmp_path / 'original', tmp_path / name)
    assert (link / 'default.xbe').read_text() == 'original'  # the reported fault
    assert relink(native, link, tmp_path / name / 'data/extracted') == RELINKED
    assert (link / 'default.xbe').read_text() == 'copy'
    assert os.path.samefile(link, tmp_path / name / 'data/extracted')
    assert (original / 'default.xbe').read_text() == 'original'
    assert not link.with_name('game.relink').exists()


@pytest.mark.parametrize('name', ['moved', 'Café DJ', 'Łódź'])
def test_a_move_is_repointed_when_the_original_is_gone(native, tmp_path, name):
    installation(tmp_path / 'original', 'the dump')
    (tmp_path / 'original').rename(tmp_path / name)
    link = tmp_path / name / 'game/versions/v/source/game'
    assert not (link / 'default.xbe').exists()
    assert relink(native, link, tmp_path / name / 'data/extracted') == RELINKED
    assert (link / 'default.xbe').read_text() == 'the dump'


def test_a_link_that_already_leads_here_is_left_alone(native, tmp_path):
    link = installation(tmp_path / 'here', 'x')
    made = os.lstat(link).st_ino
    assert relink(native, link, tmp_path / 'HERE/data/extracted') == UNNEEDED
    assert os.lstat(link).st_ino == made


@pytest.mark.parametrize('files', [[], ['default.xbe'], ['mine.txt']], ids=['empty', 'a-dump', 'other-files'])
def test_a_real_folder_is_never_replaced(native, tmp_path, files):
    write(tmp_path / 'data/extracted/default.xbe')
    link = tmp_path / 'source/game'
    link.mkdir(parents=True)
    for name in files:
        write(link / name, 'real')
    assert relink(native, link, tmp_path / 'data/extracted') == UNNEEDED
    assert not os.path.isjunction(link) and sorted(p.name for p in link.iterdir()) == files


def test_a_link_stays_when_this_folder_has_no_dump(native, tmp_path):
    installation(tmp_path / 'original', 'original')
    link = tmp_path / 'copy/source/game'
    junction(link, tmp_path / 'original/data/extracted')
    (tmp_path / 'copy/data/extracted').mkdir(parents=True)
    assert relink(native, link, tmp_path / 'copy/data/extracted') == UNNEEDED
    assert (link / 'default.xbe').read_text() == 'original'


def test_a_link_stays_when_its_replacement_cannot_be_made(native, tmp_path):
    installation(tmp_path / 'original', 'original')
    link = copy_installation(tmp_path / 'original', tmp_path / 'copy')
    write(link.with_name('game.relink') / 'in the way')
    assert relink(native, link, tmp_path / 'copy/data/extracted') == FAILED
    assert (link / 'default.xbe').read_text() == 'original'
