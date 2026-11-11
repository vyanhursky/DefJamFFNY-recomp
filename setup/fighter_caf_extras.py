"""CAF extras: explicit retail finisher identities and native-size RGB atlases."""
import hashlib
import io
from pathlib import Path
import re
import struct

from fighter_resource_files import require
from mods import ordinary_path, safe_relative

ATLASES = ('a', 'b', 'c', 'd', 'd1', 'd2')
PIXELS = 256 * 256 * 4
MAX_BYTES = 16 * 1024 * 1024
FINISHER_TABLE = 0x47D305FD
FINISHER_CHOICE = 0x6FC83815


def finishers(values, database):
    require(type(values) is list and len(values) == 4 and all(type(v) is str and re.fullmatch('[0-9a-f]{8}', v) for v in values),
            'CAF needs four retail finisher record identities')
    require(database.schema.get(FINISHER_TABLE ^ FINISHER_CHOICE) == (4, 2), 'Unsupported CAF finisher choice schema')
    database.table(FINISHER_TABLE)  # Validate all native indexes before joining.
    member = database.index(database.directory[FINISHER_TABLE] + 16)
    indexes = dict(zip(member.keys, member.values))
    primary = database.index(indexes[FINISHER_TABLE][0], tagged=True)
    rows = dict(zip(primary.keys, (v[0] for v in primary.values)))
    result = []
    for value in values:
        ident = int(value, 16)
        require(ident in rows, 'CAF finisher is absent from the original SOD')
        choice = database.word(rows[ident] + 16)
        require(choice < 82, 'CAF finisher exceeds inherited paired resources')
        result.append(choice)
    return result


def load(root, value, database):
    require(set(value) <= {'stats', 'styles', 'caf_values', 'caf_colors', 'finishers', 'atlases'}, 'Unknown CAF field')
    result = {'finishers': finishers(value['finishers'], database) if 'finishers' in value else None, 'atlases': {}}
    atlases = value.get('atlases', {})
    require(type(atlases) is dict and set(atlases) <= set(ATLASES), 'Unsupported CAF atlas slot')
    root = ordinary_path(Path(root))
    if atlases:
        from PIL import Image
    for name, descriptor in atlases.items():
        require(type(descriptor) is dict and set(descriptor) == {'path', 'sha256'}, 'Invalid CAF atlas descriptor')
        require(type(descriptor['sha256']) is str and re.fullmatch('[0-9a-f]{64}', descriptor['sha256']), 'CAF atlas needs SHA-256')
        path = ordinary_path(root.joinpath(*safe_relative(descriptor['path'])))
        require(path.is_relative_to(root), 'CAF atlas leaves its package')
        with path.open('rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        require(len(raw) <= 1024 * 1024 and hashlib.sha256(raw).hexdigest() == descriptor['sha256'], 'CAF atlas hash/size differs')
        with Image.open(io.BytesIO(raw)) as image:
            require(image.format == 'PNG' and image.size == (256, 256), 'CAF atlases must be native 256x256 PNGs')
            image.load()
            result['atlases'][name] = image.convert('RGBA').tobytes('raw', 'BGRA')
    return result


def encode_section(entries, report):
    """The extras section: rows, then the atlas blocks. Atlas offsets count from the section start.
    Returns (row count, bytes); (0, b'') when no fighter has finishers or atlases."""
    from fighter_caf_outfits import variants
    from fighter_caf_layout import EXTRA as E, EXTRA_STRIDE, FINISHERS, ATLASES as ATLAS_SLOTS, ATLAS_BYTES
    selected = [(key, index, outfit['extras']) for key, item in sorted(entries.items())
                for index, outfit in enumerate(variants(item))
                if outfit.get('extras') and (outfit['extras']['finishers'] is not None or outfit['extras']['atlases'])]
    if not selected:
        return 0, b''
    base = len(selected) * EXTRA_STRIDE
    blocks, offsets, rows = [], {}, []
    for key, index, extras in selected:
        atlas_offsets = []
        for name in ATLASES:
            pixels = extras['atlases'].get(name)
            if pixels is None:
                atlas_offsets.append(0)
                continue
            require(type(pixels) is bytes and len(pixels) == PIXELS, 'Invalid compiled CAF atlas')
            digest = hashlib.sha256(pixels).hexdigest()
            if digest not in offsets:
                offsets[digest] = base + len(blocks) * PIXELS
                blocks.append(pixels)
            atlas_offsets.append(offsets[digest])
        choices = extras['finishers']
        row = bytearray(EXTRA_STRIDE)
        struct.pack_into('<I', row, E['selection'], report['bindings'][key]['selection_key'])
        struct.pack_into('<I', row, E['has_finishers'], int(choices is not None))
        struct.pack_into('<%dI' % FINISHERS, row, E['finishers'], *(choices if choices is not None else [0] * FINISHERS))
        struct.pack_into('<%dI' % ATLAS_SLOTS, row, E['atlases'], *atlas_offsets)
        struct.pack_into('<I', row, E['outfit'], index)
        rows.append(bytes(row))
    raw = b''.join(rows) + b''.join(blocks)
    require(len(raw) <= MAX_BYTES, 'Compiled CAF extras exceed the 16 MiB budget')
    return len(rows), raw
