"""The comparison must reject real lifted-text changes, even across rechunking."""
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    'build_time_benchmark', Path(__file__).resolve().parents[2] / 'scripts/benchmark-build-time.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def _chunk(path, body):
    path.write_text('/** varying generated banner */\n#include <math.h>\n' + body, encoding='utf-8')


def test_identity_survives_rechunking_and_detects_changed_code(tmp_path):
    left, right = tmp_path / 'left', tmp_path / 'right'
    left.mkdir()
    right.mkdir()
    a, b = 'void a(void) { g_eax = 1; }\n', 'void b(void) { g_eax = 2; }\n'
    _chunk(left / 'recomp_0000.c', a + '\n' + b)
    _chunk(right / 'recomp_0000.c', a)
    _chunk(right / 'recomp_10000.c', b)
    for folder in (left, right):
        (folder / 'recomp_dispatch.c').write_text('same dispatch', encoding='utf-8')
    one, two = benchmark.generated_identity(left), benchmark.generated_identity(right)
    assert one['body_text_sha256'] == two['body_text_sha256']
    assert one['support_sha256'] == two['support_sha256']
    assert two['chunks'] == 2
    _chunk(right / 'recomp_0000.c', a.replace('= 1', '= 9'))
    assert benchmark.generated_identity(right)['body_text_sha256'] != one['body_text_sha256']


def test_identity_refuses_unrecognized_sources(tmp_path):
    (tmp_path / 'recomp_0000.c').write_text('not a generated chunk', encoding='utf-8')
    with pytest.raises(ValueError, match='Unrecognized'):
        benchmark.generated_identity(tmp_path)
