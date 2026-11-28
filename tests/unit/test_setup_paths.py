"""Setup's Windows path rules: how long and how named an install folder may be for the build to work."""
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('paths_engine', ROOT / 'setup/engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

MAX_PATH_FILE = 259
APP = (ROOT / 'src/app/app_install.cpp').read_text(encoding='utf-8')
FOLDER_MAX = int(re.search(r'k_install_folder_max = (\d+);', APP).group(1))
# What was measured below a version folder: the longest object, and the longest file in the payload.
LONGEST_OBJECT = len('source/build/win-x64-release/_deps/sdl3-build/CMakeFiles/SDL3-static.dir/'
                     'src/render/vitagxm/SDL_render_vita_gxm_memory.c.obj')
LONGEST_SOURCE = len('source/setup-deps/sdl3/SDL3-3.4.18/VisualC/VisualC/examples/audio/'
                     '02-simple-playback-callback/02-simple-playback-callback.vcxproj')


def planned(monkeypatch, tmp_path, windows, version='1.2.1'):
    monkeypatch.setattr(engine, 'IS_WINDOWS', windows)
    monkeypatch.setattr(engine, 'verify_payload', lambda payload: {
        'version': version, 'source_commit': 'a' * 40, 'toolkit_commit': 'b' * 40})
    args = SimpleNamespace(payload=str(tmp_path / 'payload'), install_dir=str(tmp_path / 'game'),
                           data_dir=str(tmp_path / 'data'), dump=None, operation='install')
    return engine.Engine(args).version_root


def test_the_windows_version_folder_is_short_and_still_a_discardable_attempt(monkeypatch, tmp_path):
    first, second = (planned(monkeypatch, tmp_path, True) for _ in range(2))
    assert re.fullmatch(r'1\.2\.1-attempt-[0-9a-f]{8}', first.name)
    assert first != second
    first.mkdir(parents=True)
    engine.discard_failed_attempt(SimpleNamespace(version_root=first, install=tmp_path / 'game'))
    assert not first.exists()


def test_other_platforms_keep_the_commits_in_the_folder_name(monkeypatch, tmp_path):
    name = planned(monkeypatch, tmp_path, False).name
    assert name.startswith('1.2.1-' + 'a' * 12 + '-' + 'b' * 12 + '-attempt-')


def test_the_engine_limit_leaves_room_for_the_longest_measured_paths():
    for longest in (LONGEST_OBJECT, LONGEST_SOURCE):
        assert engine.WINDOWS_VERSION_ROOT_MAX + 1 + longest <= MAX_PATH_FILE


@pytest.mark.parametrize('version', ['1.2.1', '1.10.0-beta.10', '10.20.30-beta.100'])
def test_the_longest_folder_the_app_accepts_builds(monkeypatch, tmp_path, version):
    name = planned(monkeypatch, tmp_path, True, version).name
    folder = 'C:/' + 'x' * (FOLDER_MAX - 3)
    engine.check_build_path(Path(folder) / 'game/versions' / name)


def test_the_longest_folder_the_app_accepts_takes_the_upscaled_textures():
    deepest = '/data/hd-work/setup-lanczos/%s/thumbnails/%s.jpg.1234567.pending' % ('f' * 64, 'f' * 64)
    assert FOLDER_MAX + len(deepest) <= MAX_PATH_FILE


def test_the_default_folder_fits_the_longest_windows_user_name():
    assert len('C:/Users/%s/AppData/Local/Programs/DefJamRecompiled' % ('u' * 20)) <= FOLDER_MAX


def version_root(length, letter='x'):
    tail = '/game/versions/1.2.1-attempt-12345678'
    return Path('D:/' + letter * (length - 3 - len(tail)) + tail)


@pytest.mark.parametrize('letter', ['x', '\u00e9'])
def test_the_limit_counts_characters_not_bytes(letter):
    engine.check_build_path(version_root(engine.WINDOWS_VERSION_ROOT_MAX, letter))
    with pytest.raises(engine.SetupError, match='1 characters too long'):
        engine.check_build_path(version_root(engine.WINDOWS_VERSION_ROOT_MAX + 1, letter))


def test_a_character_outside_the_bmp_counts_twice_as_windows_counts_it():
    assert engine.windows_path_length('D:/\U0001F3A4') == 5


def test_a_long_folder_is_refused_before_anything_expensive(monkeypatch, tmp_path):
    install, data = tmp_path / 'game', tmp_path / 'data'
    state = engine.Engine.__new__(engine.Engine)
    state.args = SimpleNamespace(log=str(tmp_path / 'setup.log'), status_file=None, cancel_file=None)
    state.manifest = {'version': '1.2.1', 'source_commit': 'a' * 40, 'toolkit_commit': 'b' * 40}
    state.install, state.data = install, data
    state.version_root = version_root(engine.WINDOWS_VERSION_ROOT_MAX + 5)
    monkeypatch.setattr(engine, 'IS_WINDOWS', True)
    monkeypatch.setattr(engine, 'check_launcher_closed', lambda root: None)
    monkeypatch.setattr(engine, 'game_lock', lambda root: engine.contextlib.nullcontext())
    reached = []
    for stage in ('check_install_destination', 'prepare_source', 'extract', 'toolchain', 'pipeline'):
        monkeypatch.setattr(state, stage, lambda *a, stage=stage, **k: reached.append(stage))
    with pytest.raises(engine.SetupError, match='too long') as refused:
        state.execute()
    assert refused.value.code == 2 and not reached


windows_only = pytest.mark.skipif(os.name != 'nt', reason='Windows code pages and tools')


def test_precompiled_headers_are_off_only_outside_ascii():
    assert engine.windows_path_options(Path('D:/Games/Def Jam/source')) == []
    for folder in ('D:/Caf\u00e9 DJ/source', 'C:/Users/Jo\u00e3o/source', 'D:/\u0141\u00f3d\u017a/source'):
        assert engine.windows_path_options(Path(folder)) == ['-DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON']


def encoding_check(monkeypatch, representable, ninja, cmake='3.31.6-msvc6'):
    state = engine.Engine.__new__(engine.Engine)
    state.install = state.source = Path('folder')
    monkeypatch.setattr(engine, 'in_ansi_code_page', lambda path: representable)

    def run(argv, **options):
        assert not representable, 'must not be asked'
        if argv[0] == 'cmake':
            return 'cmake version ' + cmake + '\n'
        if isinstance(ninja, Exception):
            raise ninja
        return ninja
    state.run = run
    state.check_path_encoding()


def test_a_folder_in_the_code_page_needs_no_newer_tools(monkeypatch):
    encoding_check(monkeypatch, True, '', '3.20.0')


@pytest.mark.parametrize('cmake', ['3.21.0', '3.31.6-msvc6', '4.1.2'])
def test_newer_tools_build_outside_the_code_page(monkeypatch, cmake):
    encoding_check(monkeypatch, False, 'Build file encoding: UTF-8\n', cmake)


@pytest.mark.parametrize('cmake', ['3.20.21032501-MSVC_2', '3.9.0', 'unknown'])
def test_an_older_cmake_is_refused_outside_the_code_page_whatever_ninja_is(monkeypatch, cmake):
    with pytest.raises(engine.SetupError, match='cannot build in a folder'):
        encoding_check(monkeypatch, False, 'Build file encoding: UTF-8\n', cmake)


@pytest.mark.parametrize('ninja', ['Build file encoding: ANSI\n', engine.SetupError('unknown tool')],
                         ids=['ansi', 'before-1.11'])
def test_an_ansi_ninja_is_refused_outside_the_code_page(monkeypatch, ninja):
    with pytest.raises(engine.SetupError, match='cannot build in a folder') as refused:
        encoding_check(monkeypatch, False, ninja)
    assert refused.value.code == 2


def test_cancelling_is_not_taken_for_an_old_ninja(monkeypatch):
    with pytest.raises(engine.SetupError) as stopped:
        encoding_check(monkeypatch, False, engine.SetupError('cancelled', 6))
    assert stopped.value.code == 6


@windows_only
def test_the_code_page_check_knows_what_no_ansi_page_holds():
    assert engine.in_ansi_code_page('D:/Games/Def Jam')
    import locale
    if locale.getencoding().lower() in ('utf-8', 'cp65001'):
        pytest.skip('this Windows uses UTF-8 as its ANSI code page')
    assert not engine.in_ansi_code_page('D:/\U0001F3A4')


@windows_only
def test_the_imported_toolchain_environment_keeps_non_ascii_values(tmp_path):
    if not shutil.which('cl'):
        pytest.skip('Visual Studio Build Tools required')
    given = {'DEFJAM_DATA': 'D:\\Caf\u00e9 DJ\\data', 'DEFJAM_PROBE_USER': 'C:\\Users\\Jo\u00e3o\\Temp',
             'DEFJAM_PROBE_WIDE': 'D:\\\u0141\u00f3d\u017a \u683c'}
    state = engine.Engine.__new__(engine.Engine)
    state.args = SimpleNamespace(status_file=None, cancel_file=None, install_prerequisites=False)
    state.log, state.payload, state.version_root, state.python = None, tmp_path, tmp_path, tmp_path / 'python.exe'
    state.manifest = {}             # a payload without a bundled compiler: the host MSVC path this test imports
    state.env = dict(os.environ, **given)
    state.event = lambda message: None
    state.toolchain()
    assert {key: state.env[key] for key in given} == given


@windows_only
@pytest.mark.parametrize('name', ['plain', 'Caf\u00e9 DJ', '\u0141\u00f3d\u017a'])
def test_the_resource_script_compiles_in_any_folder(tmp_path, name):
    tools = [shutil.which(tool) for tool in ('cmake', 'ninja', 'cl', 'rc')]
    if not all(tools):
        pytest.skip('CMake, Ninja and MSVC required')
    if name != 'plain' and not name.isascii() and not engine.in_ansi_code_page(name):
        probe = subprocess.run([tools[1], '-t', 'wincodepage'], capture_output=True)
        if b'UTF-8' not in probe.stdout:
            pytest.skip('this Ninja cannot build outside the code page, which setup refuses')
    top = tmp_path / name
    for part in ('cmake/windows_resource.cmake', 'cmake/app.rc.in', 'branding/icon/defjam.ico'):
        (top / part).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / part, top / part)
    (top / 'main.c').write_text('int main(void) { return 0; }\n')
    (top / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(probe C RC)\ninclude(cmake/windows_resource.cmake)\n'
        'defjam_windows_resource(RC NAME probe VERSION 1.2.3 DESCRIPTION "probe")\n'
        'add_executable(probe main.c "${RC}")\n')
    for command in ([tools[0], '-G', 'Ninja', '-S', '.', '-B', 'out'], [tools[0], '--build', 'out']):
        done = subprocess.run(command, cwd=top, capture_output=True)
        assert done.returncode == 0, (done.stdout + done.stderr).decode(errors='replace')
    assert (top / 'out/probe.exe').is_file()
