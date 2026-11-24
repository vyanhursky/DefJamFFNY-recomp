"""Stage the qualified x64 Windows tools from checksum-pinned upstream archives.

No compiler runs here. The per-file manifest covers the pruned files, licenses
and CMake toolchain; setup copies them into the immutable version attempt.
"""
import importlib.util
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = (
    ('llvm-mingw.zip', 'https://github.com/mstorsjo/llvm-mingw/releases/download/20261117/llvm-mingw-20261117-ucrt-x86_64.zip',
     '4d002e330a0f703625aa5ccbc37e96f8f824413e163bfc7336774aabd2c3a412', 'llvm-mingw-20261117-ucrt-x86_64', 'llvm-mingw'),
    ('cmake.zip', 'https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-windows-x86_64.zip',
     'd163cd3ab4959b0a53fa8988f2ddbd2e6c501658201e6a154386bad9dbe4f836', 'cmake-3.31.6-windows-x86_64', 'cmake'),
    ('ninja.zip', 'https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-win.zip',
     '524b344a1a9a55005eaf868d991e090ab8ce07fa109f1820d40e74642e289abc', '.', 'ninja'),
)
NINJA_NOTICE = ('https://raw.githubusercontent.com/ninja-build/ninja/v1.11.1/COPYING',
                'eb7e9ab9690124c5c9f42bdc81383d886a3dede26345b6ed15bbad7caf81f7ea')


def contract():
    spec = importlib.util.spec_from_file_location('windows_payload_contract', ROOT / 'setup/windows_toolchain.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage(staging, cache, download, unpack):
    rules = contract()
    cache.mkdir(parents=True, exist_ok=True)
    provenance = []
    for filename, url, sha, prefix, destination in ARCHIVES:
        archive = cache / filename
        download(url, archive, sha)
        provenance.append({'url': url, 'sha256': sha})
        with tempfile.TemporaryDirectory(prefix='windows-tools-', dir=cache) as scratch:
            unpack(archive, scratch)
            source = Path(scratch) / prefix
            for path in source.rglob('*'):
                if path.is_file():
                    relative = 'tools/' + destination + '/' + path.relative_to(source).as_posix()
                    if rules.allowed(relative):
                        target = staging / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(path, target)
    notice = cache / 'ninja-COPYING'
    download(NINJA_NOTICE[0], notice, NINJA_NOTICE[1])
    shutil.copyfile(notice, staging / 'tools/ninja/COPYING')
    provenance.append({'url': NINJA_NOTICE[0], 'sha256': NINJA_NOTICE[1]})
    for name in rules.REQUIRED:
        if not (staging / name).is_file():
            raise ValueError('Staged Windows toolchain is incomplete: ' + name)
    return provenance
