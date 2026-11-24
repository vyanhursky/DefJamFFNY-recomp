"""Game-free contracts; these do not qualify a real Windows client install."""
import argparse
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load('bundled_setup_engine', ROOT / 'setup/engine.py')
contract = load('bundled_setup_contract', ROOT / 'setup/windows_toolchain.py')


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, 'IS_WINDOWS', True)
    monkeypatch.setattr(engine, 'IS_LINUX', False)
    monkeypatch.setattr(engine, 'HOST_PLATFORM', 'windows-x64')
    monkeypatch.setattr(engine, 'windows_long_paths_enabled', lambda: True)
    payload = tmp_path / 'payload'
    for name in (*contract.REQUIRED, 'python/python.exe', 'source/src/example.c'):
        target = payload / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'synthetic, never executed')
    files = {p.relative_to(payload).as_posix(): engine.digest(p) for p in payload.rglob('*') if p.is_file()}
    manifest = dict(schema=1, platform='windows-x64', version='1.2.2', source_commit='a'*40,
                    toolkit_commit='b'*40, files=files, windows_toolchain=contract.descriptor(files))
    engine.write_json(payload / 'manifest.json', manifest)
    args = argparse.Namespace(payload=str(payload), install_dir=str(tmp_path / 'install'),
        data_dir=str(tmp_path / 'data'), dump=None, status_file=None, cancel_file=None,
        install_prerequisites=False, toolchain='auto')
    setup = engine.Engine(args)
    setup.prepare_source()
    return setup


def test_bundle_uses_version_tools_and_sanitizes_developer_environment(tmp_path, monkeypatch):
    setup = fixture(tmp_path, monkeypatch)
    setup.env.update(INCLUDE='foreign headers', LIB='foreign libs', CC='cl',
                     CMAKE_TOOLCHAIN_FILE='foreign.cmake', LLVM_MINGW_ROOT='foreign')
    executed = []
    monkeypatch.setattr(setup, 'run', lambda argv, **kwargs: executed.append(argv))
    monkeypatch.setattr(setup, 'install_prerequisites', lambda: pytest.fail('must not install VS'))
    setup.toolchain()
    assert setup.windows_bundled
    assert all(Path(argv[0]).is_relative_to(setup.version_root / 'tools') for argv in executed)
    assert len(executed) == 3
    assert not any(key in setup.env for key in ('INCLUDE', 'LIB', 'CC', 'CMAKE_TOOLCHAIN_FILE'))
    assert setup.env['LLVM_MINGW_ROOT'] == str((setup.version_root / 'tools/llvm-mingw').resolve())
    assert str(setup.python.parent) in setup.env['PATH']
    overrides = setup.windows_bundled_overrides()
    assert any('llvm-mingw-x64.cmake' in value for value in overrides)
    assert '-DFETCHCONTENT_FULLY_DISCONNECTED=ON' in overrides
    assert (setup.version_root / 'toolchain.txt').read_text().endswith(setup.manifest['windows_toolchain']['fingerprint'])


@pytest.mark.parametrize('damage', ['missing', 'corrupt'])
def test_installed_tool_damage_stops_before_execution_then_prepare_repairs(tmp_path, monkeypatch, damage):
    setup = fixture(tmp_path, monkeypatch)
    target = setup.version_root / 'tools/llvm-mingw/bin/clang.exe'
    if damage == 'missing':
        target.unlink()
    else:
        target.write_bytes(b'corrupt')
    monkeypatch.setattr(setup, 'run', lambda *args, **kwargs: pytest.fail('damaged tools must not run'))
    with pytest.raises(engine.SetupError, match='verification failed'):
        setup.toolchain()
    setup.prepare_source()
    assert engine.digest(target) == setup.manifest['files']['tools/llvm-mingw/bin/clang.exe']


def test_bundle_fingerprint_switch_discards_only_objects(tmp_path, monkeypatch):
    setup = fixture(tmp_path, monkeypatch)
    build = setup.source / 'build' / engine.PRESET
    build.mkdir(parents=True)
    (build / 'old.obj').touch()
    generated = setup.source / 'src/recomp/gen'
    generated.mkdir(parents=True)
    (generated / 'owned.c').touch()
    setup.record_toolchain('msvc:old')
    monkeypatch.setattr(setup, 'run', lambda *args, **kwargs: '')
    setup.toolchain()
    assert not build.exists()
    assert (generated / 'owned.c').is_file()


def test_declared_bundle_never_silently_falls_back_to_host(tmp_path, monkeypatch):
    setup = fixture(tmp_path, monkeypatch)
    setup.manifest['windows_toolchain']['revision'] = 'unsupported'
    setup.args.install_prerequisites = True
    monkeypatch.setattr(setup, 'run', lambda *args, **kwargs: pytest.fail('must not discover or execute host tools'))
    monkeypatch.setattr(setup, 'install_prerequisites', lambda: pytest.fail('must not install VS'))
    with pytest.raises(ValueError, match='descriptor'):
        setup.toolchain()


@pytest.mark.parametrize('mutation', ['missing-notice', 'unexpected-tool', 'fingerprint'])
def test_payload_contract_rejects_incomplete_or_expanded_bundle(tmp_path, monkeypatch, mutation):
    setup = fixture(tmp_path, monkeypatch)
    manifest = setup.manifest
    if mutation == 'missing-notice':
        name = contract.NOTICES[0]
        (setup.payload / name).unlink()
        del manifest['files'][name]
        manifest['windows_toolchain'] = contract.descriptor(manifest['files'])
    elif mutation == 'unexpected-tool':
        name = 'tools/llvm-mingw/include/unexpected.exe'
        (setup.payload / name).parent.mkdir(parents=True, exist_ok=True)
        (setup.payload / name).write_bytes(b'not allowed')
        manifest['files'][name] = engine.digest(setup.payload / name)
        manifest['windows_toolchain'] = contract.descriptor(manifest['files'])
    else:
        manifest['windows_toolchain']['fingerprint'] = '0'*64
    engine.write_json(setup.payload / 'manifest.json', manifest)
    with pytest.raises(engine.SetupError):
        engine.verify_payload(setup.payload)


def test_preflight_checks_bundle_without_host_probe_and_reports_tampering(tmp_path, monkeypatch):
    setup = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(engine, 'windows_toolchain_present', lambda: pytest.fail('no host probe for bundled payload'))
    args = ['--payload', str(setup.payload), '--check-toolchain']
    assert engine.main(args) == 0
    (setup.payload / 'tools/ninja/ninja.exe').write_bytes(b'corrupt')
    assert engine.main(args) == 2


def test_historical_payload_retains_msvc_preflight_and_explicit_bundle_is_refused(tmp_path, monkeypatch):
    setup = fixture(tmp_path, monkeypatch)
    del setup.manifest['windows_toolchain']
    engine.write_json(setup.payload / 'manifest.json', setup.manifest)
    monkeypatch.setattr(engine, 'windows_toolchain_present', lambda: False)
    args = ['--payload', str(setup.payload), '--check-toolchain']
    assert engine.main(args) == 3
    monkeypatch.setattr(engine, 'windows_toolchain_present', lambda: True)
    assert engine.main(args) == 0
    assert engine.main(args + ['--toolchain', 'bundled']) == 3
    setup.args.toolchain = 'bundled'
    with pytest.raises(engine.SetupError, match='historical'):
        setup.toolchain()


def test_historical_release_handoff_keeps_backend_choice_and_install_opt_in():
    args = argparse.Namespace(toolchain='auto', install_prerequisites=False)
    command = engine.releases.child_arguments(args, Path('historical'), capable=True)
    assert command[command.index('--toolchain') + 1] == 'auto'
    assert '--install-prerequisites' not in command


def test_client_payload_excludes_host_vm_orchestration():
    package = load('bundled_setup_package', ROOT / 'scripts/package-setup.py')
    assert not package.source_allowed('scripts/qualification/windows-vm-host.ps1')
    assert not package.source_allowed('scripts/qualification/windows-vm-answer.py')


@pytest.mark.parametrize('dll,accepted', [('kernel32.dll', True), ('api-ms-win-crt-runtime-l1-1-0.dll', True),
    ('vcruntime140.dll', False), ('msvcp140.dll', False), ('unshipped.dll', False), ('libllvm-23.dll', False)])
def test_tool_import_audit_rejects_external_runtimes_and_missing_bundled_dlls(tmp_path, monkeypatch, dll, accepted):
    assets = load('bundled_setup_assets', ROOT / 'scripts/check-setup-assets.py')
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'tools/tool.exe').write_bytes(b'synthetic PE input')
    monkeypatch.setattr(assets, 'pe_imports', lambda data: [dll])
    if accepted:
        assets.check_windows_tool_imports(tmp_path)
    else:
        with pytest.raises(ValueError):
            assets.check_windows_tool_imports(tmp_path)


def test_tool_import_audit_accepts_the_included_dll_with_original_filename_case(tmp_path, monkeypatch):
    assets = load('bundled_setup_assets_case', ROOT / 'scripts/check-setup-assets.py')
    folder = tmp_path / 'tools/llvm-mingw/bin'
    folder.mkdir(parents=True)
    (folder / 'libLLVM-23.dll').write_bytes(b'synthetic PE input')
    monkeypatch.setattr(assets, 'pe_imports', lambda data: ['libllvm-23.dll'])
    assets.check_windows_tool_imports(tmp_path)


def test_windows_path_budget_accepts_near_limit_and_rejects_oversized_before_staging():
    suffix = '/versions/1.2.2-aaaaaaaaaaaa-bbbbbbbbbbbb-attempt-cccccccc'
    relative = 'source/setup-deps/' + 'a'*100 + '/file.h'
    short = 'C:/' + 'x'*50 + suffix
    engine.validate_windows_copy_paths(short, {relative: '0'*64})
    with pytest.raises(engine.SetupError, match='shorter writable') as error:
        engine.validate_windows_copy_paths('C:/' + 'x'*136 + suffix, {relative: '0'*64})
    assert error.value.code == 2


def test_windows_path_budget_counts_utf16_units_for_supplementary_characters():
    root = 'C:/' + '\U0001f600'*100
    with pytest.raises(engine.SetupError):
        engine.validate_windows_copy_paths(root, {'tools/' + 'x'*60 + '.h': '0'*64})
