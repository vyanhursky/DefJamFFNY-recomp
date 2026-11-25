"""Protect the gameplay timing boundary from menu/partial/ended-match data."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]

def module(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    spec = importlib.util.spec_from_file_location('stream3_gameplay_test', ROOT / 'scripts/benchmark-runtime-stream3-gameplay.py')
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded

def event(tag, **fields):
    return ('['+tag+'] '+json.dumps(fields)+'\n').encode()

def test_partial_telemetry_and_menu_steps(monkeypatch):
    monitor = module(monkeypatch).FightWindow()
    monitor.consume(event('TEST-STATE', event='sample', match=0, step=9999))
    assert monitor.step == -1
    data = event('TEST-STATE', event='sample', match=1, step=601)
    monitor.consume(data[:20])
    assert monitor.step == -1
    monitor.consume(data[20:])
    assert monitor.step == 601
    assert monitor.reason is None

def test_early_result_invalidates_cpu_window(monkeypatch):
    monitor = module(monkeypatch).FightWindow()
    monitor.consume(event('TEST-EVENT', event='match_over', match=1, step=1801))
    assert monitor.reason == 'fight ended before measurement completed'

def test_fighter_identity_and_post_window_result(monkeypatch):
    monitor = module(monkeypatch).FightWindow()
    fighters = [{'slot':0},{'slot':1}]
    monitor.consume(event('TEST-EVENT', event='match_start', match=1, step=1, fighters=fighters))
    monitor.consume(event('TEST-STATE', event='sample', match=1, step=2401))
    monitor.consume(event('TEST-EVENT', event='result', match=1, step=2410))
    assert monitor.reason is None
    assert monitor.step == 2410
    assert monitor.fighters == fighters

def test_affinity_refuses_ambiguous_process_ownership(monkeypatch):
    module(monkeypatch)
    from runtime_benchmark_affinity import apply_owned_affinity
    alive = SimpleNamespace(poll=lambda:None)
    for owned in ([], [alive,alive]):
        harness = SimpleNamespace(_OWNED_PROCESSES=owned)
        with pytest.raises(RuntimeError,match='exactly one owned'):
            apply_owned_affinity(harness,0xffff)

def test_affinity_mask_validation(monkeypatch):
    module(monkeypatch)
    from runtime_benchmark_affinity import affinity_mask
    assert affinity_mask('0xffff') == 65535
    for value in ('0','-1','0x10000000000000000'):
        with pytest.raises(ValueError):
            affinity_mask(value)
