"""Supervise the launcher's native process using committed profile sessions.

The native launcher remains the parent. It reads a bounded ready projection,
uses the supplied private save root, and waits for final acknowledgement on
normal exit. A dead parent never causes replay of its abandoned workspace.
"""
import os
from pathlib import Path
import time

from mods import atomic_bytes, atomic_json, check, file_lock, ordinary_path, read_json
from fighter_packages import build, enabled, runtime_environment
from fighter_build import retail_catalog
from fighter_bindings import seed
from fighter_profile_store import Store
from fighter_profile_session import prepare


def parent_watch(pid):
    check(type(pid) is int and pid > 0, 'Managed Fighter launch needs its native parent process')
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        check(handle, 'Native parent process is no longer available')
        return lambda: kernel.WaitForSingleObject(handle, 0) == 258, lambda: kernel.CloseHandle(handle)
    check(os.getppid() == pid, 'Managed Fighter supervisor must be a direct child of the native launcher')
    return lambda: os.getppid() == pid, lambda: None


def projection(path, state, environment=None, data_root=None, detail=''):
    values = {'state': state, 'detail': detail, 'data_root': str(data_root or ''),
              'parent_pid': path.stem.removeprefix('fighter-session-')}
    lines = ['[session]']
    for key, value in values.items():
        check('\n' not in value and '\r' not in value and len(value.encode('utf-8')) < 2000, 'Invalid managed launch projection')
        lines.append(key + '=' + value)
    if environment:
        lines.append('[environment]')
        for key, value in environment.items():
            check(key.startswith('RECOMP_FIGHTER_') and '\n' not in value and '\r' not in value and len(value.encode('utf-8')) < 2000,
                  'Invalid Fighter launch environment')
            lines.append(key + '=' + value)
    atomic_bytes(path, ('\n'.join(lines) + '\n').encode('utf-8'))


def supervise(manager, pid, *, language=None):
    ready = ordinary_path(manager.root / f'fighter-session-{pid}.ini')
    stop = ordinary_path(manager.root / f'fighter-session-{pid}.stop')
    alive, close = parent_watch(pid)
    session = None
    started = False
    try:
        # Parent also holds runtime.lock: installed files/configuration cannot
        # change between validation, native consumption and final save commit.
        with file_lock(manager.root / 'runtime.lock', shared=True), file_lock(manager.root / 'fighter-play.lock'):
            check(not (manager.root / 'journal.json').exists(), 'Recover the interrupted mod transaction before Play')
            state = manager.state()
            adoption_path = ordinary_path(manager.root / 'fighter-adoption.json')
            adoption = read_json(adoption_path)
            store_root = ordinary_path(manager.root / 'fighter-profiles')
            if not enabled(state) and adoption is None and not (store_root / 'head.json').exists():
                projection(ready, 'unused')
                return
            check(not (manager.root / 'journal.json').exists(), 'Recover the interrupted mod transaction before Play')
            manager.progress('Preparing Fighter Mod Support')
            cache, report, screens, composed = build(manager, state, language=language)
            check(alive(), 'Native launcher closed during Fighter preparation')
            catalog = retail_catalog(manager.game / 'assets/djv2.sod')
            store = Store(store_root, seed(catalog.db, catalog.source_sha256, catalog.rows))
            generation = store.load()
            source = ordinary_path(manager.data / 'save')
            title = ordinary_path(source / 'UserData/45410049')
            empty = not title.exists() or not any(title.iterdir())
            if adoption is not None:
                check(isinstance(adoption, dict) and adoption == {'schema': 1, 'baseline': catalog.source_sha256, 'initial_empty': adoption.get('initial_empty')}
                      and type(adoption['initial_empty']) is bool, 'Invalid Fighter profile adoption record')
                check(generation is not None or adoption['initial_empty'] and not any(store.generations.iterdir()),
                      'Committed Fighter profiles are missing; restore the profile Store backup before Play')
            # An adopted, initially empty career stays empty until its first
            # verified native save. Later files in the old import folder are
            # not permission to import again.
            fresh = generation is None and (adoption['initial_empty'] if adoption is not None else empty)
            session = prepare(store, report['binding_ledger'], manager.root / 'fighter-sessions',
                              source=None if fresh else source, fresh=fresh)
            if adoption is None:
                atomic_json(adoption_path, {'schema': 1, 'baseline': catalog.source_sha256, 'initial_empty': fresh})
            from fighter_ui_hd import stage as stage_ui_hd
            ui_pack=stage_ui_hd(cache,report,manager.mods)
            environment = runtime_environment(cache, report, screens, composed,**({'ui_pack':ui_pack} if ui_pack else {}))
            environment.update({key: value for key, value in session.environment.items() if key != 'DEFJAM_DATA'})
            session.monitor.start(); started = True
            projection(ready, 'ready', environment, session.data_root)
            manager.progress('Fighter Mod Support active; profile saves are supervised')
            while alive() and not stop.exists():
                check(session.monitor.error is None, 'Fighter profile verification failed: ' + str(session.monitor.error))
                time.sleep(.1)
            clean = stop.exists()
            session.finish(require_complete=clean); started = False
            projection(ready, 'complete', detail='Profile saves committed' if clean else 'Recovered last committed profiles after native process exit')
    except Exception as error:
        projection(ready, 'failed', detail=str(error).replace('\n', ' ').replace('\r', ' ')[:1500])
        manager.progress(str(error))
        raise
    finally:
        if started:
            session.monitor.stop()
        close()
