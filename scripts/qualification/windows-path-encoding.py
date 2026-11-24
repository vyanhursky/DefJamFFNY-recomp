"""Exercise the real toolchain resolver in a hidden Windows console at CP437.

This configures a LANGUAGES NONE fixture: its placeholder compiler is never
executed. The physical Unicode directory tests decoding of Python's UTF-8
output under CMake's old policy, independently of the runner's system locale.
Run only in a qualification guest or disposable hosted runner.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', type=Path, required=True)
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    parser.add_argument('--ninja', type=Path)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--expect-failure', action='store_true', help='Confirm the pre-fix resolver fails')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Windows required')
    ninja = (args.ninja or args.cmake.resolve().parents[2] / 'ninja/ninja.exe').resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error('Choose a new scratch directory')
    work.mkdir(parents=True)
    physical = work / 'Caf\u00e9 physical tools'
    (physical / 'bin').mkdir(parents=True)
    (physical / 'bin/clang.exe').write_bytes(b'Never executed: LANGUAGES NONE fixture')
    source = work / 'source'
    source.mkdir()
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(encoding_probe LANGUAGES NONE)\n'
        'file(WRITE "${CMAKE_BINARY_DIR}/resolved.txt" "${CMAKE_C_COMPILER}")\n'
        'if(NOT EXISTS "${CMAKE_C_COMPILER}")\n'
        ' message(FATAL_ERROR "The resolved Unicode compiler path does not exist")\nendif()\n', encoding='utf-8')
    batch = work / 'configure.cmd'
    batch.write_text('@echo off\nchcp 437 >nul\nif errorlevel 1 exit /b %errorlevel%\n'
        '"%LLVM_MINGW_PYTHON%" -I -c "import ctypes,os,pathlib; pathlib.Path(os.environ[\'DJQUAL_CP_FILE\']).write_text(str(ctypes.windll.kernel32.GetConsoleOutputCP()))"\n'
        'if errorlevel 1 exit /b %errorlevel%\n'
        '"%DJQUAL_CMAKE%" -S "%DJQUAL_SOURCE%" -B "%DJQUAL_BUILD%" -G Ninja "-DCMAKE_MAKE_PROGRAM=%DJQUAL_NINJA%" '
        '"-DCMAKE_TOOLCHAIN_FILE=%DJQUAL_TOOLCHAIN%" -DCMAKE_POLICY_DEFAULT_CMP0176=OLD\n'
        'exit /b %errorlevel%\n', encoding='ascii')
    env = os.environ.copy()
    env.update(LLVM_MINGW_ROOT=str(physical), LLVM_MINGW_PYTHON=str(args.python.resolve()),
        DJQUAL_CMAKE=str(args.cmake.resolve()), DJQUAL_NINJA=str(ninja), DJQUAL_SOURCE=str(source), DJQUAL_BUILD=str(work / 'build'),
        DJQUAL_TOOLCHAIN=str(args.toolchain.resolve()), DJQUAL_CP_FILE=str(work / 'codepage.txt'),
        DJQUAL_BATCH='"' + str(batch) + '"')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    with (work / 'configure.log').open('wb') as log:
        result = subprocess.run([env.get('ComSpec', 'cmd.exe'), '/d', '/c', '%DJQUAL_BATCH%'],
            env=env, startupinfo=startup, creationflags=subprocess.CREATE_NEW_CONSOLE,
            stdout=log, stderr=subprocess.STDOUT, timeout=30)
    resolved_file = work / 'build/resolved.txt'
    resolved = resolved_file.read_text(encoding='utf-8') if resolved_file.is_file() else None
    expected = (physical / 'bin/clang.exe').resolve().as_posix()
    codepage = int((work / 'codepage.txt').read_text(encoding='ascii'))
    assert codepage == 437, codepage
    report = dict(code_page=codepage, compiler_executed=False, exit_code=result.returncode,
                  expected=expected, resolved=resolved, expected_failure=args.expect_failure)
    (work / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.expect_failure:
        assert result.returncode != 0 and resolved is not None and resolved != expected, report
    else:
        assert result.returncode == 0 and resolved == expected, report
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
