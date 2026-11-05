"""Shared native file receipts compared with Python's independent SHA-256."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.fixture(scope='module')
def verifier(tmp_path_factory):
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler: pytest.skip('Native C compiler unavailable')
    folder = tmp_path_factory.mktemp('mod-file-hash')
    source = folder / 'probe.c'
    source.write_text('''#include "mod_sha256.h"
int main(int argc, char **argv) {
    char path[2048]; size_t n; unsigned c;
    if (argc != 3 || (n = strlen(argv[1])) % 2 || n / 2 >= sizeof path) return 2;
    for (size_t i = 0; i < n / 2; ++i) {
        if (sscanf(argv[1] + i * 2, "%2x", &c) != 1) return 2;
        path[i] = (char)c;
    }
    path[n / 2] = 0;
    return mod_file_matches(path, argv[2]) ? 0 : 1;
}
''')
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    includes = Path(__file__).resolve().parents[2] / 'src/hooks'
    command = ([compiler, '/nologo', '/TC', '/I' + str(includes), str(source), '/Fe' + str(exe)]
               if os.name == 'nt' else [compiler, '-std=c11', '-I', str(includes), str(source), '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


def check(verifier, path, digest):
    return subprocess.run([str(verifier), str(path).encode('utf-8').hex(), digest],
                          capture_output=True, timeout=15).returncode


@pytest.mark.parametrize('length', [0, 3, 55, 56, 63, 64, 65, 65537])
def test_native_digest_padding_streaming_and_utf8_path(verifier, tmp_path, length):
    path = tmp_path / 'receipt-\u03bb.bin'
    data = bytes(i % 251 for i in range(length)); path.write_bytes(data)
    assert check(verifier, path, hashlib.sha256(data).hexdigest()) == 0
    assert check(verifier, path, '0' * 64) == 1


def test_missing_files_and_malformed_receipts_fail(verifier, tmp_path):
    path = tmp_path / 'missing'
    assert check(verifier, path, '0' * 64) == 1
    path.write_bytes(b'abc')
    for digest in ('', '0' * 63, '0' * 65, 'g' * 64, hashlib.sha256(b'abc').hexdigest().upper()):
        assert check(verifier, path, digest) == 1
