"""scripts/compile-game-sources.py: which objects it compiles (no compiler needed)."""
import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('compile_game_sources', ROOT / 'scripts/compile-game-sources.py')
cgs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cgs)

TARGETS = '''CMakeFiles/defjam_recomp.dir/src/main.c.obj: C_COMPILER__defjam_recomp_unscanned_Release
CMakeFiles/defjam_recomp.dir/src/hooks/dev_module.c.obj: C_COMPILER__defjam_recomp_unscanned_Release
CMakeFiles/defjam_recomp.dir/src/hooks/pc_ui.cpp.o: CXX_COMPILER__defjam_recomp_unscanned_Release
CMakeFiles/defjam_recomp.dir/src/recomp/gen/recomp_dispatch.c.obj: C_COMPILER__defjam_recomp_unscanned_Release
xboxrecomp/src/kernel/CMakeFiles/xbox_kernel.dir/kernel.c.obj: C_COMPILER__xbox_kernel_unscanned_Release
defjam_recomp.exe: CXX_EXECUTABLE_LINKER__defjam_recomp_Release
'''


def test_game_objects_are_the_game_sources_but_not_lifted_code(monkeypatch):
    monkeypatch.setattr(cgs.subprocess, 'run',
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=TARGETS, stderr=''))
    assert cgs.game_objects('build') == ['CMakeFiles/defjam_recomp.dir/src/main.c.obj',
                                         'CMakeFiles/defjam_recomp.dir/src/hooks/dev_module.c.obj',
                                         'CMakeFiles/defjam_recomp.dir/src/hooks/pc_ui.cpp.o']


def test_refuses_where_lifted_code_is_present(tmp_path, monkeypatch):
    (tmp_path / 'recomp_0000.c').write_text('')
    monkeypatch.setattr(cgs, 'GEN', tmp_path)
    try:
        cgs.main([])
    except SystemExit as e:
        assert 'lifted code is present' in str(e)
    else:
        raise AssertionError('should refuse')


def test_host_options_are_forwarded_and_standins_are_removed(tmp_path, monkeypatch):
    gen = tmp_path / 'gen'
    template = tmp_path / 'template.h'
    template.write_text('/* invented host header */')
    monkeypatch.setattr(cgs, 'GEN', gen)
    monkeypatch.setattr(cgs, 'TEMPLATE', template)
    monkeypatch.setattr(cgs, 'game_objects', lambda _: ['host.o'])
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        assert (gen / 'recomp_types.h').exists()
        assert (gen / 'recomp_dispatch.c').exists()
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(cgs.subprocess, 'run', run)
    assert cgs.main(['--build', str(tmp_path / 'build'), '--cmake-arg=-DDEFJAM_SDL3=OFF']) == 0
    assert '-DDEFJAM_SDL3=OFF' in commands[0]
    assert '-DDEFJAM_BUILD_GAME=ON' in commands[0]
    assert not list(gen.iterdir())
