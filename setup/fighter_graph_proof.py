"""Compiler-owned relocation and output proofs for the five-role graph profile.

These records are generated after typed compilation. They are never accepted
as creator source. The native provider verifies the entire relocated payload
before admitting the broader graph and rechecks actual actor resources at use.
"""
import hashlib
import re
import struct

from fighter_animation import AnimationIndex, require
from fighter_animation_graphs import ROLES, read_motion

MAX_PROOFS = 8192
MAX_RIGS = 512
MAX_RELOCATIONS = 65536
MAX_PROOF_BYTES = 64 * 1024**2


def payload_proof(envelope,token):
    index,model=AnimationIndex(envelope),envelope.model
    section=model.sections[1]
    payload=model.data[section[4]:section[4]+section[5]]
    require(0 < len(model.pointers) <= MAX_RELOCATIONS
            and all(not row['imported'] for row in model.pointers.values()),
            'Graph proof requires bounded local relocations')
    return {'schema':'fighter-graph-proof-1','data_bytes':len(payload),
            'bank_offset':model.export_offset(envelope.bank),
            'data_sha256':hashlib.sha256(payload).hexdigest(),
            'parents':[index.records[index.lookup[token+suffix]] for suffix in ('_s','_t')]+[0]*3,
            'relocations':[[field,row['target']] for field,row in sorted(model.pointers.items())],
            'bone_count':0,'allowed_rigs':[],'face_frames':[0,0],'hand_frames':[0,0]}


def graph_proof(envelope, token, rig_sha256, bone_count, allowed_rigs):
    index,model = AnimationIndex(envelope),envelope.model
    value = read_motion(index,token,rig_sha256,bone_count)
    require(type(allowed_rigs) in (list,tuple) and 0 < len(allowed_rigs) <= MAX_RIGS
            and len(set(allowed_rigs))==len(allowed_rigs)
            and all(type(s) is str and re.fullmatch('[0-9a-f]{64}',s) for s in allowed_rigs),
            'Graph requires explicit verified actor skeleton identities')
    requirements = {}
    for role in ('face','hands'):
        requirements[role] = [max(leaf['samples'])+1 for leaf in value['graphs'][role]['children']]
    return {**payload_proof(envelope,token),
            'parents':[index.records[index.lookup[token+suffix]] for suffix in ROLES.values()],
            'relocations':[[field,row['target']] for field,row in sorted(model.pointers.items())],
            'bone_count':bone_count,'allowed_rigs':sorted(allowed_rigs),
            'face_frames':requirements['face'],'hand_frames':requirements['hands']}


def encode_graph_proofs(proofs):
    require(type(proofs) is dict and 0 < len(proofs) <= MAX_PROOFS,'Invalid graph proof population')
    output=bytearray(b'FGP1'+struct.pack('<2I',1,len(proofs)))
    for ordinal,proof in sorted(proofs.items()):
        require(type(ordinal) is int and 873 <= ordinal < 873+MAX_PROOFS,'Invalid graph ordinal')
        require(proof['schema']=='fighter-graph-proof-1','Unsupported graph proof')
        relocations,rigs=proof['relocations'],proof['allowed_rigs']
        output.extend(struct.pack('<15I',ordinal,proof['data_bytes'],proof['bank_offset'],len(relocations),
                                  *proof['parents'],*proof['face_frames'],*proof['hand_frames'],
                                  proof['bone_count'],len(rigs)))
        output.extend(bytes.fromhex(proof['data_sha256']))
        output.extend(b''.join(struct.pack('<2I',*row) for row in relocations))
        output.extend(b''.join(bytes.fromhex(rig) for rig in rigs))
        require(len(output)<=MAX_PROOF_BYTES,'Graph proof byte budget exceeded')
    return bytes(output)
