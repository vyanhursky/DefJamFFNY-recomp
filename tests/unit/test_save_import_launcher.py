"""Launcher protocol, real native helper argv, locks and transactional save imports.

Invented profiles only. No downloaded saves or game bytes are committed.
"""
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys
import time
import zipfile

import pytest

from test_save_import_ps2 import story, mc02, psu, native_options
from test_save_import import make_zip

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import save_import as service


def source(path):
    path.write_bytes(psu(mc02(story())))
    return path


def test_one_entry_point_handles_ps2_xbox_and_mixed_folder(tmp_path):
    folder = tmp_path / 'mixed'
    folder.mkdir()
    source(folder / 'ps2.psu')
    make_zip(folder / 'xbox.zip', extra=False)
    save = tmp_path / 'data/save'
    assert service.main([str(folder), '--save-dir', str(save)]) == 0
    assert sorted(p.name for p in save.glob('UserData/45410049/*/*') if p.name != 'SaveMeta.xbx') == ['DEMO', 'JAYFNG', 'saveimage.xbx']


def test_xbox_unreferenced_old_file_does_not_block_named_profile(tmp_path):
    from test_save_import import profile_file, CONSOLE_KEY
    src = tmp_path / 'input.zip'
    make_zip(src, extra=False)
    with zipfile.ZipFile(src, 'a') as z:
        z.writestr('UDATA/45410049/11540F4914CA/OLDNAME', profile_file(CONSOLE_KEY))
    candidates, _ = service.read_candidates([src])
    assert [c.name for c in candidates] == ['JAYFNG']


def test_running_game_lock_refuses_import_without_changing_saves(tmp_path):
    src = source(tmp_path / 'input.psu')
    save = tmp_path / 'data/save'
    with service.runtime_lock(save):
        result = subprocess.run([sys.executable, '-B', '-I', str(ROOT / 'scripts/save-import.py'),
                                 str(src), '--save-dir', str(save)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 2 and 'Close the game' in result.stderr
    assert not save.exists()
    assert service.main([str(src), '--save-dir', str(save)]) == 0


def test_preview_report_and_changed_destination_refused(tmp_path):
    src = source(tmp_path / 'save.psu')
    save = tmp_path / 'data/save'
    report = tmp_path / 'result.ini'
    assert service.main([str(src), '--save-dir', str(save), '--dry-run', '--report', str(report)]) == 0
    assert not save.exists()
    text = report.read_text()
    assert 'platform=PS2' in text and 'action=Import' in text
    token = next(line[6:] for line in text.splitlines() if line.startswith('token='))
    target = save / 'UserData/45410049' / service.xbox.folder_name('DEMO')
    target.mkdir(parents=True)
    (target / 'DEMO').write_bytes(b'changed since preview')
    assert service.main([str(src), '--save-dir', str(save), '--expect', token, '--report', str(report)]) == 2
    assert 'changed' in report.read_text() and 'status=error' in report.read_text()
    assert (target / 'DEMO').read_bytes() == b'changed since preview'


def test_changed_source_and_options_invalidate_confirmation(tmp_path):
    src = source(tmp_path / 'save.psu')
    save = tmp_path / 'data/save'
    plan = service.make_plan([src], save)
    assert service.main([str(src), '--save-dir', str(save), '--force', '--expect', plan.token]) == 2
    raw = bytearray(story()); raw[20] ^= 1
    src.write_bytes(psu(mc02(raw)))
    assert service.main([str(src), '--save-dir', str(save), '--expect', plan.token]) == 2
    assert not save.exists()


def test_batch_publish_failure_restores_all_profiles(tmp_path, monkeypatch):
    one = source(tmp_path / 'one.psu')
    two = tmp_path / 'two.psu'; two.write_bytes(psu(mc02(story('SECOND'))))
    save = tmp_path / 'data/save'
    first = service.make_plan([one, two], save)
    service.apply_plan(first)
    paths = [target for _, target, _ in first.writes]
    for target in paths:
        (target / target.name).write_bytes(b'kept metadata fixture')
    before = {p.relative_to(save): p.read_bytes() for p in save.rglob('*') if p.is_file()}
    plan = service.make_plan([one, two], save, force=True)
    replace = service.os.replace
    calls = 0
    def fail_second(a, b):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('second publish failed')
        replace(a, b)
    monkeypatch.setattr(service.os, 'replace', fail_second)
    with pytest.raises(OSError, match='second publish'):
        service.apply_plan(plan)
    after = {p.relative_to(save): p.read_bytes() for p in save.rglob('*') if p.is_file()}
    assert before == after


def test_running_game_lock_blocks_import(tmp_path):
    src = source(tmp_path / 'save.psu')
    save = tmp_path / 'data/save'
    # Hold exactly the lock the native game and mod manager use, in another process.
    hold = '''import sys\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom save_import import runtime_lock\nwith runtime_lock(Path(sys.argv[2])):\n print("locked",flush=True)\n sys.stdin.readline()\n'''
    process = subprocess.Popen([sys.executable, '-B', '-c', hold, str(ROOT / 'scripts'), str(save)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == 'locked'
        assert service.main([str(src), '--save-dir', str(save)]) == 2
        assert not save.exists()
    finally:
        process.communicate('\n', timeout=10)


def test_xbox_options_follow_same_unlock_only_policy(tmp_path):
    save = tmp_path / 'data/save'
    target = native_options(save)
    template = bytearray(service.ps2.XBOX_OPTIONS)
    template[:8] = b'KEEPTHIS'
    (target / 'Options').write_bytes(service.ps2.signed_profile('Global', template))
    native_meta = (target / 'SaveMeta.xbx').read_bytes() + 'Description=keep native metadata\r\n'.encode('utf-16le')
    (target / 'SaveMeta.xbx').write_bytes(native_meta)
    (target / 'saveimage.xbx').write_bytes(b'native thumbnail')
    src = tmp_path / 'UDATA/45410049/OPTIONS'
    src.mkdir(parents=True)
    payload = bytearray(service.ps2.XBOX_OPTIONS)
    payload[:8] = b'OLDPREFS'
    import struct
    struct.pack_into('<III', payload, 0x1214, 1, 0, 0x17000001)
    (src / 'Options').write_bytes(service.ps2.signed_profile('Global', payload))
    (src / 'SaveMeta.xbx').write_bytes(b'\xff\xfe' + 'Name=Options\r\n'.encode('utf-16le'))
    assert service.main([str(src), '--save-dir', str(save), '--force']) == 1
    assert service.main([str(src), '--save-dir', str(save), '--force', '--include-options']) == 0
    out = (target / 'Options').read_bytes()[140:]
    assert out[:8] == b'KEEPTHIS' and out[0x1214:0x148C] == payload[0x1214:0x148C]
    assert (target / 'SaveMeta.xbx').read_bytes() == native_meta
    assert (target / 'saveimage.xbx').read_bytes() == b'native thumbnail'


DRIVER = r'''
#include "pc_save_import.h"
#include "pc_ui_actions.h"
#include <iostream>
#include <thread>
#include <chrono>
#if defined(_WIN32)
#include <windows.h>
#endif
std::string data;
namespace pcui { std::string folder_path(Folder) { return data; } }
int run(const std::string &data_path, const std::string &source_path) {
    data = data_path;
    if (!pcui::save_import_start(source_path, false, false, false)) {
        std::cout << pcui::save_import_view().status; return 2;
    }
    auto wait = []() {
        for (int i=0; i<1000 && pcui::save_import_busy(); i++) {
            pcui::save_import_poll(); std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    };
    wait();
    if (pcui::save_import_view().token.empty()) { std::cout << pcui::save_import_view().status; return 3; }
    std::cout << "preview=" << pcui::save_import_view().count << "\n";
    if (!pcui::save_import_start(source_path, false, false, true)) return 4;
    wait();
    std::cout << pcui::save_import_view().status;
    return pcui::save_import_busy() || pcui::save_import_view().failed ? 5 : 0;
}
#if defined(_WIN32)
int wmain(int argc, wchar_t **argv) {
    auto utf8 = [](const wchar_t *s) {
        int size = WideCharToMultiByte(CP_UTF8, 0, s, -1, nullptr, 0, nullptr, nullptr);
        std::string out(size, 0);
        WideCharToMultiByte(CP_UTF8, 0, s, -1, out.data(), size, nullptr, nullptr);
        out.resize(size - 1); return out;
    };
    return run(utf8(argv[1]), utf8(argv[2]));
}
#else
int main(int argc, char **argv) { return run(argv[1], argv[2]); }
#endif
'''


@pytest.fixture(scope='module', params=['c++17', 'c++20'])
def bridge(tmp_path_factory, request):
    folder = tmp_path_factory.mktemp('save bridge')
    main = folder / 'main.cpp'; main.write_text(DRIVER)
    compiler = shutil.which('cl') or shutil.which('clang++') or shutil.which('g++')
    if not compiler:
        pytest.skip('C++ compiler required')
    msvc = Path(compiler).stem.lower() == 'cl'
    exe = folder / ('bridge.exe' if msvc else 'bridge')
    native = ROOT / 'src/hooks/pc_save_import.cpp'
    if msvc:
        cmd = [compiler, '/nologo', '/std:' + request.param, '/EHsc', '/utf-8', '/DNOMINMAX',
               '/I' + str(ROOT / 'src/hooks'),
               # Forward slashes: a backslash path in a string-literal define becomes escape sequences.
               '/DDEFJAM_SAVE_SOURCE_DIR="' + ROOT.as_posix() + '"', str(main), str(native), '/Fe:' + str(exe),
               '/link', 'shell32.lib', 'comdlg32.lib', 'ole32.lib', 'user32.lib']
    else:
        if not shutil.which('pkg-config'):
            pytest.skip('SDL3 development package required')
        pkg = subprocess.run(['pkg-config', '--cflags', '--libs', 'sdl3'], capture_output=True, text=True)
        if pkg.returncode:
            pytest.skip('SDL3 development package required')
        cmd = [compiler, '-std=' + request.param, '-pthread', '-I' + str(ROOT / 'src/hooks'),
               '-DDEFJAM_SAVE_SOURCE_DIR="' + ROOT.as_posix() + '"', str(main), str(native), '-o', str(exe)] + shlex.split(pkg.stdout)
    result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def test_native_bridge_handles_unicode_spaces_and_shell_characters(bridge, tmp_path):
    src = source(tmp_path / '街 $(never-run) save.psu')
    save = tmp_path / 'Data 街 with spaces/save'
    env = dict(os.environ, DEFJAM_SAVE_PYTHON=sys.executable)
    result = subprocess.run([str(bridge), str(save), str(src)], cwd=tmp_path, env=env,
                            capture_output=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'preview=1' in result.stdout and 'Imported 1' in result.stdout
    assert (save / 'UserData/45410049' / service.xbox.folder_name('DEMO') / 'DEMO').is_file()
    assert src.exists() and not (tmp_path / 'never-run').exists()


def test_installed_helper_uses_bundled_interpreter(bridge, tmp_path):
    # Reproduce the package layout, with no developer interpreter override.
    payload = tmp_path / 'payload 街'
    scripts = payload / 'source/scripts'; scripts.mkdir(parents=True)
    for name in ('save-import.py', 'save_import.py', 'xbox_save_format.py', 'ps2_save_format.py',
                 'ps2_save_containers.py', 'ps2_lzari.py'):
        shutil.copyfile(ROOT / 'scripts' / name, scripts / name)
    python = payload / ('python/python.exe' if os.name == 'nt' else 'python/bin/python3')
    python.parent.mkdir(parents=True)
    if os.name == 'nt':
        pytest.skip('embedded Python package layout is checked in packaged Windows app retest')
    python.symlink_to(sys.executable)
    src = source(tmp_path / 'input.psu')
    env = {k: v for k, v in os.environ.items() if k != 'DEFJAM_SAVE_PYTHON'}
    env['DEFJAM_INSTALL_DIR'] = str(tmp_path / 'installed')
    result = subprocess.run([str(bridge), str(tmp_path / 'data/save'), str(src)], cwd=payload / 'source',
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list(scripts.glob('__pycache__/*')), 'verified source payload must stay immutable'
