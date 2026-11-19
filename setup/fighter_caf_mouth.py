"""Closed reviewed-donor speech mouth authoring. No rig destinations or programs are input.

Jaw is native69/local X, capped at12deg (below observed donor12.6386deg,
not a collision guarantee). Lips use the actual CAF selector1 palette. Tracks
retain the reviewed donor interval and use native type13/type25 interpolation.
"""
import copy
import io
import math
import struct
import wave
from bisect import bisect_right
from fighter_animation import require
from fighter_animation_scalars import f32
from fighter_animation_timed_quaternions import blend

FORMAT = 'fighter-caf-cinematic-2'
PUBLIC_FORMAT = 'fighter-cinematic-caf-performance-2'
DURATION = 65
DURATIONS = {"CI_132A": 65, "CI_113A": 106}
JAW_DESTINATION = 69 * 12 + 4
MAX_JAW_DEGREES = 12.0
PREVIEW_AUDIO_DELAY = 5  # Existing measured approx reference; native test calibrates this separately.


def validate_mouth(value, duration=DURATION):
    require(type(value) is dict and set(value) == {'jaw', 'lips'}, 'Mouth needs jaw and lips tracks')
    for name, maximum in [('jaw', 1.0), ('lips', 14)]:
        rows = value[name]
        require(type(rows) is list and 2 <= len(rows) <= 256, 'Mouth key population exceeds budget')
        previous = -1
        for row in rows:
            require(type(row) is list and len(row) == 2 and type(row[0]) is int
                    and previous < row[0] <= duration, 'Mouth times must be unique increasing whole source ticks')
            previous = row[0]
            require(type(row[1]) in ((int, float) if name == 'jaw' else (int,))
                    and 0 <= row[1] <= maximum and math.isfinite(row[1]), 'Mouth value exceeds native control')
        require(rows[0] == [0, 0] and rows[-1] == [duration, 0], 'Mouth must begin and end closed/neutral')
    return value


def neutral_mouth(duration=DURATION):
    return {'jaw': [[0, 0.0], [duration, 0.0]], 'lips': [[0, 0], [duration, 0]]}


def quaternion(opening):
    angle = opening * math.radians(MAX_JAW_DEGREES) / 2
    return tuple(map(f32, (math.sin(angle), 0.0, 0.0, math.cos(angle))))


def jaw_leaf(rows):
    """Quantize one generated quaternion channel, checking decoded accumulated error."""
    poses = [quaternion(r[1]) for r in rows]
    coefficients = []
    deltas = [[0] * 4 for _ in rows[1:]]
    for c in range(4):
        differences = [b[c] - a[c] for a, b in zip(poses, poses[1:])]
        low, high = min(differences), max(differences)
        offset, scale = f32(low), f32((high - low) / 65535) if high != low else 0.0
        coefficients.append([offset, scale, poses[0][c]])
        for k, d in enumerate(differences):
            deltas[k][c] = max(0, min(65535, round((d - offset) / scale))) if scale else 0
    leaf = dict(kind=13, destinations=[JAW_DESTINATION], times=[r[0] for r in rows[1:]],
                bits=16, coefficients=coefficients, deltas=deltas)
    decoded = decoded_jaw(leaf)
    require(max(abs(a-b) for p,q in zip(poses,decoded) for a,b in zip(p,q)) < 0.00005,
            'Mouth quantization error exceeds budget')
    require(all(abs(sum(v*v for v in q)-1) < .0002 for q in decoded), 'Quantized jaw norm differs')
    return leaf


def decoded_jaw(leaf):
    values = [r[2] for r in leaf['coefficients']]; out = [tuple(values)]
    for row in leaf['deltas']:
        for c,(offset,scale,_) in enumerate(leaf['coefficients']):
            delta = f32(row[c]*scale)
            values[c] = f32(f32(delta+values[c])+offset) if c%4==0 else f32(f32(delta+offset)+values[c])
        out.append(tuple(values))
    return out


def sample_jaw(rows, tick):
    leaf=jaw_leaf(rows); poses=decoded_jaw(leaf); times=[0,*leaf['times']]
    at=max(0,bisect_right(times,tick)-1)
    if at==len(times)-1 or tick==times[at]: return poses[at]
    weight=f32(f32(tick-times[at])/(times[at+1]-times[at]))
    return blend(poses[at],poses[at+1],weight,precision_bits=24)


def apply_graphs(graphs, mouth, token):
    duration=DURATIONS[token];validate_mouth(mouth,duration);result=copy.deepcopy(graphs)
    require(set(result)=={token+'_p'}, 'Mouth requires the reviewed donor face parent')
    children=result[token+'_p']['children']
    require(result[token+'_p']['duration_ticks']==duration and len(children)==2
            and [r['kind'] for r in children]==[25,25]
            and [r['selector'] for r in children]==[0,1], 'Face donor shape differs')
    children[1].update(times=[r[0] for r in mouth['lips']],samples=[r[1] for r in mouth['lips']])
    # Native face controller evaluates _s through+18, then _p through+30.
    # A type13 under _p would be a no-op. This independent _s overrides Jaw69
    # after the original body, before the disjoint expression palettes.
    result[token+'_s']=dict(duration_ticks=duration,time_scale=result[token+'_p']['time_scale'],
                           children=[jaw_leaf(mouth['jaw'])])
    return result


def wav_info(raw):
    require(type(raw) is bytes and len(raw)<=8*1024*1024, 'Voice WAV exceeds8MiB')
    try:
        with wave.open(io.BytesIO(raw),'rb') as w:
            require(w.getnchannels()==1 and w.getsampwidth()==2 and w.getcomptype()=='NONE',
                    'Import a mono uncompressed16-bit PCM WAV')
            rate,count=w.getframerate(),w.getnframes()
            require(8000<=rate<=48000 and 0<count<=4000000, 'Voice sample rate/count exceeds contract')
            require(len(w.readframes(count))==count*2,'Voice WAV is truncated')
    except (wave.Error,EOFError) as exc:raise ValueError('Invalid voice WAV') from exc
    return dict(sample_rate=rate,samples=count,seconds=count/rate)


def require_voice_fit(raw, speech_tick, duration=DURATION):
    require(type(speech_tick) is int and 0<=speech_tick<duration, 'Speech start tick exceeds donor')
    info=wav_info(raw)
    require(speech_tick+PREVIEW_AUDIO_DELAY+math.ceil(info['seconds']*30)<=duration,
            'Voice extends beyond this donor entrance; trim the clip or choose a longer donor')
    from fighter_voice import encode_stream,presentation_stream
    with wave.open(io.BytesIO(raw),'rb') as audio:pcm=audio.readframes(info['samples'])
    encoded=encode_stream(pcm,info['sample_rate']);info['encoded_bytes']=len(encoded)
    presentation_stream(encoded,'intro')
    return info


def jaw_guide(raw, speech_tick=0, duration=DURATION):
    """A labelled amplitude guide, not phoneme recognition or finished lip sync."""
    info=require_voice_fit(raw,speech_tick,duration)
    with wave.open(io.BytesIO(raw),'rb') as w:pcm=struct.unpack('<'+'h'*info['samples'],w.readframes(info['samples']))
    start=speech_tick+PREVIEW_AUDIO_DELAY; levels=[]
    for tick in range(math.ceil(info['seconds']*30)):
        chunk=pcm[round(tick*info['sample_rate']/30):round((tick+1)*info['sample_rate']/30)]
        levels.append(math.sqrt(sum(v*v for v in chunk)/max(1,len(chunk))))
    peak=max(levels,default=1) or 1;rows=[[0,0.0]]
    for i,level in enumerate(levels):
        t=start+i
        if t and t<duration:rows.append([t,0.0 if level<peak*.10 else min(.85,(level/peak)**.7*.85)])
    end=min(duration,start+len(levels))
    if rows[-1][0]!=end:rows.append([end,0.0])
    else:rows[-1][1]=0.0
    if rows[-1][0]!=duration:rows.append([duration,0.0])
    result=neutral_mouth(duration);result['jaw']=rows;validate_mouth(result,duration);return result


def speech_timeline(library, token, tick):
    """One trusted intro-start payload, private name only; preserve non-speech data."""
    rows=library.by_name[token]['events']
    starts=[payload for _,payload in rows if payload==[59,[0]]]
    require(starts and type(tick) is int and 0<=tick<DURATIONS[token], 'No verified donor speech event')
    events=[(at,copy.deepcopy(payload)) for at,payload in rows if payload!=[59,[0]]]
    events.append((tick,copy.deepcopy(starts[0])));events.sort(key=lambda r:r[0])
    return library.library.export(events)


# Coarse art mapping into the inspected CAF palette, not anatomical phonemes.
# Bilabials/pause use closed native pose1; rounded vowels use pose4. All
# samples remain user-editable. Teeth/tongue articulation is not generated.
PHONE_POSES = {
    'SIL': (0.,1), 'SPN': (0.,1), '+NSN+': (0.,1),
    'B': (0.,1), 'P': (0.,1), 'M': (0.,1),
    'W': (.12,4), 'UW': (.18,4), 'UH': (.3,4), 'OW': (.4,4), 'AO': (.5,4),
    'AA': (.75,3), 'AE': (.65,3), 'AH': (.45,0), 'AW': (.6,3), 'AY': (.6,2),
    'EH': (.4,2), 'EY': (.35,2), 'IY': (.2,2), 'IH': (.25,0), 'OY': (.45,4),
    'ER': (.25,4), 'R': (.2,4), 'F': (.12,11), 'V': (.12,11),
    'CH': (.15,0), 'DH': (.15,0), 'G': (.15,0), 'HH': (.25,0),
    'JH': (.15,0), 'K': (.15,0), 'L': (.2,0), 'N': (.12,0), 'NG': (.15,0),
    'S': (.12,0), 'SH': (.15,4), 'T': (.12,0), 'TH': (.15,0),
    'Y': (.18,2), 'Z': (.12,0), 'ZH': (.15,4), 'D': (.12,0),
}


def phoneme_guide(cues, raw, speech_tick=0, duration=DURATION):
    """Bounded whole-word/phone timing -> editable native jaw and lip samples."""
    import hashlib
    info=require_voice_fit(raw,speech_tick,duration)
    require(type(cues) is dict and cues.get('schema')=='fighter-speech-cues-1'
            and cues.get('source_sha256')==hashlib.sha256(raw).hexdigest(), 'Speech cues belong to another voice')
    words=cues.get('words');require(type(words) is list and 1<=len(words)<=100,'Speech word budget exceeded')
    offset=speech_tick+PREVIEW_AUDIO_DELAY;values={0:(0.,0),duration:(0.,0)};previous=0.
    for word in words:
        require(type(word) is dict and type(word.get('phones')) is list and len(word['phones'])<=100,'Invalid speech word')
        for phone in word['phones']:
            name=phone.get('phone');start=phone.get('start');end=phone.get('end')
            require(type(name) is str and name in PHONE_POSES and type(start) in (int,float) and type(end) in (int,float)
                    and math.isfinite(start) and math.isfinite(end)
                    and previous<=start<end<=info['seconds']+.02, 'Invalid/unsupported phone timing')
            previous=end;pose=PHONE_POSES[name]
            a=max(1,offset+round(start*30));b=min(duration-1,offset+round(end*30)-1)
            if a<duration:values[a]=pose
            if b>a:values[b]=pose
    end=offset+math.ceil(info['seconds']*30)
    if end<duration:values[end]=(0.,0)
    result={name:[[tick,value[i]] for tick,value in sorted(values.items())] for i,name in enumerate(('jaw','lips'))}
    validate_mouth(result,duration);return result
