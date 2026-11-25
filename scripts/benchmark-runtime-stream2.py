#!/usr/bin/env python3
"""Serial scene trials with frame statistics and whole-process CPU residency.

Uses the normal save-guarded harness and recorder, without picture capture.
Windows/Linux process CPU is summed across threads; 100% means one busy logical CPU.
Results/captures remain local under logs/. Feature flags are explicit per run.
"""
import argparse
import copy
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import re
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('scene_perf', ROOT / 'scripts/scene-perf.py')
scene = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scene)
import harness


def competing_workloads():
    """Cheap name-only inventory; timing trials refuse builds/other games."""
    owned = {p.pid for p in harness._OWNED_PROCESSES}
    busy = []
    names = {'cl.exe', 'clang.exe', 'clang-cl.exe', 'cc1.exe', 'cc1plus.exe',
             'gcc.exe', 'g++.exe', 'zig.exe', 'ninja.exe', 'cmake.exe', 'msbuild.exe'}
    if os.name == 'nt':
        from ctypes import wintypes as w
        class Entry(ctypes.Structure):
            _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('pid', w.DWORD),
                        ('heap', ctypes.c_size_t), ('module', w.DWORD), ('threads', w.DWORD),
                        ('parent', w.DWORD), ('priority', w.LONG), ('flags', w.DWORD),
                        ('name', w.WCHAR * 260)]
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateToolhelp32Snapshot.argtypes, k.CreateToolhelp32Snapshot.restype = [w.DWORD, w.DWORD], w.HANDLE
        k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [w.HANDLE, ctypes.POINTER(Entry)]
        k.CloseHandle.argtypes = [w.HANDLE]
        snapshot = k.CreateToolhelp32Snapshot(2, 0)
        if snapshot == w.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), 'Cannot inventory benchmark workloads')
        try:
            entry = Entry(size=ctypes.sizeof(Entry))
            valid = k.Process32FirstW(snapshot, ctypes.byref(entry))
            while valid:
                name = entry.name.lower()
                if name in names or name == 'defjam_recomp.exe' and entry.pid not in owned:
                    busy.append('%s:%d' % (name, entry.pid))
                valid = k.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            k.CloseHandle(snapshot)
    elif Path('/proc').is_dir():
        names = {'cc1', 'cc1plus', 'gcc', 'g++', 'clang', 'clang++', 'cmake', 'ninja', 'make', 'zig'}
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                name = (proc / 'comm').read_text().strip()
                if name in names or re.fullmatch(r'(?:clang(?:\+\+)?|gcc|g\+\+)-\d+', name) or name == 'defjam_recomp' and int(proc.name) not in owned:
                    busy.append('%s:%s' % (name, proc.name))
            except OSError:
                pass
    return busy


def cpu_seconds(pid):
    if os.name == 'posix' and Path('/proc').is_dir():
        try:
            fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
            return (int(fields[11]) + int(fields[12])) / os.sysconf('SC_CLK_TCK')
        except (OSError, ValueError, IndexError):
            return None
    if os.name != 'nt':
        return None
    from ctypes import wintypes as w
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes, k.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
    k.GetProcessTimes.argtypes = [w.HANDLE, ctypes.POINTER(w.FILETIME), ctypes.POINTER(w.FILETIME),
                                  ctypes.POINTER(w.FILETIME), ctypes.POINTER(w.FILETIME)]
    k.CloseHandle.argtypes = [w.HANDLE]
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    creation, exit_time, kernel, user = (w.FILETIME() for _ in range(4))
    try:
        if not k.GetProcessTimes(h, ctypes.byref(creation), ctypes.byref(exit_time),
                                 ctypes.byref(kernel), ctypes.byref(user)):
            return None
        return sum(t.dwLowDateTime + (t.dwHighDateTime << 32) for t in (kernel, user)) / 1e7
    finally:
        k.CloseHandle(h)


class MeasuredScene(scene.SceneStop):
    def __init__(self, name):
        super().__init__(name)
        self.samples = []
        self.last_sample = 0
        self.last_inventory = -10
        self.interference = []

    def poll(self, tail_log, elapsed):
        now = time.monotonic()
        if now - self.last_inventory >= 2:
            self.last_inventory = now
            busy = competing_workloads()
            if busy:
                self.interference = busy
                self.reason = 'competing workload'
                return True
        stop = super().poll(tail_log, elapsed)
        if self.saw_play and self.reason is None and now - self.last_sample >= 0.5:
            self.last_sample = now
            processes = [p for p in harness._OWNED_PROCESSES if p.poll() is None]
            if len(processes) != 1:
                raise RuntimeError('CPU sampling requires exactly one owned game process')
            p = processes[0]
            value = cpu_seconds(p.pid)
            if value is not None:
                self.samples.append({'wall_s': time.monotonic(), 'harness_elapsed_s': elapsed,
                                     'pid': p.pid, 'process_cpu_s': value})
        return stop


def runtime_counters(log, name):
    """Nearest cumulative reports at scene boundaries and latest run reports.

    State reports are periodic and fence reports sparse: boundary differences
    are approximate and deliberately separate from exact frame/CPU samples.
    """
    latest, boundaries = {}, {}
    with open(log, encoding='utf-8', errors='replace') as stream:
        for line in stream:
            match = re.search(r'\[(S2SHADER|S2STATE|S2FENCE)\] (.*)', line)
            if match and ('enabled=' in match[2] or 'wait=' in match[2]):
                row = {}
                for key, raw in re.findall(r'(\w+)=([\d.,-]+)', match[2]):
                    def number(value):
                        return float(value) if '.' in value else int(value)
                    row[key] = [number(v) for v in raw.split(',')] if ',' in raw else number(raw)
                latest[match[1]] = row
            if '[SCENE] playing ' + name + ' ' in line:
                boundaries['start'] = copy.deepcopy(latest)
            elif '[SCENE] ' + name + ' ended;' in line:
                boundaries['end'] = copy.deepcopy(latest)
    boundaries['latest'] = latest
    return boundaries


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--label', required=True)
    ap.add_argument('--scenes', nargs='+', default=['sc00', 'sc07b'])
    ap.add_argument('--env', action='append', default=[])
    a = ap.parse_args()
    if not a.label.replace('-', '').replace('_', '').isalnum():
        ap.error('label must be a simple folder name')
    out = ROOT / 'logs/stream2' / a.label
    out.mkdir(parents=True, exist_ok=False)
    env = dict(scene.PROFILES['stress'], RECOMP_RECORD='1', RECOMP_RECORD_FPS='0',
               RECOMP_PRESENT_PACING='1', RECOMP_D3D11_SHADER_CACHE='0',
               RECOMP_D3D11_STATE_CACHE='0', RECOMP_FENCE_WAIT='0', RECOMP_FENCE_HOLD='1', RECOMP_STREAM2_STATS='1')
    for item in a.env:
        key, sep, value = item.partition('=')
        if not sep or not key.startswith('RECOMP_'):
            ap.error('--env requires RECOMP_NAME=VALUE')
        env[key] = value
    runs = []
    for name in a.scenes:
        busy = competing_workloads()
        if busy:
            raise SystemExit('Timing trial refused competing workloads: ' + ', '.join(busy))
        guard = MeasuredScene(name)
        run = harness.run_game('stream2-' + name, secs=480, preset=harness.RELEASE_PRESET,
                               scripted=False, quiet=True, env=dict(env, RECOMP_SCENE=name), controller=guard)
        session = scene.keep_session(scene.session_of(run.log), out / 'sessions' / name, name, False)
        entry = dict(scene=name, profile='stress', env=env, log=os.path.relpath(run.log, ROOT),
                     session=os.path.relpath(session, ROOT) if session else None,
                     played=guard.saw_play, ended=guard.reason == 'ended', stop=guard.reason,
                     exit_code=run.exit_code)
        entry['interference'] = guard.interference
        entry['faults'] = harness.run_faults(run)
        entry['save_ok'] = run.save_ok
        entry['unexpected_exit'] = run.unexpected_exit
        entry['identity'] = run.identity
        entry['runtime_counters'] = runtime_counters(run.log, name)
        (out / (name + '-cpu.json')).write_text(json.dumps(guard.samples, indent=2))
        if len(guard.samples) > 1:
            first, last = guard.samples[0], guard.samples[-1]
            wall = last['wall_s'] - first['wall_s']
            cpu = last['process_cpu_s'] - first['process_cpu_s']
            entry['cpu'] = dict(window_s=wall, cpu_s=cpu, percent_one_core=100 * cpu / wall)
        runs.append(entry)
        (out / 'runs.json').write_text(json.dumps(runs, indent=2))
        print(name, guard.reason, entry.get('cpu'), flush=True)
        if guard.reason != 'ended' or entry['faults'] or not session:
            raise SystemExit('Invalid trial (%s; %s; recorder=%s); inspect with scripts/triage.py' %
                             (guard.reason, entry['faults'], bool(session)))
        if (os.name == 'nt' or Path('/proc').is_dir()) and len(guard.samples) < 2:
            raise SystemExit('Invalid trial: no process CPU evidence')
    if scene.summarize(out, audio=False):
        raise SystemExit('Invalid scene recorder evidence; see summary.json')
    summary = json.loads((out / 'summary.json').read_text())
    summary['cpu'] = {r['scene']: r.get('cpu') for r in runs}
    summary['runtime_counters'] = {r['scene']: r['runtime_counters'] for r in runs}
    summary['game_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    summary['toolkit_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT / 'tools/xboxrecomp', text=True).strip()
    summary['manual_sha256'] = hashlib.sha256((ROOT / 'src/recomp_manual.c').read_bytes()).hexdigest()
    summary['benchmark_sha256'] = SCRIPT_SHA
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
