"""Optional Windows benchmark affinity, limited to the exact owned game.

No system-wide setting changes. The mask applies only to this child process
and disappears with it. Keep the same mask in every comparison arm.
"""
import ctypes
import os
from pathlib import Path

def affinity_mask(text):
    value = int(text, 0)
    if value <= 0 or value >= 1 << (ctypes.sizeof(ctypes.c_size_t) * 8):
        raise ValueError('affinity must be a nonzero mask fitting this host')
    return value

def apply_owned_affinity(harness, mask):
    owned = [p for p in harness._OWNED_PROCESSES if p.poll() is None]
    if len(owned) != 1:
        raise RuntimeError('Affinity requires exactly one owned live game')
    if os.name != 'nt':
        raise RuntimeError('This optional affinity control is Windows-only')
    from ctypes import wintypes as w
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes, k.OpenProcess.restype = [w.DWORD,w.BOOL,w.DWORD], w.HANDLE
    k.CloseHandle.argtypes = [w.HANDLE]
    k.QueryFullProcessImageNameW.argtypes = [w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
    k.GetProcessAffinityMask.argtypes = [w.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
    k.SetProcessAffinityMask.argtypes = [w.HANDLE,ctypes.c_size_t]
    process = k.OpenProcess(0x200 | 0x400 | 0x1000, False, owned[0].pid)
    if not process:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        name = ctypes.create_unicode_buffer(32768)
        length = w.DWORD(len(name))
        if not k.QueryFullProcessImageNameW(process,0,name,ctypes.byref(length)):
            raise ctypes.WinError(ctypes.get_last_error())
        expected = Path(harness.exe_path(harness.RELEASE_PRESET)).resolve()
        if Path(name.value).resolve() != expected:
            raise RuntimeError('Refusing affinity change: owned PID has an unexpected executable')
        before,system,after = ctypes.c_size_t(),ctypes.c_size_t(),ctypes.c_size_t()
        if not k.GetProcessAffinityMask(process,ctypes.byref(before),ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not mask or mask & ~system.value:
            raise ValueError('Affinity includes unavailable logical processors')
        if not k.SetProcessAffinityMask(process,mask):
            raise ctypes.WinError(ctypes.get_last_error())
        if not k.GetProcessAffinityMask(process,ctypes.byref(after),ctypes.byref(system)) or after.value != mask:
            raise RuntimeError('Requested affinity was not applied')
        return dict(pid=owned[0].pid,exe=str(expected),before=hex(before.value),after=hex(after.value),system=hex(system.value))
    finally:
        k.CloseHandle(process)
