"""Xbox FFNY profile signatures and metadata; shared by the launcher importer."""
import hmac
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path

TITLE_ID = '45410049'
MAGIC = b'20CM'
HEADER = 0x4C            # 4 + 12 + 3 * 20
IDENTITY_END = 0x8C      # 64-byte identity block starts at HEADER
PORT_KEY = bytes(16)     # XboxSignatureKey as the port's kernel exports it
MAX_MEMBER = 4 << 20     # a profile is ~22 KiB; refuse anything absurd (zip bombs)
HASH_MOD = 0xFFFFFFFFFFC5
NAME_RE = re.compile(r'^[ -~]{1,32}$')   # printable ASCII; the game's profile names


def folder_name(name):
    """The directory the game derives from a profile name (src/hooks/save_compat.c, canonical)."""
    value = 0
    for char in name:
        value = (value * 65536 + ord(char)) % HASH_MOD
    return '%012X' % value


def parse_save_meta(raw):
    """The Name= value of a SaveMeta.xbx (UTF-16LE with a BOM), or None."""
    try:
        text = raw.decode('utf-16')
    except UnicodeDecodeError:
        return None
    match = re.match(r'Name=([^\r\n]*)', text)
    return match.group(1) if match else None


def hmac_sha1(key, data):
    return hmac.new(key, data, hashlib.sha1).digest()


def header_fault(blob):
    """None when the profile file has the shape the game expects, else why not."""
    if len(blob) < IDENTITY_END + 1:
        return 'too short'
    if blob[:4] != MAGIC:
        return 'not a 20CM profile file'
    size, header, payload = struct.unpack_from('<III', blob, 4)
    if size != len(blob):
        return 'size field %d does not match the file (%d bytes)' % (size, len(blob))
    if header != 0x40:
        return 'unexpected header size 0x%X' % header
    if payload != len(blob) - IDENTITY_END:
        return 'payload size field %d does not match the file' % payload
    return None


def signatures_ok(blob, key):
    """(identity, payload, header) fields each equal to the HMAC under key."""
    return (blob[0x10:0x24] == hmac_sha1(key, blob[HEADER:IDENTITY_END]),
            blob[0x24:0x38] == hmac_sha1(key, blob[IDENTITY_END:]),
            blob[0x38:HEADER] == hmac_sha1(key, blob[:0x38]))


def resign(blob, key):
    out = bytearray(blob)
    out[0x10:0x24] = hmac_sha1(key, bytes(out[HEADER:IDENTITY_END]))
    out[0x24:0x38] = hmac_sha1(key, bytes(out[IDENTITY_END:]))
    out[0x38:HEADER] = hmac_sha1(key, bytes(out[:0x38]))
    return bytes(out)


def resolve_save_dir(args):
    if args.save_dir:
        return Path(args.save_dir)
    if os.environ.get('DEFJAM_DATA'):
        return Path(os.environ['DEFJAM_DATA']) / 'save'
    installs = [Path(args.install)] if args.install else []
    installs.append(Path.home() / 'Library/Application Support/DefJamRecompiled/app')
    for install in installs:
        receipt = install / 'installed.json'
        if receipt.is_file():
            try:
                return Path(json.loads(receipt.read_text(encoding='utf-8'))['data']) / 'save'
            except (OSError, ValueError, KeyError):
                pass
    return None
