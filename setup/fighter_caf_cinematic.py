"""Bounded CAF donor cinematic reconstruction; controls remain original-owned."""
import copy
import struct
from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_curves import CurveLayouts
from fighter_animation_graphs import Writer, read_leaf, parent_profile
from fighter_animation_numeric import read_numeric, write_numeric
from fighter_animation_compile import rebuild
from fighter_animation_scalars import ScalarCurve
from fighter_animation_timed_quaternions import TimedQuaternionCurve
from fighter_animation_quaternions import QuaternionCurve
from fighter_animation_vectors import VectorCurve

FORMAT = 'fighter-caf-cinematic-1'


def validate(value):
    from fighter_caf_mouth import FORMAT as VOICE_FORMAT, DURATIONS, validate_mouth
    voice=type(value) is dict and value.get('format')==VOICE_FORMAT
    fields={'format','template','edits'}|({'mouth','speech_tick'} if voice else set())
    require(type(value) is dict and set(value)==fields
            and value['format'] in (FORMAT,VOICE_FORMAT)
            and type(value['template']) is str and value['template'] in (tuple(DURATIONS) if voice else ('CI_132A','CE_132A','CI_113A','CE_113A')),
            'CAF donor proof supports only the reviewed donor/profile')
    if voice:
        duration=DURATIONS[value['template']];validate_mouth(value['mouth'],duration)
        require(type(value['speech_tick']) is int and 0<=value['speech_tick']<duration,'Invalid speech onset')
    require(type(value['edits']) is list and len(value['edits'])<=16,'Too many facial cue edits')
    occupied=set()
    for edit in value['edits']:
        require(type(edit) is dict and set(edit)=={'selector','key','expected','sample'}
                and all(type(v) is int for v in edit.values()),'Cue edits require bounded integer fields')
        require(0<=edit['selector']<=1 and 0<=edit['key']<4096
                and 0<=edit['expected']<(13,15)[edit['selector']]
                and 0<=edit['sample']<(13,15)[edit['selector']], 'Cue exceeds CAF facial capacity')
        require(not voice or edit['selector']==0,'Voice authoring uses the dedicated lip track')
        key=(edit['selector'],edit['key'])
        require(key not in occupied,'Duplicate facial cue edit');occupied.add(key)
    return value


def compose(game,value,assigned):
    """No authored rig, pointers, envelope bytes or arbitrary curves are accepted."""
    import hashlib
    from pathlib import Path
    from fighter_workshop import original,pins
    from fighter_archive import Archive
    from fighter_assets import unpack
    from fighter_caf import output_contexts
    from fighter_face import FacePalettes,declared_capacities
    from fighter_elf import Model
    from fighter_rig import Skeleton
    from fighter_cinematic_compile import rename_bank
    validate(value);pin=pins();game=Path(game);token=value['template']
    contexts=output_contexts(game);rigs=sorted({Skeleton(Model(b)).pose_sha256 for b,_ in contexts.values()})
    require(len(rigs)==2 and all(len(Skeleton(Model(b)).rows)==94 for b,_ in contexts.values()),'Unproved CAF rig set')
    donor=Skeleton(Model(unpack(Archive(original(game,'assets/v2ip.viv',pin['v2ip_sha256'])).read('V2IP_'+token[3:]+'.o'))))
    require(all(Skeleton(Model(b)).topology_sha256==donor.topology_sha256 for b,_ in contexts.values()),
            'Donor bone names/parents differ from CAF topology')
    faces=[FacePalettes(Model(f),94,declared_capacities(Model(f))) for _,f in contexts.values()]
    hands=FacePalettes(Model(unpack(Archive(original(game,'assets/misc.viv',pin['misc_sha256'])).read('share_hp.o'))),94,(32,32))
    archive=Archive(original(game,'assets/v2ta.viv',pin['v2ta_sha256']))
    bundle=Archive(unpack(archive.read(token+'.viv')));replacements={};renames={};needs={}
    for entry in bundle.entries:
        raw=unpack(bundle.read(entry.name));_,_,graphs=parse(raw)
        role=('face' if entry.name==token+'_f.o' else 'hands' if entry.name==token+'_h.o'
              else 'body' if entry.name==token+'.o' else 'camera')
        if role=='face':
            for edit in value['edits']:
                leaf=graphs[token+'_p']['children'][edit['selector']]
                require(leaf['selector']==edit['selector'] and edit['key']<len(leaf['samples'])
                        and leaf['samples'][edit['key']]==edit['expected'],'Cue source no longer matches donor')
                leaf['samples'][edit['key']]=edit['sample']
        if role=='face' and 'mouth' in value:
            from fighter_caf_mouth import apply_graphs
            graphs=apply_graphs(graphs,value['mouth'],token)
        if role in ('face','hands'):
            leaves=graphs[token+'_p']['children'];require(len(leaves)==2,'Donor needs both palette selectors')
            needs[role]=[max(leaf['samples'])+1 for leaf in leaves]
            for ordinal,leaf in enumerate(leaves):
                require(leaf['selector']==ordinal,'Donor palette selectors differ')
                for palette in (faces if role=='face' else [hands]):palette.require_samples(ordinal,tuple(leaf['samples']))
        rebuilt=compile_member(raw,graphs,faces[0],hands,role=role,permit_face_samples=role=='face',
            mouth=value.get('mouth') if role=='face' else None,reference=unpack(bundle.read(token+'.o')) if role=='face' and 'mouth' in value else None)
        if role!='face' or not value['edits'] and 'mouth' not in value:compare_decoded(raw,rebuilt)
        replacements[entry.name]=rename_bank(rebuilt,token,assigned);renames[entry.name]=assigned+entry.name[len(token):]
    result=bundle.compose(replacements=replacements,renames=renames)
    return result,dict(schema=FORMAT,native_name=assigned,template=token,full_graph=True,caf_profile=1,
        rig_sha256=rigs[0],rig_sha256s=rigs,bone_count=94,face_frames=needs['face'],hand_frames=needs['hands'],
        members=len(replacements),construction_order='animation-bank-before-model',sha256=hashlib.sha256(result).hexdigest(),native_admission=False)

def bank_before_model(original):
    """Preserve the ELF local-symbol prefix and every export's data binding."""
    model=copy.copy(original)
    model.symbols=[row for row in original.symbols if row[3]>>4==0]+sorted(
        [row for row in original.symbols if row[3]>>4!=0],
        key=lambda row:0 if row[0].startswith('__AnimationBank:::') else 1)
    return model


def parse(data):
    index = AnimationIndex(AnimationEnvelope.from_model(data))
    layout = CurveLayouts(index)
    graphs = {}
    for name, parent in zip(index.names, index.records):
        _, _, duration, scale = parent_profile(layout, parent)
        graphs[name] = dict(duration_ticks=duration, time_scale=scale, children=[
            read_leaf(layout, child) if index.record_types[child] in (13, 25)
            else read_numeric(layout, child) for child in index.children[parent]])
    return index, layout, graphs


def type13(writer, leaf, control):
    """Generalize the existing helper-only writer to its pinned donor count."""
    count = len(leaf['coefficients'])
    require(count == 4 * len(leaf['destinations']) and count <= 4 * 94,
            'Donor scalar population escapes CAF context')
    bits = leaf['bits']
    require(bits in (4, 8, 16), 'Unproved scalar delta width')
    data = bytearray(struct.pack('<HBB', count, bits, 0))
    data.extend(b''.join(struct.pack('<3f', *row) for row in leaf['coefficients']))
    for row in leaf['deltas']:
        require(len(row) == count, 'Donor delta population differs')
        if bits == 4:
            data.extend(bytes(row[i] | row[i + 1] << 4 for i in range(0, count, 2)))
        else:
            data.extend(struct.pack('<' + ('B' if bits == 8 else 'H') * count, *row))
    descriptor = writer.append(data)
    stamps = writer.append(struct.pack('<' + 'H' * len(leaf['times']), *leaf['times']))
    record = writer.append(struct.pack('<HHIIHH', 13, control, 0, 0,
                                      len(leaf['deltas']) + 1, leaf['destinations'][0])
                           + struct.pack('<' + 'H' * (len(leaf['destinations']) - 1),
                                         *leaf['destinations'][1:]))
    writer.pointer(record + 4, descriptor)
    writer.pointer(record + 8, stamps)
    return record


def compile_member(template, document, face, hands, *, role, permit_face_samples=False, mouth=None, reference=None):
    index, layout, trusted = parse(template)
    # This bounded proof admits only original curves, plus face sample changes.
    # It does not accept new destinations, controls, key times or raw pointers.
    expected = copy.deepcopy(trusted)
    require(role in ('body', 'face', 'hands', 'camera'), 'Coordinator must supply a verified member role')
    facial = role == 'face'
    if permit_face_samples and facial:
        for name, graph in trusted.items():
            require(name in document and len(document[name]['children'])==len(graph['children']), 'Face parent shape differs')
            for i, leaf in enumerate(graph['children']):
                if mouth is not None and i==1:continue
                samples=document[name]['children'][i].get('samples')
                require(type(samples) is list and len(samples)==len(leaf['samples']), 'Sample population differs')
                expected[name]['children'][i]['samples']=samples
    if mouth is not None:
        from fighter_caf_mouth import apply_graphs
        require(facial and reference is not None,'Mouth needs a verified donor body control reference')
        token=next(iter(trusted))[:-2];expected=apply_graphs(expected,mouth,token)
    require(document == expected, 'Only verified donor data and explicitly permitted face samples are admitted')
    start, size = index.model.sections[1][4:6]
    payload = bytearray(index.model.data[start:start + size])
    writer = Writer(payload, {offset: pointer['target'] for offset, pointer in index.model.pointers.items()})
    palette = face if facial else hands
    camera = role == 'camera'
    records={}
    for name, graph in document.items():
        fresh_parent=name not in index.lookup
        if fresh_parent:
            ref_index,ref_layout,ref_graphs=parse(reference)
            require(name.endswith('_s') and name in ref_index.lookup and len(graph['children'])==1,
                    'Only the closed jaw root may be added')
            ref_parent=ref_index.records[ref_index.lookup[name]]
            parent_control,padding,duration,scale=parent_profile(ref_layout,ref_parent)
            require((duration,scale)==(graph['duration_ticks'],graph['time_scale']),'Jaw clock differs from donor')
            attributes=writer.append(struct.pack('<3I',1,65537,padding|scale))
            parent=writer.append(struct.pack('<HHIHHI',15,parent_control,0,1,duration,0))
            writer.pointer(parent+4,attributes)
            old_children=ref_index.children[ref_parent];controls=[ref_layout.values(old_children[0]+2,1)[0]]
        else:
            parent=index.records[index.lookup[name]];old_children=index.children[parent]
            controls=[layout.values(old+2,1)[0] for old in old_children]
        for ordinal,leaf in enumerate(graph['children']):
            control=controls[ordinal];kind=leaf['kind']
            if kind==13:
                require(all(type(d) is int and d%12==4 and d+4<=94*12 for d in leaf['destinations']),
                        'Type13 output destination differs from bone quaternion')
                fresh=type13(writer,leaf,control)
            elif kind==25:
                palette.require_samples(leaf['selector'],tuple(leaf['samples']))
                fresh=writer.leaf(leaf,control,layout.values(old_children[ordinal]+7,1,'B')[0])
            else:fresh=write_numeric(writer,leaf,control,64 if camera else 94*12)
            writer.pointer(parent+12+4*ordinal,fresh)
        records[name]=parent
    if set(document)!=set(trusted):
        names=sorted(document);bank=index.model.export_offset(index.envelope.bank)
        struct.pack_into('<I',payload,bank+4,len(names))
        table=writer.append(bytes(4*len(names)));labels=writer.append(bytes(4*len(names)))
        writer.pointer(bank+16,table);writer.pointer(bank+20,labels)
        for i,name in enumerate(names):
            writer.pointer(table+4*i,records[name]);writer.pointer(labels+4*i,writer.append(name.encode('ascii')+b'\0'))
    payload.extend(bytes(-len(payload) % 4))
    # 10AB10 constructs exports in ELF symbol order. Retail victory camera
    # __Model1122F0 stamps model+DC before a later AnimationBank constructor.
    # Seal the untouched complete payload first, retaining every original
    # Model/BBOX export and value; intro cameras already use this ordering.
    model=bank_before_model(index.model)
    result = b''.join(rebuild(model, payload, writer.pointers))
    _, _, actual = parse(result)
    require(actual == document, 'Rebuilt curves differ from typed document')
    return result


def compare_decoded(a, b):
    ia, la, ga = parse(a)
    ib, lb, gb = parse(b)
    require(ga == gb, 'Unchanged typed curves differ')
    checks = dict(key_scalar_values=0, interpolated_quaternions=0, palette_samples=0)
    for name in ia.names:
        pa, pb = ia.records[ia.lookup[name]], ib.records[ib.lookup[name]]
        for ca, cb in zip(ia.children[pa], ib.children[pb]):
            kind = ia.record_types[ca]
            if kind == 13:
                sa, sb = ScalarCurve(la, ca), ScalarCurve(lb, cb)
                for va, vb in zip(sa.poses(), sb.poses()):
                    require(va == vb, 'Decoded type13 key differs')
                    checks['key_scalar_values'] += len(va)
                qa, qb = TimedQuaternionCurve(la, ca), TimedQuaternionCurve(lb, cb)
                for t in [0., *[float(t) for t in qa.times], *[(a + b) / 2 for a, b in zip((0, *qa.times), qa.times)]]:
                    for precision in (24, 53):
                        require(qa.sample(t, precision_bits=precision) == qb.sample(t, precision_bits=precision),
                                'Interpolated type13 pose differs')
                        checks['interpolated_quaternions'] += len(qa.destinations)
            elif kind in (18, 20, 21):
                cls = QuaternionCurve if kind == 18 else VectorCurve
                qa, qb = cls(la, ca), cls(lb, cb)
                for key in range(la.records[ca]['keys']):
                    va, vb = qa.pose(key), qb.pose(key)
                    require(va == vb, 'Decoded numeric key differs')
                    checks['key_scalar_values'] += sum(len(row) for row in va)
            elif kind == 25:
                checks['palette_samples'] += la.records[ca]['keys']
    return checks
