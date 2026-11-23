#!/usr/bin/env python3
"""Run existing regression checks with explicit Stream 2 switches in every run.

Example: python scripts/check-runtime-stream2.py --quick
         python scripts/check-runtime-stream2.py --env RECOMP_FENCE_WAIT=1 --only ffa,visual,replay,repeat
Use --env RECOMP_NAME=value to override a switch. Startup isolation otherwise
removes inherited RECOMP variables, so inject these into the harness baseline
and record each effective environment. Fence waits remain off unless explicitly
requested. Does not change saved player settings.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stream2_benchmark', ROOT / 'scripts/benchmark-runtime-stream2.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)
harness = benchmark.harness


def instrument_harnesses(configure):
    """Apply configuration to fresh harness copies loaded by the existing tools.

    regress.py and scenario_suite.py intentionally exec their own modules rather
    than importing the cached `harness`. Scope the loader hook to that exact file.
    """
    original_spec = importlib.util.spec_from_file_location
    target = (ROOT / 'scripts/harness.py').resolve()

    def configured_spec(*args, **kwargs):
        spec = original_spec(*args, **kwargs)
        if spec and spec.origin and Path(spec.origin).resolve() == target:
            execute = spec.loader.exec_module

            def configured_exec(module):
                execute(module)
                configure(module)

            spec.loader.exec_module = configured_exec
        return spec

    importlib.util.spec_from_file_location = configured_spec

    def restore():
        importlib.util.spec_from_file_location = original_spec

    return restore


def main():
    ap = argparse.ArgumentParser(description=__doc__, add_help=False)
    ap.add_argument('--env', action='append', default=[])
    args, forward = ap.parse_known_args()
    flags = dict(RECOMP_D3D11_STATE_CACHE='1', RECOMP_D3D11_SHADER_CACHE='1',
                 RECOMP_FENCE_WAIT='0', RECOMP_FENCE_HOLD='1', RECOMP_STREAM2_STATS='1')
    for item in args.env:
        name, sep, value = item.partition('=')
        if not sep or not name.startswith('RECOMP_'):
            ap.error('--env requires RECOMP_NAME=value')
        flags[name] = value
    output = ROOT / 'logs/stream2' / ('validation-' + time.strftime('%Y%m%d-%H%M%S') + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    configured = []

    def configure(module):
        # All copies in this checker own the same children, so the workload
        # monitor cannot mistake a scenario's own game for a foreign process.
        original = module.run_game
        configured.append((module, original, dict(module.BASE_ENV), module._OWNED_PROCESSES))
        module._OWNED_PROCESSES = harness._OWNED_PROCESSES
        module.BASE_ENV.update(flags)

        def checked(*pos, **kw):
            return checked_run(module, original, *pos, **kw)

        module.run_game = checked

    def checked_run(module, original, *pos, **kw):
        quiet_since, announced = None, False
        while True:
            if benchmark.competing_workloads():
                quiet_since = None
                if not announced:
                    print('Stream 2 checks waiting for another game/build', flush=True)
                    announced = True
            else:
                now = time.monotonic()
                if quiet_since is None:
                    quiet_since = now
                if now - quiet_since >= 4:
                    break
            time.sleep(0.5)
        delegate = kw.get('controller')

        class Monitor:
            last = -10
            interference = []

            def poll(self, tail, elapsed):
                now = time.monotonic()
                if now - self.last >= 2:
                    self.last = now
                    self.interference = benchmark.competing_workloads()
                    if self.interference:
                        return True
                return delegate.poll(tail, elapsed) if delegate else False

        monitor = Monitor()
        kw['controller'] = monitor
        run = original(*pos, **kw)
        effective = run.identity['environment']
        missing = [name for name, value in flags.items() if effective.get(name) != value]
        if monitor.interference or missing:
            run.supervisor_failure = 'Stream 2 invalid run: interference=%s, missing overrides=%s' % (monitor.interference, missing)
        records.append(dict(log=run.log, identity=run.identity, save_ok=run.save_ok,
                            unexpected_exit=run.unexpected_exit, faults=module.run_faults(run)))
        output.write_text(json.dumps(records, indent=2) + '\n')
        return run

    configure(harness)
    restore_loader = instrument_harnesses(configure)
    sys.argv = [str(ROOT / 'scripts/regress.py'), *forward]
    try:
        try:
            runpy.run_path(sys.argv[0], run_name='__main__')
        except SystemExit as result:
            if result.code not in (None, 0):
                raise
        unit_only = '--only' in forward and forward[forward.index('--only') + 1:] == ['unit']
        if not records and not unit_only and not {'--help', '-h'}.intersection(forward):
            raise SystemExit('Invalid Stream 2 validation: no game runs were intercepted')
        if any(row['faults'] for row in records):
            raise SystemExit('Invalid Stream 2 validation: recorded run faults; see ' + str(output))
    finally:
        restore_loader()
        for module, original, environment, owned in reversed(configured):
            module.run_game = original
            module.BASE_ENV.clear()
            module.BASE_ENV.update(environment)
            module._OWNED_PROCESSES = owned


if __name__ == '__main__':
    main()
