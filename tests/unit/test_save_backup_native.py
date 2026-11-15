"""Rolling save backups: the last three, plus the first of each of the seven most recent days."""
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
extern "C" void pc_save_backup(void);
int main() { pc_save_backup(); return 0; }
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cxx = shutil.which('cl') if os.name == 'nt' else (shutil.which('c++') or shutil.which('g++') or shutil.which('clang++'))
    if not cxx:
        pytest.skip('native C++ compiler unavailable')
    folder = tmp_path_factory.mktemp('save-backup')
    driver = folder / 'driver.cpp'
    driver.write_text(DRIVER)
    exe = folder / ('backup.exe' if os.name == 'nt' else 'backup')
    sources = [str(driver), str(ROOT / 'src/hooks/save_backup.cpp')]
    command = ([cxx, '/nologo', '/std:c++17', '/EHsc', '/W4', '/WX', *sources, '/Fe:' + str(exe)] if os.name == 'nt'
               else [cxx, '-std=c++17', '-Wall', '-Wextra', '-Werror', *sources, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def data_root(tmp_path, content=b'profile v1'):
    data = tmp_path / 'data'
    profile = data / 'save/UserData/45410049/AAAABBBBCCCC'
    profile.mkdir(parents=True)
    (profile / 'VY1').write_bytes(content)
    (data / 'fighter-state').mkdir()
    (data / 'fighter-state/unlocks.ini').write_text('[fighter-unlocks]\nschema=1\n')
    return data


def run(tool, data):
    result = subprocess.run([str(tool)], env={**os.environ, 'DEFJAM_DATA': str(data)}, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return result.stderr


def test_backup_copies_saves_and_unlocks_and_skips_unchanged(tool, tmp_path):
    data = data_root(tmp_path)
    log = run(tool, data)
    backups = sorted((data / 'save-backups').iterdir())
    assert len(backups) == 1 and 'backed up' in log
    assert (backups[0] / 'UserData/45410049/AAAABBBBCCCC/VY1').read_bytes() == b'profile v1'
    assert (backups[0] / 'fighter-state/unlocks.ini').exists()
    assert 'unchanged' in run(tool, data)
    assert len(list((data / 'save-backups').iterdir())) == 1


def test_a_week_of_daily_backups_and_the_last_three_are_kept(tool, tmp_path):
    data = data_root(tmp_path, b'today')
    root = data / 'save-backups'
    old = []
    for day in range(1, 11):            # ten earlier days of play, three launches each
        for hour in (9, 13, 21):
            name = f'202601{day:02}-{hour:02}0000'
            (root / name / 'UserData').mkdir(parents=True)
            (root / name / 'UserData/marker').write_text(name)
            old.append(name)
    (root / '20260105-120000.partial').mkdir()  # an interrupted copy is not a backup
    run(tool, data)
    kept = sorted(path.name for path in root.iterdir() if not path.name.endswith('.partial'))
    today = time.strftime('%Y%m%d')
    new = [name for name in kept if name.startswith(today)]
    assert len(new) == 1
    # The first of each of the seven most recent days (today and six played days before it),
    # and the last three launches overall.
    first_of_day = [f'202601{day:02}-090000' for day in range(5, 11)]
    last_three = ['20260110-130000', '20260110-210000']
    assert kept == sorted(set(first_of_day + last_three + new))
    assert len(kept) == 9
