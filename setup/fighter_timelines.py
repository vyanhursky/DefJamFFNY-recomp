"""Typed retiming of verified native tag and camera event payloads.

Creator files reference complete baseline payloads, never native opcodes,
arguments, XML or serialized pointer tables. Paired tags retain their behavior
template's exact payload order. Cameras retain its non-shake sequence; authored
shake entries must also be complete verified payloads. Native filtering remains
authoritative. Times use the native event clock, independently of curve keys.
"""
import hashlib
import re
import struct

from fighter_animation import require
from fighter_registry import fingerprint

MAX_BYTES=64*1024**2
MAX_ROWS=65535
MAX_EVENTS=8192
TAG_FORMAT='fighter-tag-timeline-1'
CAMERA_FORMAT='fighter-camera-timeline-1'
NAME=re.compile(r'[A-Za-z0-9_]{1,8}')


def fields(value,names):
    require(type(value) is dict and set(value)==set(names.split()),'Timeline fields differ from the typed schema')


def tag_rows(data):
    require(type(data) is bytes and 8<=len(data)<=MAX_BYTES and data[:4]==b'TAGS','Invalid animation tag envelope')
    count,=struct.unpack_from('<I',data,4)
    require(0<count<=MAX_ROWS and 8+4*count<=len(data),'Animation tag population exceeds budget')
    offsets=struct.unpack_from('<'+'I'*count,data,8)
    require(offsets[0]==8+4*count and all(a<b for a,b in zip(offsets,offsets[1:])),
            'Animation tag offsets overlap or leave unaccounted bytes')
    rows=[]
    for index,start in enumerate(offsets):
        end=offsets[index+1] if index+1<count else len(data)
        require(start+12<=end<=len(data),'Animation tag row exceeds its envelope')
        raw=data[start:start+8][::-1]
        try:
            name=raw.rstrip(b'\0').decode('ascii')
        except UnicodeError as error:
            raise ValueError('Unsupported animation tag name') from error
        require(NAME.fullmatch(name) and name.encode().ljust(8,b'\0')==raw,'Noncanonical animation tag name')
        population,=struct.unpack_from('<I',data,start+8)
        require(population<=MAX_EVENTS,'Animation tag event count exceeds budget')
        at=start+12;events=[]
        for _ in range(population):
            require(at+6<=end,'Truncated animation tag event')
            tick,arguments,opcode=struct.unpack_from('<3h',data,at)
            require(0<=arguments<=64 and at+6+2*arguments<=end,'Animation tag argument range escapes row')
            args=list(struct.unpack_from('<'+'h'*arguments,data,at+6))
            events.append((tick,[opcode,args]));at+=6+2*arguments
        require(at==end,'Unaccounted animation tag row bytes')
        rows.append({'name':name,'events':events,'raw':data[start:end]})
    keys=[int.from_bytes(row['name'].encode().ljust(8,b'\0'),'big') for row in rows]
    require(all(a<b for a,b in zip(keys,keys[1:])),'Animation tag names are not unique native search keys')
    return rows


def camera_rows(data):
    require(type(data) is bytes and 0<len(data)<=MAX_BYTES and data.count(b'<specialcamera>')==1
            and data.count(b'</specialcamera>')==1,'Unsupported camera XML envelope')
    rows=[]
    for match in re.finditer(rb'<timetable>(.*?)</timetable>',data,re.S):
        block=match[1];names=re.findall(rb'<name>([^<]*)</name>',block)
        require(len(names)==1,'Camera timetable needs exactly one name')
        try:
            name=names[0].strip().decode('ascii')
        except UnicodeError as error:
            raise ValueError('Unsupported camera timetable name') from error
        require(re.fullmatch(r'[A-Za-z0-9_]{1,31}',name),'Unsupported camera timetable identifier')
        frames=re.findall(rb'<frame>([^<]*)</frame>',block)
        require(0<len(frames)<=MAX_EVENTS,'Camera frame population exceeds budget')
        events=[]
        for frame in frames:
            try:
                values=[part.strip().decode('ascii') for part in frame.split(b',')]
                require(len(values)==6 and re.fullmatch(r'-?[0-9]{1,6}',values[0]),'Unsupported camera frame fields')
                require(all(0<len(v)<=64 and all(32<=ord(c)<127 and c not in '<>&,\"' for c in v)
                            for v in values[1:]),'Unsupported camera payload token')
                events.append((int(values[0]),values[1:]))
            except UnicodeError as error:
                raise ValueError('Camera frame is not supported ASCII data') from error
        rows.append({'name':name,'events':events})
    require(0<len(rows)<=MAX_ROWS,'Camera timetable population exceeds budget')
    return rows


class EventLibrary:
    def __init__(self,kind,rows):
        require(kind in ('tag','camera'),'Unsupported event library kind')
        self.kind=kind
        self.format=TAG_FORMAT if kind=='tag' else CAMERA_FORMAT
        self.payloads={}
        for row in rows:
            for _tick,payload in row['events']:
                self.payloads['retail/'+kind+'-'+fingerprint(payload)]=payload

    def export(self,events):
        result=[]
        for tick,payload in events:
            identifier='retail/'+self.kind+'-'+fingerprint(payload)
            require(identifier in self.payloads and self.payloads[identifier]==payload,
                    'Source event payload is absent from the verified original')
            result.append({'tick':tick,'template':identifier})
        source={'format':self.format,'events':result}
        self.compile(source)
        return source

    def compile(self,source):
        fields(source,'format events')
        require(source['format']==self.format and type(source['events']) is list
                and (0 if self.kind=='tag' else 1)<=len(source['events'])<=MAX_EVENTS,
                'Unsupported typed timeline profile or population')
        result=[];previous=-1
        for event in source['events']:
            fields(event,'tick template')
            tick=event['tick'];identifier=event['template']
            require(type(tick) is int and 0<=tick<=(32767 if self.kind=='tag' else 65535)
                    and (tick>=previous if self.kind=='tag' else tick>previous),
                    'Timeline ticks must use the bounded ordered native clock')
            require(type(identifier) is str and identifier in self.payloads,'Unknown baseline event reference')
            result.append((tick,self.payloads[identifier]));previous=tick
        return result


class TagTimelines:
    def __init__(self,data,expected_sha256):
        require(type(data) is bytes and hashlib.sha256(data).hexdigest()==expected_sha256,
                'Tag timelines require a verified original')
        self.data=data;self.rows=tag_rows(data);self.by_name={row['name']:row for row in self.rows}
        self.library=EventLibrary('tag',self.rows)

    def compose(self,additions):
        require(type(additions) is dict and 0<len(additions) and len(additions)+len(self.rows)<=MAX_ROWS,
                'Tag timeline population exceeds budget')
        rows={row['name']:row['raw'] for row in self.rows}
        for name,value in additions.items():
            require(type(name) is str and NAME.fullmatch(name) and name not in rows,'Owned tag name collides or is invalid')
            fields(value,'template timeline')
            require(type(value['template']) is str and value['template'] in self.by_name,'Missing verified tag behavior template')
            events=self.library.compile(value['timeline'])
            require([payload for _,payload in events]==[payload for _,payload in self.by_name[value['template']]['events']],
                    'Tag payload sequence differs from its verified behavior template')
            output=bytearray(name.encode().ljust(8,b'\0')[::-1]+struct.pack('<I',len(events)))
            for tick,(opcode,args) in events:
                output.extend(struct.pack('<3h',tick,len(args),opcode)+struct.pack('<'+'h'*len(args),*args))
            rows[name]=bytes(output)
        ordered=sorted(rows,key=lambda name:int.from_bytes(name.encode().ljust(8,b'\0'),'big'))
        at=8+4*len(ordered);offsets=[]
        for name in ordered:
            offsets.append(at);at+=len(rows[name])
        require(at<=MAX_BYTES,'Composed tag timelines exceed byte budget')
        result=b'TAGS'+struct.pack('<I',len(ordered))+struct.pack('<'+'I'*len(offsets),*offsets)+b''.join(rows[name] for name in ordered)
        tag_rows(result)
        return result


class CameraTimelines:
    def __init__(self,data,expected_sha256):
        require(type(data) is bytes and hashlib.sha256(data).hexdigest()==expected_sha256,
                'Camera timelines require a verified original')
        self.data=data;self.rows=camera_rows(data);self.by_name={row['name']:row for row in self.rows}
        require(len(self.by_name)==len(self.rows),'Verified camera baseline contains duplicate identities')
        self.library=EventLibrary('camera',self.rows)

    def compose(self,additions):
        require(type(additions) is dict and 0<len(additions) and len(additions)+len(self.rows)<=MAX_ROWS,
                'Camera timetable population exceeds budget')
        output=[]
        for name,value in sorted(additions.items()):
            require(type(name) is str and NAME.fullmatch(name) and name not in self.by_name,'Owned camera name collides or is invalid')
            fields(value,'template timeline')
            require(type(value['template']) is str and value['template'] in self.by_name,'Missing verified camera behavior template')
            events=self.library.compile(value['timeline'])
            source_payloads=[p for _,p in events if p[2]!='shake']
            template_payloads=[p for _,p in self.by_name[value['template']]['events'] if p[2]!='shake']
            require(source_payloads==template_payloads,'Camera non-shake sequence differs from its verified behavior template')
            output.append(('<timetable>\r\n<name>'+name+'</name>\r\n'+''.join(
                '<frame>'+str(tick)+','+','.join(payload)+'</frame>\r\n' for tick,payload in events)
                           +'</timetable>\r\n').encode('ascii'))
        at=self.data.index(b'</specialcamera>')
        result=self.data[:at]+b''.join(output)+self.data[at:]
        require(len(result)<=MAX_BYTES,'Composed camera timelines exceed byte budget')
        camera_rows(result)
        return result


def encode_timeline_bindings(tags,cameras,claims):
    require(type(claims) is dict and 0<len(claims)<=MAX_ROWS,'Invalid owned timeline claims')
    tag_names={row['name'] for row in tag_rows(tags)}
    camera_names={row['name'] for row in camera_rows(cameras)}
    rows=[]
    for name,flags in sorted(claims.items()):
        require(type(name) is str and NAME.fullmatch(name) and type(flags) is int and 0<=flags<=3,
                'Invalid owned timeline binding')
        require((not flags&1 or name in tag_names) and (not flags&2 or name in camera_names),
                'Owned timeline binding lacks its generated row')
        rows.append(struct.pack('<8sI',name.encode(),flags))
    return (struct.pack('<4s7I',b'FTE1',1,len(rows),len(tag_names),len(camera_names),len(tags),len(cameras),0)
            +hashlib.sha256(tags).digest()+hashlib.sha256(cameras).digest()+b''.join(rows))
