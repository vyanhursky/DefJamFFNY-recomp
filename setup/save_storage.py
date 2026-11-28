"""Verified, zero-skipping save copies. No image contents are assumed disposable."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

BLOCK = 1024 * 1024
ZERO = bytes(BLOCK)


def ordinary(path):
    path = Path(path)
    if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
        raise ValueError('Save backup cannot follow a link: ' + str(path))
    return path


def sparse_output(stream):
    """POSIX holes need no flag. On unsupported Windows volumes write dense instead."""
    if os.name != 'nt':
        return True
    import msvcrt
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.DeviceIoControl.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p,
                                     ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong,
                                     ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p]
    kernel.DeviceIoControl.restype = ctypes.c_int
    returned = ctypes.c_ulong()
    return bool(kernel.DeviceIoControl(msvcrt.get_osfhandle(stream.fileno()), 0x900C4,
                                      None, 0, None, 0, ctypes.byref(returned), None))


def sha256(path):
    with ordinary(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def set_length(stream, length, sparse):
    # Python's Windows truncate uses the CRT, which can zero-fill an extension
    # even after FSCTL_SET_SPARSE. SetEndOfFile preserves the skipped ranges.
    stream.flush()
    if os.name == 'nt' and sparse:
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.SetFilePointerEx.argtypes = [ctypes.c_void_p, ctypes.c_longlong,
                                          ctypes.POINTER(ctypes.c_longlong), ctypes.c_ulong]
        kernel.SetFilePointerEx.restype = ctypes.c_int
        kernel.SetEndOfFile.argtypes = [ctypes.c_void_p]
        kernel.SetEndOfFile.restype = ctypes.c_int
        handle = msvcrt.get_osfhandle(stream.fileno())
        if not kernel.SetFilePointerEx(handle, length, None, 0) or not kernel.SetEndOfFile(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        stream.truncate(length)


def sparse_copy(source, destination):
    """Exclusive destination; preserve logical length, all bytes and basic metadata.

    Returns whether holes were requested (allocation is filesystem-dependent).
    Callers must verify before deleting or replacing any source.
    """
    source, destination = ordinary(source), ordinary(destination)
    if not stat.S_ISREG(source.stat().st_mode):
        raise ValueError('Save backup requires a regular file: ' + str(source))
    with source.open('rb') as original, destination.open('xb') as copy:
        sparse = sparse_output(copy)
        length = 0
        while block := original.read(BLOCK):
            if sparse and block == ZERO[:len(block)]:
                copy.seek(len(block), os.SEEK_CUR)
            else:
                copy.write(block)
            length += len(block)
        set_length(copy, length, sparse)  # trailing holes and entirely zero images too
        copy.flush()
        os.fsync(copy.fileno())
    shutil.copystat(source, destination, follow_symlinks=False)
    return sparse


def entries(data):
    """Inventory only durable backup roots, including all raw images/caches in save/."""
    data = ordinary(data)
    result = {}

    def visit(path):
        ordinary(path)
        info = path.stat()
        name = path.relative_to(data).as_posix()
        if stat.S_ISDIR(info.st_mode):
            result[name] = None
            for child in sorted(path.iterdir()):
                visit(child)
        elif stat.S_ISREG(info.st_mode):
            result[name] = info.st_size
        else:
            raise ValueError('Unsupported save entry: ' + str(path))

    for name in ('save', 'fighter-state', 'settings.ini'):
        path = data / name
        ordinary(path)  # includes dangling links, which exists() would miss
        if path.exists():
            visit(path)
    return result


def backup(data, destination, report=print, forbidden=()):
    """Caller holds setup/data/play locks. Never merge with an existing backup."""
    data = ordinary(Path(data)).resolve()
    destination = Path(destination).resolve()
    for root in (data, *(Path(p).resolve() for p in forbidden)):
        if destination == root or root in destination.parents or destination in root.parents:
            raise ValueError('Save backup must be outside the install and data folders')
    before = entries(data)
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    try:
        for name, length in before.items():
            target = destination / name
            if length is None:
                target.mkdir()
            else:
                report('Backing up ' + name)
                holes = sparse_copy(data / name, target)
                if not holes:
                    report('Sparse files unavailable here; using an ordinary verified copy')
                hashes[name] = sha256(target)
                if target.stat().st_size != length or sha256(data / name) != hashes[name]:
                    raise ValueError('Save backup verification failed: ' + name)
        if entries(data) != before:
            raise ValueError('Saves changed while making the backup; original data kept')
        # Recheck every source at the end, including those copied before another large image.
        for name, digest in hashes.items():
            if sha256(data / name) != digest or sha256(destination / name) != digest:
                raise ValueError('Save backup changed during verification: ' + name)
        manifest = destination / 'backup.json.pending'
        with manifest.open('x', encoding='utf-8') as stream:
            json.dump(dict(schema=1, files=hashes, directories=[n for n, size in before.items() if size is None]), stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != 'nt':
            for directory in [destination / n for n, size in before.items() if size is None] + [destination]:
                fd = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        os.replace(manifest, destination / 'backup.json')
        if os.name != 'nt':
            fd = os.open(destination, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        report('Verified save backup: ' + str(destination))
        return destination
    except BaseException:
        # A partial backup is evidence, not permission to uninstall. Keep it and all sources.
        report('Backup incomplete; game builds and original data were kept. Partial copy: ' + str(destination))
        raise
