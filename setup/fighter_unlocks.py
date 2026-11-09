"""Stable-key projection of the fixed native Options Character unlock set.

This operates on the audited 0x1490 settings subpayload, not a complete Options
file or the separate 0x5904 user-profile payload. It owns no filesystem writes.
Native runtime storage, complete save interception and coherent publication of
settings plus extension remain required before this can activate any mod.
"""
from hashlib import sha256
import struct

from fighter_bindings import allocate
from fighter_registry import fingerprint

SCHEMA = 'fighter-unlocks-1'
SIZE = 0x1490
COUNT = 0x1218
SENTINEL = 0x1290
KEYS = 0x1294
CAPACITY = 80
METADATA = 0x00800000
IDENTITY = 0xff7fffff


def entries(ledger, baseline):
    # Reuse the allocator's full historical/retail immutability checks.
    return allocate(baseline, (), ledger)['fighters']


def settings_keys(payload):
    if not isinstance(payload, bytes) or len(payload) != SIZE:
        raise ValueError('Unsupported Options settings payload size')
    count = struct.unpack_from('<I', payload, COUNT)[0]
    if count > CAPACITY or struct.unpack_from('<I', payload, SENTINEL)[0] != 0xffffffff:
        raise ValueError('Invalid native Character unlock count or sentinel')
    values = list(struct.unpack_from(f'<{count}I', payload, KEYS))
    identities = [value & IDENTITY for value in values]
    if any(left >= right for left, right in zip(identities, identities[1:])):
        raise ValueError('Native Character unlock keys are duplicated or unsorted')
    return values


def read(payload, ledger, baseline):
    """Decode existing native/stable handles; preserve the opaque metadata bit."""
    known = {entry['handle']: key for key, entry in entries(ledger, baseline).items()}
    marks = {}
    for value in settings_keys(payload):
        identity = known.get(value & IDENTITY)
        if identity is None:
            raise ValueError('Native Character unlock has no historical fighter binding')
        marks[identity] = value & METADATA
    return marks


def validate_marks(marks, known):
    if not isinstance(marks, dict) or not marks.keys() <= known.keys():
        raise ValueError('Unlock state contains an unknown historical fighter')
    if any(type(value) is not int or value not in (0, METADATA) for value in marks.values()):
        raise ValueError('Invalid native Character unlock metadata')


def project(payload, marks, ledger, baseline):
    """Return retail-only native settings and a hash-bound custom extension.

    marks is the complete live set exported by the future expanded native
    container. Disabled fighters remain historical keys and are retained here.
    Only the count and 80 key cells change; all other native bytes are preserved.
    """
    settings_keys(payload)
    known = entries(ledger, baseline)
    validate_marks(marks, known)
    retail = sorted(known[key]['handle'] | value for key, value in marks.items() if key.startswith('retail/'))
    # Sort comparisons ignore bit 23, exactly as the native set does.
    retail.sort(key=lambda value: value & IDENTITY)
    if len(retail) > CAPACITY:
        raise ValueError('Retail unlock projection exceeds native capacity')
    output = bytearray(payload)
    struct.pack_into('<I', output, COUNT, len(retail))
    struct.pack_into(f'<{CAPACITY}I', output, KEYS, *(retail + [0xffffffff] * (CAPACITY - len(retail))))
    output = bytes(output)
    extension = {'schema': SCHEMA, 'ledger_sha256': fingerprint(ledger),
                 'settings_sha256': sha256(output).hexdigest(),
                 'marks': {key: value for key, value in sorted(marks.items()) if not key.startswith('retail/')}}
    return output, extension


def restore(payload, extension, ledger, baseline):
    """Require an exact coherent generation; never pair unrelated state files.

    Roster updates first restore with the old ledger, then project unchanged
    stable-key marks with the validated append-only new ledger. An extension's
    hashes detect mismatches; they are not an authenticity/signature claim.
    """
    settings_keys(payload)
    if not isinstance(extension, dict) or set(extension) != {'schema', 'ledger_sha256', 'settings_sha256', 'marks'}:
        raise ValueError('Invalid fighter unlock extension shape')
    if extension['schema'] != SCHEMA or extension['ledger_sha256'] != fingerprint(ledger) \
            or extension['settings_sha256'] != sha256(payload).hexdigest():
        raise ValueError('Fighter unlock extension belongs to a different save generation')
    result = read(payload, ledger, baseline)
    known = entries(ledger, baseline)
    validate_marks(extension['marks'], known)
    if any(key.startswith('retail/') for key in extension['marks']) or any(not key.startswith('retail/') for key in result):
        raise ValueError('Native/custom unlock projection has mixed ownership')
    result.update(extension['marks'])
    return result
