"""Read-only catalogs and audio audition for the offline Fighter Workshop.

Original event ordinals are labelled as ordinals until their semantics have
been established. Audio audition does not change the native decoder or banks.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import wave

from fighter_archive import Archive, MAX_ARCHIVE
from fighter_assets import unpack, AssetError
from fighter_ai import AIProfiles, EDITABLE, DIFFICULTIES, FIELDS, xml, children
from fighter_build import retail_catalog
from fighter_cinematics import Cinematics
from fighter_voice_bank import VoiceBankTemplate, FAMILIES
from fighter_voice import parse_stream
from fighter_voice_r2 import inspect_source

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssetError(message)


def original(game, relative, pin):
    with (Path(game)/relative).open('rb') as stream:
        raw = stream.read(MAX_ARCHIVE+1)
    require(0 < len(raw) <= MAX_ARCHIVE and hashlib.sha256(raw).hexdigest()==pin,
            'Original authoring asset differs from the supported game: '+relative)
    return raw


def pins():
    return json.loads((ROOT/'config/fighter-native-baseline.json').read_text())


def bank(archive, category, voice):
    require(category in FAMILIES and type(voice) is int and 0 <= voice < 65535, 'Unknown voice bank')
    directory='Def_Jam_IP_Characters' if voice>=500 else 'Def_Jam_Characters'
    stem=f'speech/{category}/{directory}/{voice:03d}'
    header,data=archive.read(stem+'.hdr'),archive.read(stem+'.dat')
    result=VoiceBankTemplate(header,data,hashlib.sha256(header).hexdigest(),hashlib.sha256(data).hexdigest())
    require(result.first_key in FAMILIES[category] and result.voice_key==voice,'Original voice category differs')
    return result


def catalog(game):
    pin=pins();retail=retail_catalog(Path(game)/'assets/djv2.sod')
    speech=Archive(original(game,'audio/speech2.viv',pin['speech_sha256']),native_separators=True)
    banks=[]
    for entry in speech.entries:
        name=speech.name_key(entry.name)
        match=re.fullmatch(r'speech/(character|taunts|enviro)/def_jam_(?:ip_)?characters/([0-9]+)\.hdr',name)
        if not match:continue
        category=next(key for key in FAMILIES if key.lower()==match[1]);voice=int(match[2])
        try:template=bank(speech,category,voice)
        except ValueError:continue
        banks.append(dict(category=category,voice=voice,family=template.first_key,count=template.count))
    available={(row['category'],row['voice']):row for row in banks}
    streams={role:{} for role in ('intro','extro')}
    for role in streams:
        for entry in speech.entries:
            name=speech.name_key(entry.name)
            match=re.fullmatch('speech/streams/'+role+r'/([0-9]+)([ie][0-9]+)?\.asf',name)
            if match:
                streams[role].setdefault(int(match[1]),[]).append(name)
        for voice in streams[role]:streams[role][voice].sort(key=lambda n:(len(n),n))
    nis=Archive(original(game,'assets/nis.viv',pin['nis_sha256']))
    films=Cinematics(unpack(nis.read('assets/IntroExtro.xml')),pin['intro_extro_sha256'])
    v2ta=Archive(original(game,'assets/v2ta.viv',pin['v2ta_sha256']))
    owners={};fighters=[]
    baseline={'retail/'+row['id']:row for row in retail.baseline()['fighters']}
    for key,row in sorted(retail.rows.items()):
        if not 1<=row['native_binding']['core_id']<=86:continue
        label=row['fields']['DisplayName']['symbol'];model=row['fields']['Model']['symbol'];voice=row['fields']['SpeechId']['word']
        pair=films.bindings.get(model.casefold())
        if pair:
            for token in (pair.intro,pair.victory):owners.setdefault(token,[]).append(label)
        fighters.append(dict(key=key,label=label,core=row['native_binding']['core_id'],voice=voice,
            voice_resource=baseline[key]['components']['voice'],
            banks={category:available[(category,voice)] for category in FAMILIES if (category,voice) in available},
            streams={role:streams[role].get(voice,[]) for role in streams},
            intro=pair.intro if pair else None,victory=pair.victory if pair else None))
    clips=[]
    for entry in v2ta.entries:
        match=re.fullmatch(r'(C[IE]_[A-Za-z0-9]{4})\.viv',entry.name,re.I)
        if match:
            token=match[1].upper();names=sorted(set(owners.get(token,[])))
            clips.append(dict(key=token,role='intro' if token.startswith('CI_') else 'victory',
                label=(', '.join(names)+' · ' if names else 'Original sequence · ')+token))
    ai=AIProfiles(original(game,'assets/ai/ai.viv',pin['ai_sha256']),pin['ai_sha256'])
    personalities=[]
    for entry in ai.archive.entries:
        match=re.fullmatch(r'assets/ai/(cha(?:r[0-9]{4}|[0-9]{5}))\.xml',entry.name,re.I)
        if not match:continue
        try:
            name=match[1].lower();profile=xml(ai.read(name),'artficial_intelligence');levels={}
            for difficulty in DIFFICULTIES:
                slots=[]
                for slot in range(4):
                    ref=profile.findtext('tendency_list/'+difficulty+f'/tendency{slot}')
                    tendency=xml(ai.read(ref),'tendencies');children(tendency,FIELDS)
                    slots.append({field:int(tendency.findtext(field)) for field in sorted(EDITABLE)})
                levels[difficulty]=slots
            personalities.append(dict(key=name,label=name,tendencies=levels))
        except (ValueError,TypeError,KeyError):
            continue  # Only profiles admitted by the shared AI compiler appear.
    ai_labels={}
    for fighter in fighters:ai_labels.setdefault(f"char{fighter['core']:04d}",set()).add(fighter['label'])
    for personality in personalities:
        if personality['key'] in ai_labels:personality['label']=', '.join(sorted(ai_labels[personality['key']]))+' · '+personality['key']
    return dict(schema='fighter-workshop-catalog-1',fighters=fighters,banks=banks,
        cinematics=sorted(clips,key=lambda r:(r['role'],r['label'])),ai=sorted(personalities,key=lambda r:r['label']),
        identity='original-event-ordinal',source_sha256=retail.source_sha256)


def check(settings, choices):
    require(type(settings) is dict and set(settings)<={'voice','ai','intro','victory'},'Unknown performance setting')
    for role in ('intro','victory'):
        if role in settings:
            require(any(row['key']==settings[role] and row['role']==role for row in choices['cinematics']), 'Unavailable '+role+' sequence')
    if 'ai' in settings:
        ai=settings['ai'];require(any(row['key']==ai['preset'] for row in choices['ai']),'Unknown AI profile')
        require(set(ai['tendencies'])==set(DIFFICULTIES),'AI needs all difficulty levels')
        for slots in ai['tendencies'].values():
            require(type(slots) is list and len(slots)==4,'AI needs four slots per difficulty')
            for edits in slots:require(type(edits) is dict and set(edits)<=EDITABLE and all(type(v) is int and 1<=v<=5 for v in edits.values()),'Unsupported AI tendency')
    if 'voice' in settings:
        voice=settings['voice'];require(any(row['key']==voice['preset'] for row in choices['fighters']),'Unknown voice preset')
        selected=next(row for row in choices['fighters'] if row['key']==voice['preset'])
        require(set(voice['banks'])<=set(FAMILIES),'Unknown voice category')
        for category,key in voice['banks'].items():
            require(any(row['category']==category and row['voice']==key for row in choices['banks']),'Unsupported voice category template')
        for target in voice['clips']:
            if target in ('intro','extro'):continue
            match=re.fullmatch(r'(Character|Taunts|Enviro):([0-9]+)',target)
            require(match is not None,'Unknown voice override slot')
            category,index=match[1],int(match[2]);key=voice['banks'].get(category,selected['voice'])
            require(any(row['category']==category and row['voice']==key and index<row['count'] for row in choices['banks']), 'Voice clip exceeds its original event table')
    return dict(valid=True)


def decode_audio(raw):
    """Audition original PCM/R2 as WAV; R2 uses bounded integer prediction.

    R2 framing is verified by inspect_source. Predictor/block semantics were
    checked against FFmpeg libavcodec/adpcm.c's EA R2 implementation
    (https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/adpcm.c); this is
    an offline audition, not the native game's float-history decoder oracle.
    """
    try:
        value=parse_stream(raw);pcm,rate=value.pcm16,value.sample_rate
    except ValueError:
        value=inspect_source(raw);rate=value.sample_rate;history=[0,0];samples=[]
        coefficients=((0,0),(240,0),(460,-208),(392,-220))
        for count,payload in value.packets:
            cursor=0;decoded=[]
            while len(decoded)<count:
                selector=payload[cursor];cursor+=1
                if selector==0xee:
                    values=struct.unpack_from('>30h',payload,cursor);cursor+=60
                    history[:]=values[:2];decoded.extend(values[2:])
                else:
                    a,b=coefficients[selector>>4];shift=12-(selector&15)
                    for byte in payload[cursor:cursor+14]:
                        for nibble in (byte>>4,byte&15):
                            signed=nibble if nibble<8 else nibble-16
                            sample=max(-32768,min(32767,(signed*(1<<(shift+8))+a*history[0]+b*history[1])>>8))
                            history[:]=[sample,history[0]];decoded.append(sample)
                    cursor+=14
            samples.extend(decoded[:count])
        require(len(samples)==value.sample_count,'Decoded voice length differs')
        pcm=struct.pack('<'+'h'*len(samples),*samples)
    output=io.BytesIO()
    with wave.open(output,'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
    return output.getvalue()


def audio(game,request):
    pin=pins();archive=Archive(original(game,'audio/speech2.viv',pin['speech_sha256']),native_separators=True)
    require(type(request) is dict and set(request)<={'category','voice','index','stream'},'Unsupported audio audition request')
    if 'stream' in request:
        name=request['stream'];require(type(name) is str and re.fullmatch(r'speech/streams/(?:intro|extro)/[0-9]+(?:[ie][0-9]+)?\.asf',name),'Unknown original speech stream')
        raw=archive.read(name)
    else:
        template=bank(archive,request['category'],request['voice']);index=request['index']
        require(type(index) is int and 0<=index<len(template.streams),'Unknown original voice clip')
        raw=template.streams[index]
    wav=decode_audio(raw)
    return dict(mime='audio/wav',data=base64.b64encode(wav).decode('ascii'),bytes=len(wav))


def export_performance(game,request,destination):
    """Generate ordinary typed resources; the whole pack still compiles later."""
    from mods import ordinary_path
    from fighter_behavior_files import wav_file
    require(type(request) is dict and set(request)=={'settings','pack','donor'},'Unsupported performance export request')
    require(type(request['pack']) is str and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',request['pack']),'Invalid pack identity')
    settings=request['settings'];choices=catalog(game);check(settings,choices)
    require(any(row['key']==request['donor'] for row in choices['fighters']),'Unknown presentation donor')
    family='retail/binding-'+request['donor'].split('/')[1]
    target=ordinary_path(Path(destination));require(not target.exists(),'Performance output already exists')
    require(not target.is_relative_to(Path(game).resolve()),'Keep authored outputs outside the game files')
    target.mkdir(parents=True);resources=[];components={};pack=request['pack']
    def file(raw,suffix):
        digest=hashlib.sha256(raw).hexdigest();name=digest+suffix;path=target/name
        if not path.exists():path.write_bytes(raw)
        return dict(path='performance/'+name,sha256=digest)
    if 'voice' in settings:
        voice=settings['voice'];preset=next(r for r in choices['fighters'] if r['key']==voice['preset'])
        components['voice']=preset['voice_resource']
        if not voice['banks'] and not voice['clips']:
            resources.append(dict(id='performance-voice',kind='voice',compatibility={'events':family},
                source=dict(format='fighter-voice-retail-1',donor=voice['preset'])))
            components['voice']=pack+'/performance-voice'
        if voice['banks'] or voice['clips']:
            from fighter_voice_compile import CATEGORIES
            archive=Archive(original(game,'audio/speech2.viv',pins()['speech_sha256']),native_separators=True)
            banks={}
            for category in CATEGORIES:
                selected=voice['banks'].get(category,preset['voice'])
                row=next((r for r in choices['banks'] if r['category']==category and r['voice']==selected),None)
                if row is None:banks[category]=dict(state='absent');continue
                samples={}
                for key,value in voice['clips'].items():
                    if key.startswith(category+':'):
                        raw=base64.b64decode(value,validate=True);wav_file(raw)
                        samples[key.split(':')[1]]={**file(raw,'.wav'), 'format':'wav-pcm16'}
                banks[category]=dict(state='present',template_voice=selected,family=row['family'],samples=samples)
            source=dict(format='fighter-voice-4',banks=banks)
            for role in ('intro','extro'):
                if role in voice['clips']:raw=base64.b64decode(voice['clips'][role],validate=True)
                else:
                    require(preset['streams'][role], 'This voice preset has no '+role+' stream; import a WAV for that slot')
                    raw=decode_audio(archive.read(preset['streams'][role][0]))
                wav_file(raw);source[role]={**file(raw,'.wav'),'format':'wav-pcm16'}
            resources.append(dict(id='performance-voice',kind='voice',compatibility={'events':family},source=source))
            components['voice']=pack+'/performance-voice'
    if 'ai' in settings:
        ai=settings['ai'];source=dict(format='fighter-ai-2',template_profile=ai['preset'],
            tendencies={level:{str(i):row for i,row in enumerate(rows)} for level,rows in ai['tendencies'].items()})
        resources.append(dict(id='performance-ai',kind='ai',compatibility={},source=source));components['ai']=pack+'/performance-ai'
    for role in ('intro','victory'):
        if role not in settings:continue
        resources.append(dict(id='performance-'+role,kind='cinematic',compatibility={'skeleton':family,'events':family},
            source=dict(format='fighter-cinematic-retail-1',template=settings[role])))
        components[role]=pack+'/performance-'+role
    return dict(resources=resources,components=components)
