"""CAF v7: host-side HD RGB, native compositor alpha and 256px fallback."""
import hashlib
import struct
from fighter_resource_files import require
from fighter_caf_extras import ATLASES

MAX_BYTES = 128*1024**2
ROW = 32


def encode(entries, report):
    from fighter_caf_outfits import variants
    selected = [(key,index,outfit['extras']['hd_atlases'])
                for key,item in sorted(entries.items()) for index,outfit in enumerate(variants(item))
                if (outfit.get('extras') or {}).get('hd_atlases')]
    if not selected:return None
    base=16+len(selected)*ROW
    blocks=[];offsets={};rows=[];size=base
    for key,index,atlases in selected:
        row=[report['bindings'][key]['selection_key'],index]
        for slot in ATLASES:
            block=atlases.get(slot)
            if block is None:row.append(0);continue
            require(type(block) is bytes and len(block)>=4,'Invalid HD CAF block')
            edge=struct.unpack_from('<I',block)[0]
            require(edge in (512,1024,2048) and len(block)==4+edge*edge*4,'Invalid HD CAF dimensions')
            digest=hashlib.sha256(block).digest()
            if digest not in offsets:
                require(size+len(block)<=MAX_BYTES,'HD CAF atlases exceed the 128 MiB compiled budget')
                offsets[digest]=size;blocks.append(block);size+=len(block)
            row.append(offsets[digest])
        rows.append(struct.pack('<8I',*row))
    return struct.pack('<4sIII',b'FCH1',1,len(rows),ROW)+b''.join(rows)+b''.join(blocks)
