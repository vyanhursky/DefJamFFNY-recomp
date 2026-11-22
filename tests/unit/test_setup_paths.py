"""Setup's Windows path rules: how long and how named an install folder may be for the build to work."""
import importlib.util
from pathlib import Path
import re
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
