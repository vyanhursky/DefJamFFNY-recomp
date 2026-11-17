#!/usr/bin/env python3
"""Custom Story clothing packs: list base items, export a starting point, validate, compile.

A clothing pack is an ordinary mod folder with ``clothing.json`` at its root.
Each item names a retail Clothing row of the player's own ``assets/djv2.sod``
as its *base*. The item reuses the base's mesh, fits and colour list and ships
its own textures, painted on the base textures' UV layout (docs/custom-clothing.md).
Nothing in a pack is executable and a pack never carries game files: the
compiler paints the author's PNGs into copies of the player's own textures.

How the game names an item's files (sub_0001FE70): the row's Type picks one
category (TYPE_CATEGORY), the row gives a model number and a texture-set code
("variant", e.g. ``A03``), and each colour has its own texture::

    assets/v2cp_N.viv         V2CP_<cat>_<model>_<variant>_<colour>.xsh   (the garment)
    screens/screens.viv       screens/shopThumbs/100/V2TN_<cat>_<model>_<variant>_<colour>[_t].big

A custom item copies its base row with a new variant code (``Z01``..``Z99``),
so the game builds new texture and thumbnail names that only this item uses.

The compiler writes ``<out>`` (normally ``<data>/cache/clothing``):

* ``items.txt``       -- one line per item for the game (src/patches/clothing.c);
* ``v2cp_N-add.viv``  -- files added to assets/v2cp_N.viv at start: each new texture goes
                        into the archive that holds its base's textures (the creator reads a
                        body part's files from one fixed archive, ``assets/v2cp_N.viv|<name>``),
                        and the parts catalogue (below) replaces both of its copies (_0, _3);
* ``screens-add.viv`` -- the new thumbnails, added to screens/screens.viv at start;
* ``receipt.json``    -- what was compiled, with hashes.
"""
import argparse
import os
import hashlib
import io
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fighter_archive import store  # noqa: E402
from fighter_assets import AssetError, unpack  # noqa: E402
from fighter_sod import Database, name_hash  # noqa: E402
from fighter_xsh import Textures  # noqa: E402

FORMAT = 'clothing-pack-1'
CAPABILITY = 'clothing-v1'
MANIFEST = 'clothing.json'
ITEMS_HEADER = 'clothing-items-1'
# Shared with src/patches/clothing.h (tests/unit/test_clothing_pack.py keeps them equal).
MAX_ITEMS_PER_PACK = 64
MAX_ITEMS = 256
MAX_NAME = 40
MAX_PRICE = 99999
VARIANT_LETTER = os.environ.get('CLOTHING_TEST_LETTER', 'Z')  # retail texture sets use A..L
# The game's Type -> category table (16 words at 0x002898D8, read by sub_0001FE70).
TYPE_CATEGORY = (111, 112, 113, 114, 115, 121, 122, 123, 131, 132, 133, 134, 141, 142, 143, 144)
ARCHIVES = ('v2cp_0.viv', 'v2cp_1.viv', 'v2cp_2.viv', 'v2cp_3.viv')
PARTS_ARCHIVES = ('v2cp_0.viv', 'v2cp_3.viv')   # both hold the same createplayer_parts.xml
THUMBS = 'screens/shopThumbs/100/'
ID_RE = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?')
AVAILABILITY = ('wardrobe', 'shop')


class ClothingError(ValueError):
    pass


def check(condition, message):
    if not condition:
        raise ClothingError(message)


class RetailArchive:
    """Read-only BIG directory of a retail archive.

    The retail v2cp_3.viv lists a few model names twice in different case, which
    the strict fighter composer refuses; the game finds the first, and so does this.
    """

    def __init__(self, data):
        check(data[:4] in (b'BIGF', b'BIG4') and len(data) >= 16, 'Not a BIG archive')
        count, header_end = struct.unpack_from('>II', data, 8)
        check(0 < count <= 100_000 and 16 <= header_end <= len(data), 'Invalid BIG directory')
        self.data, self.names, self.by_name, at = data, [], {}, 16
        for _ in range(count):
            check(at + 9 <= header_end, 'Truncated BIG directory')
            offset, size = struct.unpack_from('>II', data, at)
            end = data.find(b'\0', at + 8, min(header_end, at + 8 + 513))
            check(end > at + 8 and offset + size <= len(data), 'Invalid BIG entry')
            name = data[at + 8:end].decode('latin-1')
            self.names.append(name)
            self.by_name.setdefault(name.lower(), (offset, size))
            at = end + 1

    def has(self, name):
        return name.lower() in self.by_name

    def read(self, name):
        offset, size = self.by_name[name.lower()]
        return self.data[offset:offset + size]


def build_archive(members):
    """A BIGF archive of the given members, in name order (the game searches, it does not bisect)."""
    names = sorted(members)
    for n in names:
        check(n.isascii() and 0 < len(n) < 200 and '\0' not in n, 'Invalid archive member name')
    directory = 16 + sum(9 + len(n) for n in names)
    first = directory + 8
    first += -first % 128
    entries, payload = [], bytearray()
    for n in names:
        entries.append((first + len(payload), len(members[n]), n))
        payload += members[n]
        payload += bytes(-len(payload) % 128)
    out = bytearray(b'BIGF' + bytes(4) + struct.pack('>II', len(names), directory + 8))
    for offset, size, n in entries:
        out += struct.pack('>II', offset, size) + n.encode('ascii') + b'\0'
    out += b'L231\0\0\0\1'
    out += bytes(first - len(out))
    out += payload
    struct.pack_into('<I', out, 4, len(out))
    return bytes(out)


# ---- the player's own game data -------------------------------------------------------------

class Game:
    """Read-only view of the Clothing table, the garment archives and the thumbnails of one dump."""

    def __init__(self, game):
        self.root = Path(game)
        sod = self.root / 'assets' / 'djv2.sod'
        check(sod.is_file(), 'assets/djv2.sod is missing from the game folder')
        self.db = Database(sod.read_bytes())
        self.table = name_hash('Clothing')
        check(self.table in self.db._tables, 'The Clothing table is missing from djv2.sod')
        self._archives = None
        self._screens = None
        self.rows = self._rows()

    def _rows(self):
        db, w = self.db, self.db.word
        header = db.directory[self.table]
        primary = db.index(db.word(header + 4))
        ordered = db.index(primary.values[0][0], tagged=True)
        rows = {}
        for rank, (pointer,) in enumerate(ordered.values):
            name = db.symbol(w(pointer))
            check(name is not None, 'A Clothing row has no name')
            kind = w(pointer + 32)
            check(kind < len(TYPE_CATEGORY), 'Unknown clothing Type in ' + name)
            rows[name] = {'rank': rank, 'name': name, 'model': w(pointer + 4),
                          'variant': db.symbol(w(pointer + 8)), 'cost': w(pointer + 16),
                          'type': kind, 'category': TYPE_CATEGORY[kind], 'colours': w(w(pointer + 12))}
        return rows

    def archives(self):
        if self._archives is None:
            self._archives = []
            for name in ARCHIVES:
                path = self.root / 'assets' / name
                check(path.is_file(), 'assets/' + name + ' is missing from the game folder')
                self._archives.append(RetailArchive(path.read_bytes()))
        return self._archives

    def screens(self):
        if self._screens is None:
            path = self.root / 'screens' / 'screens.viv'
            check(path.is_file(), 'screens/screens.viv is missing from the game folder')
            self._screens = RetailArchive(path.read_bytes())
        return self._screens

    def parts(self):
        archive = self.archives()[ARCHIVES.index(PARTS_ARCHIVES[-1])]
        check(archive.has(PARTS), 'assets/' + PARTS_ARCHIVES[-1] + ' has no ' + PARTS)
        return unpack(archive.read(PARTS))

    def base(self, name):
        check(name in self.rows, f'Unknown base item "{name}" (python setup/clothing_pack.py list --game ... shows them)')
        return self.rows[name]

    def texture_name(self, row, colour, variant=None):
        return f'V2CP_{row["category"]}_{row["model"]:04d}_{variant or row["variant"]}_{colour:02d}.xsh'

    def thumb_stem(self, row, colour, variant=None):
        return f'V2TN_{row["category"]}_{row["model"]:04d}_{variant or row["variant"]}_{colour:02d}'

    def texture(self, row, colour):
        """(archive file name, unpacked bytes) of one of the base's textures."""
        name = self.texture_name(row, colour)
        for file, archive in zip(ARCHIVES, self.archives()):
            if archive.has(name):
                return file, unpack(archive.read(name))
        raise ClothingError('The game has no texture ' + name)

    def thumbs(self, row, colour):
        """{suffix: unpacked bytes} of the base's thumbnails for one colour ('' and '_t')."""
        found = {}
        for suffix in ('', '_t'):
            name = THUMBS + self.thumb_stem(row, colour) + suffix + '.big'
            if self.screens().has(name):
                found[suffix] = unpack(self.screens().read(name))
        return found

    def used_variants(self):
        used = set()
        pattern = re.compile(r'V2CP_(\d{3})_(\d{4})_([A-Z]\d\d)_\d\d\.xsh', re.I)
        for archive in self.archives():
            for name in archive.names:
                m = pattern.fullmatch(name)
                if m:
                    used.add((int(m.group(1)), int(m.group(2)), m.group(3).upper()))
        return used


# ---- the pack ------------------------------------------------------------------------------

def safe_relative(value):
    check(isinstance(value, str) and 0 < len(value) <= 200 and '\\' not in value and not value.startswith('/')
          and ':' not in value, 'Invalid file path in clothing.json')
    parts = value.split('/')
    check(all(p not in ('', '.', '..') for p in parts), 'Invalid file path in clothing.json')
    return parts


def load_manifest(folder):
    folder = Path(folder)
    path = folder / MANIFEST
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024 ** 2, 'Missing or oversized clothing.json')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ClothingError('clothing.json is not valid JSON: ' + str(error)) from error
    check(type(value) is dict and value.get('format') == FORMAT, 'clothing.json needs "format": "' + FORMAT + '"')
    check(set(value) <= {'format', 'name', 'items'}, 'clothing.json has an unknown top-level key')
    check(type(value.get('name', '')) is str and len(value.get('name', '')) <= 80, 'Pack name must be text')
    items = value.get('items')
    check(type(items) is list and 1 <= len(items) <= MAX_ITEMS_PER_PACK,
          f'clothing.json needs 1 to {MAX_ITEMS_PER_PACK} items')
    seen = set()
    for item in items:
        check(type(item) is dict and {'id', 'name', 'base', 'textures'} <= set(item)
              and set(item) <= {'id', 'name', 'base', 'textures', 'price', 'availability'},
              'Each item needs id, name, base and textures (optional: price, availability)')
        check(type(item['id']) is str and ID_RE.fullmatch(item['id']), 'Item id must be a short lowercase slug: ' + repr(item['id']))
        check(item['id'] not in seen, 'Duplicate item id ' + item['id'])
        seen.add(item['id'])
        name = item['name']
        check(type(name) is str and 0 < len(name) <= MAX_NAME and name.isprintable() and '\t' not in name,
              'Item name must be 1-40 printable characters')
        check(type(item['base']) is str and 0 < len(item['base']) <= 128 and '\t' not in item['base'], 'Invalid base for ' + item['id'])
        check(item.get('availability', 'wardrobe') in AVAILABILITY, 'availability must be "wardrobe" or "shop"')
        price = item.get('price', 0)
        check(type(price) is int and 0 <= price <= MAX_PRICE, 'price must be a whole number from 0 to 99999')
        textures = item['textures']
        check(type(textures) is dict and 0 < len(textures) <= 32, 'textures must map colour numbers ("01") to PNGs')
        for key, spec in textures.items():
            check(re.fullmatch(r'\d\d', key) and 1 <= int(key) <= 32, 'Texture keys are colour numbers like "01": ' + key)
            check(type(spec) is dict and set(spec) == {'path', 'sha256'} and type(spec['sha256']) is str
                  and re.fullmatch('[0-9a-f]{64}', spec['sha256']), 'Each texture needs path and sha256')
            safe_relative(spec['path'])
    return value


def receipt(folder):
    """Install-time check of a pack folder without the game: the manifest, its PNGs and nothing else.

    The base items and the PNG sizes are checked against the player's own game when the
    enabled packs are compiled (compile_packs).
    """
    folder = Path(folder)
    manifest = load_manifest(folder)
    referenced = {MANIFEST}
    for item in manifest['items']:
        for spec in item['textures'].values():
            png_bytes(folder, spec)
            referenced.add(spec['path'])
    extra = {'README.md', 'LICENSE.txt', 'CHANGELOG.md', 'preview.png'}
    for path in folder.rglob('*'):
        if path.is_file():
            relative = path.relative_to(folder).as_posix()
            check(relative in referenced or relative in extra,
                  f'{relative} is not part of the clothing pack (clothing.json lists every file it uses)')
    return {'capabilities': [CAPABILITY], 'texture_ids': [], 'wide_ids': [], 'category': 'clothing',
            'clothing_count': len(manifest['items'])}


def png_bytes(folder, spec):
    path = Path(folder).joinpath(*safe_relative(spec['path']))
    check(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024 ** 2, 'Missing PNG ' + spec['path'])
    raw = path.read_bytes()
    check(hashlib.sha256(raw).hexdigest() == spec['sha256'], 'PNG hash in clothing.json differs: ' + spec['path']
          + ' (run: python setup/clothing_pack.py rehash --pack <folder>)')
    return raw


def paint(native, raw):
    """One PNG painted into one native texture (1x, 2x or 4x its size).

    The texture keeps its format, size, palette size and the original alpha
    (the game's material channel); only colours change. Indexed textures are
    quantized separately for each alpha value, as the fighter painter does,
    and tolerate art with fewer colours than the palette holds.
    """
    from PIL import Image
    from fighter_appearance_authoring import morton, raster
    textures = Textures(native)
    check(len(textures.images) == 1, 'Clothing textures hold one image')
    tile = textures.images[0]
    check(tile['kind'] in (0x7b, 0x7d), 'This base texture format is not supported yet')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            check(image.format == 'PNG', 'Textures must be PNG files')
            picture = image.convert('RGB')
    except OSError as error:
        raise ClothingError('Unreadable PNG: ' + str(error)) from error
    width, height = tile['width'], tile['height']
    scale = picture.width // width
    check(scale in (1, 2, 4) and picture.size == (width * scale, height * scale),
          f'A texture PNG must be {width}x{height} (or 2x/4x that); this one is {picture.width}x{picture.height}')
    original = raster(textures, tile)
    picture = picture.resize((width, height), Image.Resampling.LANCZOS) if scale > 1 else picture
    flat = (lambda im: list(im.get_flattened_data())) if hasattr(picture, 'get_flattened_data') else (lambda im: list(im.getdata()))
    pixels = flat(picture)
    alpha = flat(original.getchannel('A'))
    output = bytearray(native)
    if tile['kind'] == 0x7b:
        budget = tile['palette_entries']
        groups = {}
        for i, a in enumerate(alpha):
            groups.setdefault(a, []).append(i)
        check(len(groups) <= budget, 'The base texture uses more alpha values than its palette holds')
        counts = {a: 1 for a in groups}
        for _ in range(budget - len(groups)):
            a = max(groups, key=lambda k: len(groups[k]) / counts[k])
            counts[a] += 1
        palette, indices, start = bytearray(budget * 4), bytearray(width * height), 0
        for a, positions in sorted(groups.items()):
            w = min(4096, len(positions))
            h = (len(positions) + w - 1) // w
            source = Image.new('RGB', (w, h))
            source.putdata([pixels[i] for i in positions] + [(0, 0, 0)] * (w * h - len(positions)))
            quantized = source.quantize(colors=counts[a], method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            colours = (quantized.getpalette() or [])[:counts[a] * 3]
            colours += [0] * (counts[a] * 3 - len(colours))
            q = quantized.tobytes()
            for n, position in enumerate(positions):
                indices[position] = start + min(q[n], counts[a] - 1)
            for i in range(counts[a]):
                r, g, b = colours[i * 3:i * 3 + 3]
                palette[(start + i) * 4:(start + i + 1) * 4] = bytes((b, g, r, a))
            start += counts[a]
        at = tile['palette_offset']
        output[at:at + len(palette)] = palette
        data = indices
        stride = 1
    else:
        data = bytearray()
        for (r, g, b), a in zip(pixels, alpha):
            data += bytes((b, g, r, a))
        stride = 4
    if tile['swizzled']:
        ordered = bytearray(len(data))
        for y in range(height):
            for x in range(width):
                s, d = (y * width + x) * stride, morton(x, y, width, height) * stride
                ordered[d:d + stride] = data[s:s + stride]
        data = ordered
    check(len(data) == tile['pixels_bytes'], 'Texture encoder changed the native size')
    output[tile['pixels_offset']:tile['pixels_offset'] + len(data)] = data
    result = bytes(output)
    check(Textures(result).controls == textures.controls, 'Texture encoder changed native controls')
    check(raster(Textures(result), Textures(result).images[0]).getchannel('A').tobytes() == original.getchannel('A').tobytes(),
          'Texture encoder changed the material alpha')
    return result


PARTS = 'createplayer_parts.xml'


def patched_parts(xml, entries):
    """The creator's parts catalogue with each item's texture set listed under its base mesh.

    The catalogue lists, for every mesh (``<model>``), its texture sets (``<texture>``, the
    first colour's name) with the further colours (``<colour>``); the creator only builds a
    texture it finds there. An item's set goes after the base's own sets, in the same layout.
    """
    text = xml.decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    for entry in entries:
        base, variant = entry['base'], entry['variant']
        stem = f'V2CP_{base["category"]}_{base["model"]:04d}_'
        first = f'<name>{stem}{base["variant"]}_01</name>'
        hits = 0
        at = 0
        while True:
            start = text.find('<model>', at)
            if start < 0:
                break
            end = text.find('</model>', start)
            check(end > start, 'Unreadable createplayer_parts.xml')
            block = text[start:end]
            if f'<name>{stem}' in block and first in block:
                indent = '\t\t\t\t'
                lines = [indent + '<texture>', indent + f'\t<name>{stem}{variant}_01</name>']
                if base['colours'] > 1:
                    lines.append(indent + f'\t<count>{base["colours"] - 1}</count>')
                    for colour in range(2, base['colours'] + 1):
                        lines += [indent + '\t<colour>', indent + f'\t\t<name>{stem}{variant}_{colour:02d}</name>',
                                  indent + '\t</colour>']
                lines.append(indent + '</texture>')
                count = re.search(r'<count>(\d+)</count>', block)
                check(count is not None, 'A mesh in createplayer_parts.xml has no texture count')
                block = block[:count.start(1)] + str(int(count.group(1)) + 1) + block[count.end(1):]
                block = block.rstrip('\t') + newline.join(lines) + newline + '\t\t\t'
                text = text[:start] + block + text[end:]
                hits += 1
                at = start + len(block) + len('</model>')
            else:
                at = end + len('</model>')
        check(hits, f'{base["name"]}: its mesh is not in createplayer_parts.xml')
    return text.encode('utf-8')


def renamed_thumb(data, old, new):
    """A thumbnail (a small archive whose members carry its own name) under a new name of the same length."""
    check(len(old) == len(new), 'Thumbnail names must keep their length')
    check(data.count(old.encode()) >= 1, 'Thumbnail does not carry its own name')
    return data.replace(old.encode(), new.encode())


# ---- compile -------------------------------------------------------------------------------

def plan(game, packs):
    """Every enabled pack's items with their variant codes, in a deterministic order."""
    items, taken = [], {}
    used = game.used_variants()
    folders = sorted((Path(p) for p in packs), key=lambda p: p.name.lower())
    check(len({p.name.lower() for p in folders}) == len(folders), 'Two enabled packs share a folder name')
    for folder in folders:
        manifest = load_manifest(folder)
        for item in manifest['items']:
            base = game.base(item['base'])
            check(len(base['variant']) == 3, f'{item["base"]} has an unusual texture-set code')
            for key in item['textures']:
                check(int(key) <= base['colours'], f'{item["id"]}: {item["base"]} has colours 01-{base["colours"]:02d}')
            slot = (base['category'], base['model'])
            n = taken.get(slot, 0)
            while True:
                n += 1
                check(n <= 99, 'More than 99 custom items on one retail mesh')
                variant = f'{VARIANT_LETTER}{n:02d}'
                if (slot[0], slot[1], variant) not in used:
                    break
            taken[slot] = n
            items.append({'folder': folder, 'item': item, 'base': base, 'variant': variant,
                          'key': folder.name.lower() + '/' + item['id']})
    check(len(items) <= MAX_ITEMS, f'At most {MAX_ITEMS} custom clothing items can be enabled together')
    return items


def compile_items(game, items):
    garments, thumbs, lines = {file: {} for file in ARCHIVES}, {}, [ITEMS_HEADER]
    for entry in items:
        base, item, variant = entry['base'], entry['item'], entry['variant']
        for colour in range(1, base['colours'] + 1):
            file, native = game.texture(base, colour)
            key = f'{colour:02d}'
            data = paint(native, png_bytes(entry['folder'], item['textures'][key])) if key in item['textures'] else native
            garments[file][game.texture_name(base, colour, variant)] = store(data)
            old, new = game.thumb_stem(base, colour), game.thumb_stem(base, colour, variant)
            for suffix, thumb in game.thumbs(base, colour).items():
                thumbs[THUMBS + new + suffix + '.big'] = store(renamed_thumb(thumb, old + suffix, new + suffix))
        fields = [entry['key'], base['name'], variant, str(base['colours']), str(item.get('price', base['cost'])),
                  item.get('availability', 'wardrobe'), item['name']]
        lines.append('\t'.join(fields))
    if items:
        parts = store(patched_parts(game.parts(), items))
        for file in PARTS_ARCHIVES:
            garments[file][PARTS] = parts
    return garments, thumbs, '\n'.join(lines) + '\n'


def write_atomic(path, data):
    part = path.with_name(path.name + '.part')
    part.write_bytes(data)
    part.replace(path)


def compile_packs(game_dir, packs, output):
    output = Path(output)
    game = Game(game_dir)
    items = plan(game, packs)
    garments, thumbs, listing = compile_items(game, items)
    output.mkdir(parents=True, exist_ok=True)
    files = {'items.txt': listing.encode('utf-8'), 'screens-add.viv': build_archive(thumbs) if thumbs else b''}
    for file, members in garments.items():
        files[file.replace('.viv', '-add.viv')] = build_archive(members) if members else b''
    for name, data in files.items():
        write_atomic(output / name, data)
    receipt = {'format': 'clothing-cache-1', 'items': [i['key'] for i in items],
               'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    write_atomic(output / 'receipt.json', (json.dumps(receipt, indent=1) + '\n').encode('utf-8'))
    return receipt


# ---- export: a starting point for authors -----------------------------------------------------

def export(game_dir, base_name, pack, item_id, display):
    from fighter_appearance_authoring import raster
    game = Game(game_dir)
    base = game.base(base_name)
    pack = Path(pack)
    (pack / item_id).mkdir(parents=True, exist_ok=True)
    textures = {}
    for colour in range(1, base['colours'] + 1):
        native = Textures(game.texture(base, colour)[1])
        buffer = io.BytesIO()
        raster(native, native.images[0]).convert('RGB').save(buffer, format='PNG')
        raw = buffer.getvalue()
        relative = f'{item_id}/{colour:02d}.png'
        (pack / relative).write_bytes(raw)
        textures[f'{colour:02d}'] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
    return {'id': item_id, 'name': display, 'base': base_name, 'price': base['cost'],
            'availability': 'wardrobe', 'textures': textures}


def rehash(folder):
    """Refresh every texture sha256 in clothing.json after editing the PNGs."""
    folder = Path(folder)
    value = json.loads((folder / MANIFEST).read_text(encoding='utf-8'))
    for item in value['items']:
        for spec in item['textures'].values():
            spec['sha256'] = hashlib.sha256(folder.joinpath(*safe_relative(spec['path'])).read_bytes()).hexdigest()
    (folder / MANIFEST).write_text(json.dumps(value, indent=1) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('list', help='list the retail Clothing rows (the base item names)')
    p.add_argument('--game', required=True)
    p = sub.add_parser('export', help='start a pack item from a retail base item (writes its textures as PNGs)')
    p.add_argument('--game', required=True)
    p.add_argument('--base', required=True)
    p.add_argument('--pack', required=True, help='pack folder (clothing.json is created or extended)')
    p.add_argument('--id', required=True)
    p.add_argument('--name', required=True)
    p = sub.add_parser('rehash', help='update texture hashes after editing PNGs')
    p.add_argument('--pack', required=True)
    p = sub.add_parser('validate')
    p.add_argument('--game', required=True)
    p.add_argument('packs', nargs='+')
    p = sub.add_parser('compile')
    p.add_argument('--game', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('packs', nargs='*')
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            game = Game(args.game)
            for row in sorted(game.rows.values(), key=lambda r: (r['type'], r['name'])):
                print(f'{row["type"]:2d}  {row["name"]}  (${row["cost"]}, {row["colours"]} colour(s), '
                      f'V2CP_{row["category"]}_{row["model"]:04d}_{row["variant"]})')
        elif args.command == 'export':
            pack = Path(args.pack)
            pack.mkdir(parents=True, exist_ok=True)
            path = pack / MANIFEST
            value = (json.loads(path.read_text(encoding='utf-8')) if path.is_file()
                     else {'format': FORMAT, 'name': pack.name, 'items': []})
            check(all(i['id'] != args.id for i in value['items']), 'That id is already in the pack')
            value['items'].append(export(args.game, args.base, pack, args.id, args.name))
            path.write_text(json.dumps(value, indent=1) + '\n', encoding='utf-8')
            print('Exported', args.base, 'to', pack)
        elif args.command == 'rehash':
            rehash(args.pack)
        elif args.command == 'validate':
            game = Game(args.game)
            for i in plan(game, args.packs):
                print(i['key'], '<-', i['base']['name'], i['variant'])
        elif args.command == 'compile':
            print(json.dumps(compile_packs(args.game, args.packs, args.out), indent=1))
    except (ClothingError, AssetError, OSError, KeyError) as error:
        print('error:', error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
