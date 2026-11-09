"""Compose native model registrations from typed, runtime-owned declarations.

The native model manager resolves an entity name before loading its model and
textures. Merely adding files to v2ip.viv does not register that entity. Pack XML
is never accepted: preserve a hash-verified baseline and emit only this bounded
single-model form. Validation of the referenced model/texture bytes is separate.
"""
from dataclasses import dataclass
import hashlib
import re
import xml.etree.ElementTree as ET

from fighter_assets import AssetError
from fighter_sod import name_hash

MAX_BYTES = 4 * 1024**2
MAX_ENTITIES = 16384
NATIVE_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,30}\Z')
CLOSE = b'</entitylist>'


def require(condition, message):
    if not condition:
        raise AssetError(message)


def native_name(name):
    require(isinstance(name, str) and NATIVE_NAME.fullmatch(name), 'Invalid native appearance resource name')
    return name


@dataclass(frozen=True)
class Entity:
    name: str
    model: str
    texture: str

    def xml(self):
        name, model, texture = map(native_name, (self.name, self.model, self.texture))
        return (f'\r\n\t<entity><name>{name}</name><model><name>{model}</name>'
                f'<texture><name>{texture}</name></texture></model></entity>\r\n').encode('ascii')


class Entities:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and 0 < len(data) <= MAX_BYTES, 'Entity file exceeds budget')
        require(isinstance(expected_sha256, str) and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Entity adapter requires a hash-verified baseline')
        require(data.count(CLOSE) == 1, 'Unsupported entity root envelope')
        end = data.index(CLOSE)
        # The supported retail file contains non-XML processing instructions
        # and an unused example after its root. Only normalize a reading view;
        # preserve every original byte, including that tail, in the output.
        view = re.sub(br'<\?.*?\?>', b'', data[:end + len(CLOSE)], flags=re.S)
        require(b'<!' not in view, 'Entity declarations/DTD are unsupported')
        try:
            root = ET.fromstring(view)
        except ET.ParseError as error:
            raise AssetError('Invalid entity baseline structure') from error
        require(root.tag == 'entitylist' and not root.attrib and len(root) <= MAX_ENTITIES,
                'Unsupported entity list')
        names = []
        for element in root:
            fields = element.findall('name')
            require(element.tag == 'entity' and len(fields) == 1 and fields[0].text,
                    'Entity has no unambiguous name')
            name = fields[0].text
            require(name.isascii() and '\0' not in name, 'Unsupported baseline entity name')
            names.append(name)
        self.data, self.end, self.names = data, end, tuple(names)

    def compose(self, additions):
        require(type(additions) in (list, tuple) and len(additions) + len(self.names) <= MAX_ENTITIES,
                'Entity composition population exceeds budget')
        require(all(type(entity) is Entity for entity in additions), 'Expected typed appearance entities')
        names, hashes = {name.casefold() for name in self.names}, {name_hash(name) for name in self.names}
        validated = [(entity, entity.xml()) for entity in additions]
        encoded = []
        for entity, entry in sorted(validated, key=lambda pair: pair[0].name):
            digest = name_hash(entity.name)
            require(entity.name.casefold() not in names and digest not in hashes,
                    'Appearance entity name or native hash collides')
            names.add(entity.name.casefold()); hashes.add(digest)
            encoded.append(entry)
        result = self.data[:self.end] + b''.join(encoded) + self.data[self.end:]
        require(len(result) <= MAX_BYTES, 'Composed entity file exceeds budget')
        return result
