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

        count, tokens = None, None
        if names is not None:
            count, reserved = struct.unpack_from('<2I', names)
            body = names[8:]
            require(0 < count <= MAX_NAMES and reserved == 0 and body.endswith(b'.')
                    and body.count(b'.') == count, 'Animation name count/terminator differs')
            tokens = body[:-1].split(b'.')
            require(all(TOKEN.fullmatch(token) for token in tokens), 'Unsupported animation name token')
        self.model, self.bank, self.name_count = model, banks[0], count
        self.tokens = None if tokens is None else tuple(token.decode('ascii') for token in tokens)
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


class AnimationIndex:
    """Native E68E0 name lookup and type15 child edges, without curve admission.

    Only established fields are interpreted. Unknown curve types are reported,
    never considered executable or safe for the native evaluator by this reader.
    """
    def __init__(self, envelope):
        require(type(envelope) is AnimationEnvelope, 'Expected a validated animation envelope')
        self.envelope, self.model = envelope, envelope.model
        model = self.model
        root = model.export_offset(envelope.bank)
        words = model.data_words(root, 6)
        count = words[1]
        require(0 < count <= MAX_NAMES, 'Animation bank entry count exceeds budget')
        require(root + 4 not in model.pointers, 'Animation count cannot be relocated')
        records = model.local_pointer(root + 16, count * 4)
        names = model.local_pointer(root + 20, count * 4)
        self.names, self.records = [], []
        for i in range(count):
            self.records.append(model.local_pointer(records + i * 4, 2))
            name = model.local_pointer(names + i * 4, 1)
            begin = model.data_range(name, 1)
            end = model.data.find(b'\0', begin, min(begin + MAX_NAME + 3, model.sections[1][4] + model.sections[1][5]))
            require(end > begin, 'Animation bank name is empty, too long or unterminated')
            raw = model.data[begin:end]
            require(re.fullmatch(rb'[A-Za-z0-9_]{1,129}', raw), 'Unsupported animation bank name')
            self.names.append(raw.decode('ascii'))
        require(all(a < b for a, b in zip(self.names, self.names[1:])),
                'Animation bank names must be unique and sorted for native lookup')
        self.lookup = {name: i for i, name in enumerate(self.names)}
        self.token_links = None if envelope.tokens is None else tuple(
            (self.lookup.get(token + '_t', -1), self.lookup.get(token + '_s', -1))
            for token in envelope.tokens)
        self.record_types, self.children = {}, {}
        pending, edge_count = list(self.records), 0
        while pending:
            offset = pending.pop()
            if offset in self.record_types:
                continue
            require(len(self.record_types) < MAX_NAMES * 4, 'Animation record graph exceeds budget')
            at = model.data_range(offset, 2)
            require(offset not in model.pointers, 'Animation type cannot be relocated')
            kind, = model.unpack('<H', at)
            self.record_types[offset] = kind
            if kind == 15:
                at = model.data_range(offset, 12)
                child_count, = model.unpack('<H', at + 8)
                edge_count += child_count
                require(edge_count <= 1048576, 'Animation child edges exceed budget')
                require(offset + 8 not in model.pointers, 'Animation child count cannot be relocated')
                model.data_range(offset + 12, child_count * 4)
                children = tuple(model.local_pointer(offset + 12 + i * 4, 2) for i in range(child_count))
                self.children[offset] = children
                pending.extend(children)
        # Type15 wrappers recursively construct child wrappers. Shared children
        # are allowed; cycles are not. Iterative DFS avoids Python recursion limits.
        done, active = set(), set()
        for start in self.children:
            stack = [(start, False)]
            while stack:
                node, leaving = stack.pop()
                if leaving:
                    active.remove(node)
                    done.add(node)
                    continue
                if node in done:
                    continue
                require(node not in active, 'Cyclic animation child graph')
                active.add(node)
                stack.append((node, True))
                stack.extend((child, False) for child in self.children.get(node, ()))

    def metadata(self):
        from collections import Counter
        types = Counter(self.record_types.values())
        return {'named_entries': len(self.names), 'unique_records': len(self.record_types),
                'record_types': dict(sorted(types.items())),
                'type15_child_edges': sum(map(len, self.children.values())),
                'motion_tokens': None if self.token_links is None else len(self.token_links),
                'missing_t_links': None if self.token_links is None else sum(a < 0 for a, _ in self.token_links),
                'missing_s_links': None if self.token_links is None else sum(b < 0 for _, b in self.token_links),
                'name_index_validated': True, 'animation_records_validated': False,
                'event_links_validated': False, 'runtime_ready': False}
