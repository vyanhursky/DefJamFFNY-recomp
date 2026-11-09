"""Compose typed intro/victory bindings into the verified native cinematic list.

The combat path reads assets/nis.viv|assets/IntroExtro.xml. The loose taunt.xml
is not this list. Packs provide logical resources, never replacement XML.
Animation bank validation and runtime ownership are separate adapter gates.
"""
from dataclasses import dataclass
import hashlib
import xml.etree.ElementTree as ET

from fighter_assets import AssetError
from fighter_entity import native_name

MAX_BYTES = 4 * 1024**2
MAX_BINDINGS = 16384
TARGET = 'assets/nis.viv|assets/IntroExtro.xml'
CLOSE = b'</tauntslist>'


def require(condition, message):
    if not condition:
        raise AssetError(message)


@dataclass(frozen=True)
class Cinematic:
    name: str
    intro: str
    victory: str

    def xml(self):
        name, intro, victory = map(native_name, (self.name, self.intro, self.victory))
        return (f'\r\n\t<taunt>\r\n\t\t<name>{name}</name>\r\n'
                f'\t\t<intro>{intro}</intro>\r\n\t\t<extro>{victory}</extro>\r\n'
                '\t</taunt>\r\n').encode('ascii')


class Cinematics:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and 0 < len(data) <= MAX_BYTES, 'Cinematic list exceeds budget')
        require(isinstance(expected_sha256, str) and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Cinematic adapter requires a hash-verified baseline')
        require(data.count(CLOSE) == 1 and b'<!' not in data, 'Unsupported cinematic root envelope')
        try:
            root = ET.fromstring(data)
        except ET.ParseError as error:
            raise AssetError('Invalid cinematic baseline structure') from error
        require(root.tag == 'tauntslist' and not root.attrib and len(root) <= MAX_BINDINGS,
                'Unsupported cinematic list')
        self.bindings = {}
        for row in root:
            names = row.findall('name')
            require(row.tag == 'taunt' and not row.attrib and names
                    and all(child.tag in ('name', 'intro', 'extro') and not child.attrib
                            for child in row)
                    and all(not len(field) for field in names)
                    and len(row.findall('intro')) == len(row.findall('extro')) == 1,
                    'Ambiguous cinematic baseline row')
            # The original created-fighter row contains counted random variants.
            # Preserve and reserve it, but do not silently choose one for a new
            # fighter or advertise the still-unimplemented variant adapter.
            variants = any(len(row.find(tag)) for tag in ('intro', 'extro'))
            if variants:
                for tag in ('intro', 'extro'):
                    clip = row.find(tag)
                    count = clip.findtext('count')
                    choices = clip.findall('name')
                    require(count is not None and count.isascii() and count.isdecimal()
                            and len(clip.findall('count')) == 1 and 0 < int(count) == len(choices) <= 255
                            and all(c.tag in ('count', 'name') and not c.attrib and not len(c) for c in clip),
                            'Invalid cinematic baseline variants')
                    for choice in choices:
                        native_name(choice.text)
            else:
                intro, victory = native_name(row.findtext('intro')), native_name(row.findtext('extro'))
            for field in names:
                name = native_name(field.text)
                require(name.casefold() not in self.bindings, 'Duplicate cinematic baseline name')
                self.bindings[name.casefold()] = None if variants else Cinematic(name, intro, victory)
        require(len(self.bindings) <= MAX_BINDINGS, 'Cinematic population exceeds budget')
        self.data, self.end = data, data.index(CLOSE)

    def inherit(self, name, donor):
        native_name(name); native_name(donor)
        require(donor.casefold() in self.bindings, 'Appearance donor has no native intro/victory mapping')
        original = self.bindings[donor.casefold()]
        require(original is not None, 'Counted cinematic variants require a separate native adapter')
        return Cinematic(name, original.intro, original.victory)

    def compose(self, additions, available_banks):
        require(type(additions) in (list, tuple) and len(additions) + len(self.bindings) <= MAX_BINDINGS,
                'Cinematic composition population exceeds budget')
        require(all(type(row) is Cinematic for row in additions), 'Expected typed cinematic bindings')
        require(type(available_banks) in (set, frozenset) and all(isinstance(s, str) for s in available_banks),
                'Expected verified animation bank names')
        validated = [(row, row.xml()) for row in additions]
        names, encoded = set(self.bindings), []
        for row, entry in sorted(validated, key=lambda pair: pair[0].name):
            require(row.name.casefold() not in names, 'Cinematic name collides')
            require(row.intro in available_banks and row.victory in available_banks,
                    'Cinematic binding references a missing animation bank')
            names.add(row.name.casefold()); encoded.append(entry)
        result = self.data[:self.end] + b''.join(encoded) + self.data[self.end:]
        require(len(result) <= MAX_BYTES, 'Composed cinematic list exceeds budget')
        return result
