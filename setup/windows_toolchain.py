"""Contract shared by Windows payload packaging, inspection and setup.

The descriptor is opt-in: historical payloads without it still use MSVC. A
declared but broken bundle is an invalid payload, never a reason to install VS.
"""
import hashlib
import json

BACKEND = 'llvm-mingw-ucrt-x64'
REVISION = '20261117'
LLVM_BIN = frozenset(('clang.exe clang++.exe clang-23.exe ld.lld.exe llvm-ar.exe '
    'llvm-ranlib.exe llvm-nm.exe llvm-objdump.exe llvm-readobj.exe llvm-strip.exe '
    'llvm-windres.exe windres.exe llvm-rc.exe llvm-cvtres.exe clang-scan-deps.exe '
    'clang-scan-deps-real.exe libLLVM-23.dll libclang-cpp.dll libc++.dll libunwind.dll '
    'mingw32-common.cfg x86_64-pc-windows-gnu.cfg x86_64-w64-windows-gnu.cfg').split()) | frozenset(
        'x86_64-w64-mingw32-' + name + '.exe' for name in ('clang', 'clang++', 'gcc', 'g++', 'windres'))
LLVM_TREES = ('include/', 'x86_64-w64-mingw32/lib/', 'x86_64-w64-mingw32/share/mingw32/',
              'lib/clang/23/include/', 'share/libc++/')
CMAKE_TREES = tuple('share/cmake-3.31/' + part + '/' for part in ('Modules', 'Templates', 'include', 'Licenses'))
NOTICES = ('tools/llvm-mingw/LICENSE.TXT',
    'tools/llvm-mingw/x86_64-w64-mingw32/share/mingw32/COPYING',
    'tools/llvm-mingw/x86_64-w64-mingw32/share/mingw32/COPYING.MinGW-w64-runtime.txt',
    'tools/cmake/doc/cmake/Copyright.txt', 'tools/ninja/COPYING')
REQUIRED = NOTICES + tuple('tools/llvm-mingw/bin/' + name for name in sorted(LLVM_BIN)) + (
    'tools/llvm-mingw/lib/clang/23/lib/windows/libclang_rt.builtins-x86_64.a',
    'tools/cmake/bin/cmake.exe', 'tools/ninja/ninja.exe', 'source/cmake/llvm-mingw-x64.cmake')


def allowed(name):
    if name.startswith('tools/llvm-mingw/bin/'):
        return name[len('tools/llvm-mingw/bin/'):] in LLVM_BIN
    if name in REQUIRED:
        return True
    if name.startswith('tools/llvm-mingw/'):
        relative = name[len('tools/llvm-mingw/'):]
        return relative.startswith(LLVM_TREES) and not relative.lower().endswith(('.exe', '.dll', '.pdb'))
    if name.startswith('tools/cmake/'):
        relative = name[len('tools/cmake/'):]
        return relative.startswith(CMAKE_TREES) and not relative.lower().endswith(('.exe', '.dll', '.pdb'))
    return False


def fingerprint(files):
    inventory = {name: sha for name, sha in files.items()
                 if name.startswith('tools/') or name == 'source/cmake/llvm-mingw-x64.cmake'}
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def descriptor(files):
    return {'schema': 1, 'backend': BACKEND, 'revision': REVISION, 'fingerprint': fingerprint(files)}


def validate(manifest):
    declared = manifest.get('windows_toolchain')
    if declared is None:
        return None
    if manifest.get('platform') != 'windows-x64' or declared != descriptor(manifest['files']):
        raise ValueError('Unsupported or inconsistent Windows bundled toolchain descriptor')
    missing = set(REQUIRED) - set(manifest['files'])
    if missing:
        raise ValueError('Windows bundled toolchain inventory missing: ' + ', '.join(sorted(missing)))
    for name in manifest['files']:
        if name.startswith('tools/') and not allowed(name):
            raise ValueError('Unexpected Windows bundled tool: ' + name)
    return declared
