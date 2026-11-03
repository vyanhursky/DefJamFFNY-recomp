"""Inspect split native animation-bank envelopes without activating them.

Native .ord/.orl resources reconstruct one relocatable, data-only ELF envelope.
The .mnl is a separate counted list of animation tokens. Their internal curve,
pose, event and name-to-record relationships remain separate validation gates.
"""
import hashlib
import re
import struct

from fighter_assets import AssetError
from fighter_elf import Model, MAX_BYTES

MAX_NAMES = 65535
MAX_NAME = 127
MAX_NAME_BYTES = 8 + MAX_NAMES * (MAX_NAME + 1)
TOKEN = re.compile(rb'[A-Za-z0-9_]{1,127}')


def require(condition, message):
    if not condition:
        raise AssetError(message)


class AnimationEnvelope:
    def __init__(self, data, links, names=None):
        parts = (data, links) if names is None else (data, links, names)
        require(all(isinstance(part, bytes) for part in parts), 'Animation resources must be bytes')
        require(len(data) >= 64 and links and len(data) + len(links) <= MAX_BYTES,
                'Animation ELF pair exceeds its byte budget')
        if names is not None:
            require(8 <= len(names) <= MAX_NAME_BYTES, 'Animation name list exceeds its byte budget')
        model = Model(data + links)
        sections_at, = model.unpack('<I', 32)
        require(model.sections[1][4] + model.sections[1][5] == len(data)
                and model.sections[2][4] == len(data)
                and all(row[4] >= len(data) and row[4] + row[5] <= sections_at for row in model.sections[2:])
                and sections_at + 6 * 40 == len(data) + len(links),
                'Animation data/link boundary differs from the native split layout')
        model.require_imports(())
        banks = [name for name in model.exports if name.startswith('__AnimationBank:::')]
        require(len(banks) == 1 and banks[0] != '__AnimationBank:::', 'Animation envelope needs one bank export')

        count = None
        if names is not None:
            count, reserved = struct.unpack_from('<2I', names)
            body = names[8:]
            require(0 < count <= MAX_NAMES and reserved == 0 and body.endswith(b'.')
                    and body.count(b'.') == count, 'Animation name count/terminator differs')
            tokens = body[:-1].split(b'.')
            require(all(TOKEN.fullmatch(token) for token in tokens), 'Unsupported animation name token')
        self.model, self.bank, self.name_count = model, banks[0], count
        self.hashes = {key: hashlib.sha256(part).hexdigest()
                       for key, part in (('data', data), ('links', links), ('names', names)) if part is not None}

    def metadata(self):
        return {'format': 'fighter-animation-envelope-draft-1', 'bank_export': self.bank,
                'combined_sha256': hashlib.sha256(self.model.data).hexdigest(),
                'decoded_sha256': self.hashes, 'bytes': len(self.model.data),
                'name_count': self.name_count, 'symbol_count': len(self.model.symbols),
                'relocation_count': self.model.relocations,
                'animation_records_validated': False, 'motion_name_links_validated': False,
                'event_links_validated': False, 'runtime_ready': False}
