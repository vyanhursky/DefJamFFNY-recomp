"""Fresh, lossless cinematic graphs; offline reconstruction, not native admission.

Only the verified original archive supplies native control profiles and ELF
envelopes. Documents contain numeric curves, parent timing and palette indices.
Every name, pointer, wrapper, table and relocation is emitted from scratch.
"""
import copy
import hashlib
import re
import struct
import math

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_compile import rebuild
from fighter_animation_curves import CurveLayouts
from fighter_animation_graphs import Writer, fields, integer, array, read_leaf, parent_profile, times
from fighter_animation_numeric import read_numeric, validate_numeric, write_numeric
from fighter_animation_quaternions import QuaternionCurve
from fighter_animation_vectors import VectorCurve
from fighter_archive import Archive
from fighter_assets import unpack, AssetError
from fighter_face import FacePalettes

FORMAT='fighter-cinematic-graph-1'


def record_token(token):
    match=re.search(r'([12]?)_(EYE|TARGET)$',token)
    return 'CAM_'+match[2]+('p'+match[1] if match[1] else '') if match else token


def member_roles(token):
    return {'.o':{'rotation':'_s','position':'_t'},'_f.o':{'pose':'_p'},'_h.o':{'pose':'_p'},
            **({s+'.o':{'rotation':'_s','position':'_t'} for s in
                ('1_EYE','1_TARGET','2_EYE','2_TARGET') if token.startswith('CI_')}
               if token.startswith('CI_') else
               {s+'.o':{'rotation':'_s','position':'_t'} for s in ('_EYE','_TARGET')})}


def read_member(data,token,roles):
    index=AnimationIndex(AnimationEnvelope.from_model(data));layout=CurveLayouts(index)
    token=record_token(token)
    require(set(index.names)=={token+suffix for suffix in roles.values()},'Unexpected cinematic graph names')
    result={}
    for role,suffix in roles.items():
        parent=index.records[index.lookup[token+suffix]]
        _,_,duration,scale=parent_profile(layout,parent)
        children=[read_leaf(layout,c) if index.record_types[c]==25 else read_numeric(layout,c)
                  for c in index.children[parent]]
        result[role]={'duration_ticks':duration,'time_scale':scale,'children':children}
    return result


def read_cinematic(data,token,rig_sha256,bone_count):
    archive=Archive(data);roles=member_roles(token)
    require({e.name for e in archive.entries}=={token+s for s in roles},'Unexpected cinematic bundle members')
    return {'format':FORMAT,'rig_sha256':rig_sha256,'bone_count':bone_count,
            'layout':'intro' if token.startswith('CI_') else 'single-camera',
            'members':{suffix:read_member(unpack(archive.read(token+suffix)),
                       token if suffix in ('.o','_f.o','_h.o') else token+suffix[:-2],graphs)
                       for suffix,graphs in roles.items()}}


class CinematicGraphs:
    def __init__(self,data,expected_sha256):
        require(type(data) is bytes and hashlib.sha256(data).hexdigest()==expected_sha256,
                'Cinematic graphs require the verified original archive')
        self.archive=Archive(data);self.sha256=expected_sha256
        self.controls={};self.attributes=set();self.headers={};self.envelopes={}
        # Derive role-specific opaque controls from the whole verified corpus.
        # No source control, native address or ELF header is accepted from JSON.
        for entry in self.archive.entries:
            if not re.fullmatch(r'(?:CI_|CE_|BT)[A-Za-z0-9_]+\.viv',entry.name):continue
            bundle=Archive(unpack(self.archive.read(entry.name)));token=entry.name[:-4]
            for suffix,roles in member_roles(token).items():
                if (token+suffix).lower() not in bundle.by_name:continue
                index=AnimationIndex(AnimationEnvelope.from_model(unpack(bundle.read(token+suffix))))
                try:layout=CurveLayouts(index)
                except AssetError:continue  # Unadmitted retail codecs are never a template.
                self.envelopes.setdefault(suffix,index.model)
                for role,ending in roles.items():
                    name=record_token(token if suffix in ('.o','_f.o','_h.o') else token+suffix[:-2])+ending
                    if name not in index.lookup:continue
                    parent=index.records[index.lookup[name]]
                    control,padding,_,scale=parent_profile(layout,parent)
                    self.attributes.add(padding|scale)
                    key=(suffix,role)
                    profile=self.controls.setdefault(key,{'parent':set(),'leaf':{},'padding':set()})
                    profile['parent'].add(control)
                    for child in index.children[parent]:
                        kind=index.record_types[child];profile['leaf'].setdefault(kind,set()).add(layout.values(child+2,1)[0])
                        if kind==25:profile['padding'].add(layout.values(child+7,1,'B')[0])
                        elif kind in (20,21):
                            self.headers.setdefault((suffix,role,kind),set()).add(layout.values(child+18,2,'B'))
        require(self.controls and self.attributes,'Original archive has no supported cinematic profiles')

    def convert(self,data,token,rig_sha256,bone_count):
        """Account for source controls before exporting its numeric document."""
        bundle=Archive(data)
        for suffix,roles in member_roles(token).items():
            index=AnimationIndex(AnimationEnvelope.from_model(unpack(bundle.read(token+suffix))))
            layout=CurveLayouts(index);model=index.model;root=model.export_offset(index.envelope.bank)
            bank=token if suffix in ('.o','_f.o','_h.o') else token+suffix[:-2]
            expected={index.envelope.bank,'__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4'}
            if 'EYE' in suffix or 'TARGET' in suffix:
                expected|={'__Model:::'+record_token(bank),'__BBOX:::'+record_token(bank)}
            require(index.envelope.bank=='__AnimationBank:::'+bank and model.exports==expected,
                    'Source cinematic has unaccounted exports')
            words=model.data_words(root,6)
            require((words[0],words[2],words[3])==(28,32 if 'EYE' in suffix or 'TARGET' in suffix else 0,0),
                    'Source cinematic bank controls differ from supported role')
            for role,ending in roles.items():
                parent=index.records[index.lookup[record_token(bank)+ending]]
                control,padding,_,scale=parent_profile(layout,parent);profile=self.controls[(suffix,role)]
                require(control in profile['parent'] and padding|scale in self.attributes,'Source parent controls are unsupported')
                for child in index.children[parent]:
                    kind=index.record_types[child]
                    require(kind in (18,20,21,25) and kind in profile['leaf']
                            and layout.values(child+2,1)[0] in profile['leaf'][kind],'Source leaf controls are unsupported')
                    if kind==25:
                        require(layout.values(child-20,5,'I')==(0,0,25,0,0)
                                and layout.values(child+7,1,'B')[0] in profile['padding'],'Source palette envelope is unsupported')
                    if kind==18:require(layout.values(child+17,1,'B')==(0,),'Source quaternion header is unsupported')
        return read_cinematic(data,token,rig_sha256,bone_count)

    def compose(self,value,assigned,rig_sha256,bone_count,hands):
        fields(value,'format rig_sha256 bone_count layout members')
        require(value['format']==FORMAT and value['rig_sha256']==rig_sha256
                and value['bone_count']==bone_count and type(bone_count) is int and 1<=bone_count<=256,
                'Cinematic graph differs from the actual rig')
        require(value['layout'] in ('intro','single-camera') and re.fullmatch(r'(?:FI|FV)[0-9]{5}|B[0-9]{5}',assigned),
                'Unsupported cinematic layout or assigned name')
        roles=member_roles('CI_0000' if value['layout']=='intro' else 'CE_0000')
        fields(value['members'],' '.join(roles))
        require(type(hands) is FacePalettes and hands.frame_counts==(32,32),'Cinematic requires verified shared hands')
        outputs={};checks=0
        for suffix,graphs in roles.items():
            member=value['members'][suffix];fields(member,' '.join(graphs))
            name=assigned if suffix in ('.o','_f.o','_h.o') else assigned+suffix[:-2]
            payload=bytearray(struct.pack('<I',4)+bytes(12));writer=Writer(payload,{})
            root=writer.append(struct.pack('<6I',28,len(graphs),32 if 'EYE' in suffix or 'TARGET' in suffix else 0,0,0,0))
            records={}
            for role,ending in graphs.items():
                graph=member[role];fields(graph,'duration_ticks time_scale children')
                integer(graph['duration_ticks'],0,65535);integer(graph['time_scale'],1,255)
                attr=0x30303000|graph['time_scale']
                require(attr in self.attributes,'Unsupported cinematic timing profile')
                profile=self.controls[(suffix,role)]
                require(len(profile['parent'])==1,'Ambiguous original cinematic parent control')
                children=array(graph['children'],0,16);emitted=[]
                palette=suffix in ('_f.o','_h.o');camera='EYE' in suffix or 'TARGET' in suffix
                require((not children if suffix=='_f.o' else len(children) in (0,2)) if palette else bool(children),
                        'Unsupported cinematic output-role shape')
                occupied=set()
                for ordinal,leaf in enumerate(children):
                    kind=leaf.get('kind') if type(leaf) is dict else None
                    require(kind in profile['leaf'] and len(profile['leaf'][kind])==1,'Unsupported cinematic codec control')
                    control=next(iter(profile['leaf'][kind]))
                    if palette:
                        fields(leaf,'kind selector samples times')
                        require(kind==25 and type(leaf['selector']) is int and leaf['selector']==ordinal,
                                'Cinematic hand selectors must be ordered zero and one')
                        samples=[integer(v,0,255) for v in array(leaf['samples'],1,4096)]
                        times(leaf['times'],len(samples),transitions=False);hands.require_samples(ordinal,tuple(samples))
                        require(len(profile['padding'])==1,'Ambiguous cinematic palette padding')
                        emitted.append(writer.leaf(leaf,control,next(iter(profile['padding']))));continue
                    require(kind in ((18,) if role=='rotation' else (20,21)), 'Cinematic codec differs from output role')
                    validate_numeric(leaf,64 if camera else 12*bone_count)
                    destinations=leaf['destinations']+leaf['constant_destinations']
                    if role=='rotation':
                        require(all(d<(1 if camera else bone_count) for d in destinations),'Cinematic bone exceeds output')
                        writes={12*d+j for d in destinations for j in range(4,8)}
                    else:
                        allowed=({0,2,8,9,10} if 'EYE' in suffix else {8,9,10}) if kind==21 else ({0,8} if camera else {8})
                        require(set(destinations)<=allowed,'Cinematic vector/scalar escapes its semantic output')
                        require(tuple(leaf['unused_header']) in self.headers.get((suffix,role,kind),set()),
                                'Unsupported cinematic vector header profile')
                        writes={d+j for d in destinations for j in range(3 if kind==20 else 1)}
                    require(not occupied&writes,'Overlapping cinematic destinations');occupied.update(writes)
                    emitted.append(write_numeric(writer,leaf,control,64 if camera else 12*bone_count))
                attributes=writer.append(struct.pack('<3I',1,65537,attr))
                parent=writer.append(struct.pack('<HHIHH',15,next(iter(profile['parent'])),0,len(emitted),graph['duration_ticks'])+bytes(4*len(emitted)))
                writer.pointer(parent+4,attributes)
                for i,child in enumerate(emitted):writer.pointer(parent+12+4*i,child)
                records[record_token(name)+ending]=parent
            ordered=sorted(records)
            table=writer.append(bytes(4*len(ordered)));names=writer.append(bytes(4*len(ordered)))
            for i,label in enumerate(ordered):
                writer.pointer(table+4*i,records[label]);writer.pointer(names+4*i,writer.append(label.encode()+b'\0'))
            writer.pointer(root+16,table);writer.pointer(root+20,names)
            model=copy.copy(self.envelopes[suffix]);model.sections=copy.deepcopy(model.sections)
            model.sections[4]=list(model.sections[4]);model.sections[4][7]=1
            model.symbols=[('',0,0,0,0),('__AnimationBank:::'+name,root,24,0x10,1),
                           ('__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4',0,4,0x21,1)]
            model.imports=set();payload.extend(bytes(-len(payload)%4))
            parts=rebuild(model,payload,writer.pointers);data=b''.join(parts)
            actual=read_member(data,name,graphs)
            require(actual==member,'Fresh cinematic graph differs from authored values')
            layout=CurveLayouts(AnimationIndex(AnimationEnvelope(*parts)))
            for record,info in layout.records.items():
                if info['kind'] not in (18,20,21):continue
                curve=(QuaternionCurve if info['kind']==18 else VectorCurve)(layout,record)
                for key in range(info['keys']):
                    for row in curve.pose(key):
                        require(all(math.isfinite(v) and abs(v)<=1_000_000 for v in row),'Decoded cinematic scalar is nonfinite or unbounded')
                        if info['kind']==18:require(0.000001<=sum(v*v for v in row)<=4,'Decoded cinematic quaternion has invalid norm')
                    checks+=1
            outputs[assigned+suffix]=data
        # Fresh BIG container: no inherited or unreferenced source members.
        directory=16+sum(9+len(name) for name in outputs)
        offset=(directory+127)&~127
        header=bytearray(b'BIGF'+bytes(4)+struct.pack('>II',len(outputs),directory))
        payloads=bytearray()
        for name,data in outputs.items():
            padding=-(offset+len(payloads))%128;payloads.extend(bytes(padding))
            header.extend(struct.pack('>II',offset+len(payloads),len(data))+name.encode()+b'\0')
            payloads.extend(data)
        header.extend(bytes(offset-len(header)));header.extend(payloads)
        struct.pack_into('<I',header,4,len(header));result=bytes(header);Archive(result)
        hand_leaves=value['members']['_h.o']['pose']['children']
        return result,{'schema':FORMAT,'sha256':hashlib.sha256(result).hexdigest(),
                       'members':len(outputs),'decoded_key_checks':checks,'native_admission':False,
                       'full_graph':True,'rig_sha256':rig_sha256,'bone_count':bone_count,
                       'hand_frames':[max(leaf['samples'])+1 for leaf in hand_leaves] if hand_leaves else [0,0]}
