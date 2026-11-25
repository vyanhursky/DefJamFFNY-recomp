"""Fresh, independently exec'd harness copies must receive the experiment flags.

This reproduces the loader path used by regress.py and scenario_suite.py without
launching a game. A checker that intercepts nothing must never report success.
"""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    spec = importlib.util.spec_from_file_location('stream2_runner_test', ROOT / 'scripts/check-runtime-stream2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fresh_harness(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/harness.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fresh_copies_are_instrumented_and_loader_is_restored(runner, tmp_path):
    original = importlib.util.spec_from_file_location
    configured = []

    def configure(module):
        module.BASE_ENV['RECOMP_FENCE_WAIT'] = '1'
        configured.append(module)

    restore = runner.instrument_harnesses(configure)
    try:
        first, second = fresh_harness('stream2_first'), fresh_harness('stream2_second')
        assert first is not second
        assert first.BASE_ENV['RECOMP_FENCE_WAIT'] == second.BASE_ENV['RECOMP_FENCE_WAIT'] == '1'
        other = tmp_path / 'unrelated.py'
        other.write_text('value = 7\n')
        spec = importlib.util.spec_from_file_location('stream2_unrelated', other)
        spec.loader.exec_module(importlib.util.module_from_spec(spec))
        assert configured == [first, second]
    finally:
        restore()
    assert importlib.util.spec_from_file_location is original


@pytest.mark.parametrize('arguments,expected', [([], '0'), (['--env', 'RECOMP_FENCE_WAIT=1'], '1')])
def test_cli_fence_wait_is_explicit_opt_in_in_fresh_copies(runner, monkeypatch, arguments, expected):
    original_run = runner.harness.run_game
    before = dict(runner.harness.BASE_ENV)

    def fake_regression(*args, **kwargs):
        # Load as the existing regression/scenario tools do, not `import harness`.
        module = fresh_harness('stream2_cli_fresh')
        assert module.BASE_ENV['RECOMP_FENCE_WAIT'] == expected
        assert module._OWNED_PROCESSES is runner.harness._OWNED_PROCESSES
        assert module.run_game.__name__ == 'checked'
        return {}

    monkeypatch.setattr(runner.runpy, 'run_path', fake_regression)
    monkeypatch.setattr(sys, 'argv', ['check-runtime-stream2.py', *arguments, '--help'])
    runner.main()
    assert runner.harness.run_game is original_run
    assert runner.harness.BASE_ENV == before


def test_missing_interception_is_a_failure(runner, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner.runpy, 'run_path', lambda *args, **kwargs: {})
    monkeypatch.setattr(sys, 'argv', ['check-runtime-stream2.py', '--only', 'm2'])
    with pytest.raises(SystemExit, match='no game runs were intercepted'):
        runner.main()
