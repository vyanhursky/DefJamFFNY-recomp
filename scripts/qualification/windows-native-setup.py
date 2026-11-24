"""Run the real packaged Windows engine on a tiny, explicitly synthetic project.

Run in a disposable hosted runner or qualification guest, never on the owner's
host. No game bytes are needed or produced. Native marker builds test setup
transactions and tool selection; they do not qualify a real game installation.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(folder):
    return {p.relative_to(folder).as_posix(): inventory_file(p)
            for p in folder.rglob('*') if p.is_file()}


def make_fixture(base, target, version, contract):
    target.mkdir()
    for path in base.iterdir():
        if path.name in ('source', 'manifest.json'):
            continue
        if path.is_dir():
            shutil.copytree(path, target / path.name)
        else:
            shutil.copyfile(path, target / path.name)
    source = target / 'source'
    (source / 'scripts').mkdir(parents=True)
    (source / 'config').mkdir()
    (source / 'src/recomp/gen').mkdir(parents=True)
    (source / 'cmake').mkdir()
    shutil.copyfile(base / 'source/cmake/llvm-mingw-x64.cmake', source / 'cmake/llvm-mingw-x64.cmake')
    (source / 'config/dump-manifest.json').write_text('{}')
    (source / 'scripts/verify-dump.py').write_text(
        "def verify(root, manifest):\n from pathlib import Path\n return [] if (Path(root)/'default.xbe').read_bytes()==b'synthetic setup fixture' else ['wrong fixture']\n")
    (source / 'scripts/pipeline.py').write_text(
        "import sys\nfrom pathlib import Path\nPath(sys.argv[1]+'.state').write_text('verified')\n")
    (source / 'scripts/pipeline-state.py').write_text(
        "from pathlib import Path\ndef verify_analysis(root, toolkit, python=None):\n"
        " if not (root/'analyze.state').is_file(): raise ValueError('not analyzed')\n"
        "def verify_lift(root, toolkit, python=None):\n"
        " if not (root/'recomp.state').is_file(): raise ValueError('not lifted')\n"
        "def verify_build(root, preset, python=None):\n"
        " if not (root/'build'/preset/'defjam_recomp.exe').is_file(): raise ValueError('not built')\n")
    preset = 'win-x64-release'
    (source / 'CMakePresets.json').write_text(json.dumps(dict(version=2, configurePresets=[dict(
        name=preset, generator='Ninja', binaryDir='${sourceDir}/build/' + preset,
        cacheVariables={'CMAKE_BUILD_TYPE': 'RelWithDebInfo'})], buildPresets=[dict(name=preset, configurePreset=preset)])))
    (source / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(setup_marker C)\n'
        'add_executable(defjam_recomp marker.c)\n')
    (source / 'marker.c').write_text(
        '#include <windows.h>\n#include <stdio.h>\n#include <stdlib.h>\n'
        'int main(void) { char path[4096]; const char *data=getenv("DEFJAM_DATA"); if(!data)return 2;\n'
        ' snprintf(path,sizeof(path),"%s/launcher-marker.txt",data); FILE *f=fopen(path,"w"); if(!f)return 3;\n'
        ' fprintf(f,"' + version + '\\n"); fclose(f); return 0; }\n', encoding='utf-8')
    manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    manifest.update(development=True, version=version, source_commit=hashlib.sha1(version.encode()).hexdigest())
    manifest['files'] = inventory(target)
    manifest['windows_toolchain'] = contract.descriptor(manifest['files'])
    contract.validate(manifest)
    (target / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Windows required')
    work = args.work.resolve()
    if work.exists():
        parser.error('Choose a new disposable work folder')
    work.mkdir(parents=True)
    base = args.payload.resolve(strict=True)
    engine = load('native_qualification_engine', base / 'engine/engine.py')
    manifest = engine.verify_payload(base)
    if 'windows_toolchain' not in manifest:
        parser.error('This qualification requires a bundled Windows payload')
    contract = engine.windows_contract()
    a = make_fixture(base, work / 'payload-a', '0.0.1', contract)
    b = make_fixture(base, work / 'payload-b', '0.0.2', contract)
    app, data, dump = (work / name for name in ('app', 'data', 'dump'))
    dump.mkdir()
    (dump / 'default.xbe').write_bytes(b'synthetic setup fixture')
    (data / 'save').mkdir(parents=True)
    (data / 'save/profile').write_bytes(b'preserve synthetic current progress')
    (data / 'settings.ini').write_bytes(b'; user comments\r\n[controls]\r\ncustom=keep\r\n')
    protected = inventory(data)
    reports = []
    metadata = dict(synthetic=True, host=platform.platform(), python=sys.version,
        source_commit=manifest['source_commit'], toolkit_commit=manifest['toolkit_commit'],
        toolchain=manifest['windows_toolchain'],
        base_manifest_sha256=hashlib.sha256((base / 'manifest.json').read_bytes()).hexdigest())
    def save():
        (work / 'results.json').write_text(json.dumps(dict(**metadata, results=reports), indent=2), encoding='utf-8')
    def unchanged():
        for name, sha in protected.items():
            assert inventory_file(data / name) == sha, name
    def command(package, operation, first=False):
        result = [package / 'python/python.exe', '-B', package / 'engine/engine.py', '--payload', package,
            '--bundled-only', '--operation', operation, '--install-dir', app, '--data-dir', data, '--no-shortcuts']
        if first:
            result += ['--dump', dump]
        return list(map(str, result))
    def run(label, argv, expected=0):
        started = time.monotonic()
        with (work / (label + '.out')).open('w', encoding='utf-8') as out:
            completed = subprocess.run(argv, stdout=out, stderr=subprocess.STDOUT, timeout=600)
        reports.append(dict(case=label, exit_code=completed.returncode, expected=expected,
                            seconds=round(time.monotonic() - started, 2)))
        save()
        assert completed.returncode == expected, label + ': see ' + str(work / (label + '.out'))
        unchanged()
    for label, package, operation, first in (
        ('install', a, 'install', True), ('update', b, 'update', False),
        ('downgrade', a, 'downgrade', False), ('repair-missing-output', a, 'repair', False),
        ('rebuild', a, 'rebuild', False)):
        if label == 'repair-missing-output':
            receipt = json.loads((app / 'installed.json').read_text())
            Path(receipt['executable']).unlink()
        run(label, command(package, operation, first))
        receipt = json.loads((app / 'installed.json').read_text())
        expected = json.loads((package / 'manifest.json').read_text())['version']
        assert receipt['version'] == expected and not (app / '.setup-transaction').exists()
        identity = Path(receipt['source']).parent / 'toolchain.txt'
        assert identity.read_text().startswith(contract.BACKEND + ':')
        compiler_notes = list((Path(receipt['source']) / 'build/win-x64-release/CMakeFiles').glob('*/CMakeCCompiler.cmake'))
        assert len(compiler_notes) == 1
        assert str((Path(receipt['source']).parent / 'tools/llvm-mingw/bin/clang.exe').resolve()).replace('\\', '/') in compiler_notes[0].read_text()
        env = os.environ.copy()
        env['DEFJAM_DATA'] = str(data)
        subprocess.run([receipt['executable']], check=True, env=env, timeout=30)
        assert (data / 'launcher-marker.txt').read_text().strip() == expected
        reports[-1].update(version=expected, compiler_identity=identity.read_text(), native_marker=True)
        save()
    # These are real cancellation and inventory failures at the standalone boundary.
    cancel = work / 'cancel'
    cancel.touch()
    before = (app / 'installed.json').read_bytes()
    run('cancel-before-stage', command(a, 'rebuild') + ['--cancel-file', str(cancel)], expected=6)
    assert (app / 'installed.json').read_bytes() == before
    target = a / 'tools/ninja/ninja.exe'
    original = target.read_bytes()
    target.write_bytes(b'corrupt synthetic qualification copy')
    try:
        run('corrupt-payload', command(a, 'rebuild'), expected=2)
        assert (app / 'installed.json').read_bytes() == before
    finally:
        target.write_bytes(original)
    print(json.dumps(dict(**metadata, results=reports), indent=2))


def inventory_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


if __name__ == '__main__':
    main()
