"""Compiler-only seals for freshly emitted cinematic members."""
import hashlib
import re
import struct

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_archive import Archive
from fighter_assets import unpack


def encode_film_proofs(archive_data,resources):
    """resources: assigned-token -> {graph, rig_sha256, bone_count, tags}."""
    archive=Archive(archive_data);records=[]
    version=2 if any(r.get('caf_profile')==1 for r in resources.values()) else 1
    for token,resource in sorted(resources.items()):
        require(re.fullmatch(r'(?:FI|FV)[0-9]{5}|B[0-9]{5}',token),'Invalid cinematic proof name')
        bundle=Archive(archive.read(token+'.viv'));hand_need=resource['hand_frames']
        for entry in bundle.entries:
            envelope=AnimationEnvelope.from_model(unpack(bundle.read(entry.name)))
            model=envelope.model;section=model.sections[1]
            payload=model.data[section[4]:section[4]+section[5]]
            relocations=sorted((field,row['target']) for field,row in model.pointers.items())
            suffix=entry.name[len(token):]
            role={'.o':1,'_f.o':2,'_h.o':3}.get(suffix,4)
            require(0<len(relocations)<=65536 and len(entry.name)<=31,'Cinematic proof exceeds bounds')
            data=struct.pack('<32s8I',entry.name.encode(),len(payload),model.export_offset(envelope.bank),
                len(relocations),resource['bone_count'],*hand_need,role,resource['tags'])
            data+=bytes.fromhex(resource['rig_sha256'])+hashlib.sha256(payload).digest()
            if version==2:
                caf=resource.get('caf_profile')==1
                rigs=resource.get('rig_sha256s',[resource['rig_sha256']])
                face=resource.get('face_frames',[0,0])
                require(len(rigs)==(2 if caf else 1) and rigs==sorted(set(rigs))
                        and rigs[0]==resource['rig_sha256'] and (not caf or resource['bone_count']==94),
                        'CAF film needs its two verified rig contexts')
                data+=struct.pack('<4I',int(caf),*face,len(rigs))+(bytes.fromhex(rigs[1]) if caf else bytes(32))
            data+=b''.join(struct.pack('<2I',*row) for row in relocations)
            records.append((entry.name,data))
    require(0<len(records)<=8192,'Cinematic proof population exceeds budget')
    result=(b'FCP2' if version==2 else b'FCP1')+struct.pack('<4I',version,len(records),len(archive_data),0)+hashlib.sha256(archive_data).digest()
    result+=b''.join(data for _,data in sorted(records))
    require(len(result)<=64*1024**2,'Cinematic proof bytes exceed budget')
    return result
