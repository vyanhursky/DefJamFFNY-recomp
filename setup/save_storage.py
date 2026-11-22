"""Verified, zero-skipping save copies. No image contents are assumed disposable."""
import ctypes
import contextlib
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


def allocated_bytes(path):
    """Allocated storage, rather than a sparse image's logical length."""
    if os.name != 'nt':
        return Path(path).stat().st_blocks * 512
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCompressedFileSizeW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.GetCompressedFileSizeW.restype = ctypes.c_ulong
    high = ctypes.c_ulong()
    ctypes.set_last_error(0)
    low = kernel.GetCompressedFileSizeW(str(path), ctypes.byref(high))
    if low == 0xffffffff and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    return low + (high.value << 32)


@contextlib.contextmanager
def exclusive_image(path):
    """OS-enforced writer/deletion exclusion also covers other installs/older games."""
    if os.name != 'nt':
        raise ValueError('Experimental compaction apply is Windows-only; allocation reporting is available here')
    import msvcrt
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
                                  ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    # READ|WRITE access, READ sharing only. Existing writers make this fail, and
    # new writers/deleters remain denied until our handle closes.
    handle = kernel.CreateFileW(str(path), 0xC0000000, 1, None, 3, 0x80000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(descriptor, 'r+b') as stream:
        yield stream


def zero_range(stream, start, end):
    """Deallocate only a range already proved zero while writers are excluded.

    FSCTL_SET_ZERO_DATA never changes logical size; holes read as the same zeros.
    https://learn.microsoft.com/windows/win32/api/winioctl/ni-winioctl-fsctl_set_zero_data
    """
    import msvcrt
    class Range(ctypes.Structure):
        _fields_ = [('start', ctypes.c_longlong), ('end', ctypes.c_longlong)]
    region = Range(start, end)
    returned = ctypes.c_ulong()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.DeviceIoControl.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p,
                                     ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong,
                                     ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p]
    kernel.DeviceIoControl.restype = ctypes.c_int
    if not kernel.DeviceIoControl(msvcrt.get_osfhandle(stream.fileno()), 0x980C8,
                                  ctypes.byref(region), ctypes.sizeof(region), None, 0,
                                  ctypes.byref(returned), None):
        raise ctypes.WinError(ctypes.get_last_error())


def restore_times(stream, before):
    """Use our owned handle; do not reopen a path while writes are excluded."""
    import msvcrt
    class FileTime(ctypes.Structure):
        _fields_ = [('low', ctypes.c_ulong), ('high', ctypes.c_ulong)]
    def encoded(ns):
        ticks = ns // 100 + 116444736000000000
        return FileTime(ticks & 0xffffffff, ticks >> 32)
    access, modified = encoded(before.st_atime_ns), encoded(before.st_mtime_ns)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.SetFileTime.argtypes = [ctypes.c_void_p, ctypes.POINTER(FileTime),
                                   ctypes.POINTER(FileTime), ctypes.POINTER(FileTime)]
    kernel.SetFileTime.restype = ctypes.c_int
    if not kernel.SetFileTime(msvcrt.get_osfhandle(stream.fileno()), None,
                              ctypes.byref(access), ctypes.byref(modified)):
        raise ctypes.WinError(ctypes.get_last_error())


def compact_image(path, report=print):
    """Preverified zero ranges only; no rename, truncation or discarded image bytes.

    Caller holds setup/data/play locks. The image handle excludes every writer
    (including games using another installation). In-place zero-range deallocation
    preserves the inode, ACLs, alternate streams and hardlinks; a crash leaves a
    partially compacted but byte-identical file. Full hashes also verify the result.
    """
    path = ordinary(Path(path))
    if path.stat().st_nlink > 1:
        raise ValueError('Image has multiple hard links; original kept: ' + path.name)
    with exclusive_image(path) as stream:
        before = os.fstat(stream.fileno())
        if before.st_nlink > 1:
            raise ValueError('Image has multiple hard links; original kept: ' + path.name)
        allocated = allocated_bytes(path)
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        stream.seek(0)
        # Discover and verify every range before mutation. Mixed blocks are kept.
        ranges = []
        offset, start = 0, None
        while block := stream.read(BLOCK):
            if block == ZERO[:len(block)]:
                if start is None:
                    start = offset
            elif start is not None:
                ranges.append((start, offset))
                start = None
            offset += len(block)
        if start is not None:
            ranges.append((start, offset))
        if not ranges or not allocated:
            report(path.name + ': no allocated zero range to compact')
            return dict(image=path.name, logical=before.st_size, before=allocated, after=allocated, changed=False)
        if not sparse_output(stream):
            raise ValueError('This volume cannot create sparse images; bytes unchanged')
        try:
            for first, end in ranges:
                zero_range(stream, first, end)
            os.fsync(stream.fileno())
            stream.seek(0)
            if (os.fstat(stream.fileno()).st_size != before.st_size
                    or hashlib.file_digest(stream, 'sha256').hexdigest() != digest):
                raise ValueError('Compaction byte verification failed: ' + path.name)
        finally:
            # Updating allocation may change timestamps. Restore access/write time;
            # the OS handle remains held so no writer can race this operation.
            restore_times(stream, before)
            os.fsync(stream.fileno())
        after = allocated_bytes(path)
    report(path.name + ': freed ' + str(max(0, allocated - after)) + ' bytes; all bytes verified')
    return dict(image=path.name, logical=before.st_size, before=allocated, after=after, changed=after < allocated)
