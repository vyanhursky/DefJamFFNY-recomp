"""CAF HD atlases: host-side RGB at 512..2048px, native compositor alpha and a 256px fallback.

The fallback lives in the extras section; this module writes the hd section that carries the full-resolution RGB.
"""
import hashlib
import struct
from fighter_resource_files import require
from fighter_caf_layout import HD as H, HD_STRIDE, HD_EDGES, HD_MAX_BYTES, HD_MAX_BLOCKS, ATLASES as ATLAS_SLOTS
from fighter_caf_extras import ATLASES


def encode_section(entries, report):
    """The hd section: rows, then the pixel blocks. Block offsets count from the section start.
    Returns (row count, bytes); (0, b'') when no outfit has HD atlases."""
    from fighter_caf_outfits import variants
    selected = [(key, index, outfit['extras']['hd_atlases'])
                for key, item in sorted(entries.items()) for index, outfit in enumerate(variants(item))
                if (outfit.get('extras') or {}).get('hd_atlases')]
    if not selected:
        return 0, b''
    base = len(selected) * HD_STRIDE
    blocks, offsets, rows, size = [], {}, [], base
    for key, index, atlases in selected:
        row = bytearray(HD_STRIDE)
        struct.pack_into('<II', row, H['selection'], report['bindings'][key]['selection_key'], index)
        for slot, name in enumerate(ATLASES):
            block = atlases.get(name)
            if block is None:
                continue
            require(type(block) is bytes and len(block) >= 4, 'Invalid HD CAF block')
            edge = struct.unpack_from('<I', block)[0]
            require(edge in HD_EDGES and len(block) == 4 + edge * edge * 4, 'Invalid HD CAF dimensions')
            digest = hashlib.sha256(block).digest()
            if digest not in offsets:
                require(size + len(block) <= HD_MAX_BYTES, 'HD CAF atlases exceed the 128 MiB compiled budget')
                require(len(blocks) < HD_MAX_BLOCKS, 'HD CAF atlases exceed the distinct block budget')
                offsets[digest] = size
                blocks.append(block)
                size += len(block)
            struct.pack_into('<I', row, H['atlases'] + 4 * slot, offsets[digest])
        rows.append(bytes(row))
    assert len(ATLASES) == ATLAS_SLOTS
    return len(rows), b''.join(rows) + b''.join(blocks)
