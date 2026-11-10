"""Bounded offline source-track playback. Never admits imported native code.

Physical skeleton rows match the original animation buffer. The unrelated
skeleton permutation is intentionally not used to reorder channel destinations.
Preview runs at an explicit 30 source ticks/second; original camera, face/hand
palettes, runtime blending and event dispatch are not reproduced here.
"""
import math
import hashlib
import re
import struct

from fighter_workshop import original, pins, require
from fighter_assets import unpack
from fighter_archive import Archive
from fighter_caf import baseline_pins
from fighter_elf import Model
from fighter_skin import Skin
from fighter_animation import AnimationEnvelope, AnimationIndex
from fighter_animation_curves import CurveLayouts
from fighter_animation_graphs import parent_profile
from fighter_animation_quaternions import QuaternionCurve
from fighter_animation_timed_quaternions import TimedQuaternionCurve
from fighter_animation_vectors import VectorCurve


def motion_index(game, core):
    require(type(core) is int and 1 <= core <= 141, 'Choose an original fighter motion bank')
    archive = Archive(original(game, 'motion/wres_all.viv', pins()['animation_sha256']))
    return AnimationIndex(AnimationEnvelope(*(unpack(archive.read(f'wres{core:03d}.'+suffix))
                                              for suffix in ('ord', 'orl', 'mnl'))))


def index_for(game, request):
    token = request.get('clip')
    require(type(token) is str and re.fullmatch(r'[A-Za-z0-9_]{1,120}', token), 'Invalid animation token')
    if request.get('core') is not None:
        return motion_index(game, request['core'])
    require(re.fullmatch(r'C[IE]_[A-Za-z0-9]{4}', token), 'Choose an original cinematic')
    archive = Archive(original(game, 'assets/v2ta.viv', pins()['v2ta_sha256']))
    bundle = Archive(unpack(archive.read(token+'.viv')))
    return AnimationIndex(AnimationEnvelope.from_model(unpack(bundle.read(token+'.o'))))


def tracks(index, token, layout=None):
    layout = layout or CurveLayouts(index)
    result = []
    for role, suffix in (('body', '_s'), ('root', '_t')):
        require(token+suffix in index.lookup, 'This clip has no supported paired body/root tracks')
        parent = index.records[index.lookup[token+suffix]]
        _, _, duration, _ = parent_profile(layout, parent)
        require(0 < duration <= 3600, 'Preview clip exceeds 120 seconds at 30 ticks/second')
        for child in index.children[parent]:
            kind = index.record_types[child]
            if role == 'body' and kind == 18:
                curve = QuaternionCurve(layout, child); destinations = list(curve.destinations)
            elif role == 'body' and kind == 13:
                curve = TimedQuaternionCurve(layout, child)
                require(all(n % 12 == 4 for n in curve.destinations), 'Unsupported rotation destinations')
                destinations = [n//12 for n in curve.destinations]
            elif role == 'root' and kind == 20:
                curve = VectorCurve(layout, child)
                require(all(n % 12 == 8 for n in curve.destinations), 'Unsupported translation destinations')
                destinations = [n//12 for n in curve.destinations]
            else:
                raise ValueError(f'Preview does not decode {role} curve type {kind}')
            require(len(set(destinations)) == len(destinations) and all(0 <= n < 256 for n in destinations),
                    'Invalid animation destination set')
            result.append((role, kind, curve, destinations, duration))
    return result


def model_entries(raw):
    """Pinned CAF archives contain duplicate texture names; never compose them.

    Match the existing CAF reader's original-only directory bounds. Target model
    duplicates are refused below rather than weakening the general BIG parser.
    """
    require(raw[:4] in (b'BIGF',b'BIG4') and len(raw)>=16, 'Unsupported CAF archive')
    size=struct.unpack_from('<I',raw,4)[0];count,directory=struct.unpack_from('>II',raw,8)
    require(size==len(raw) and 0<count<=16384 and 16<=directory<=size, 'Invalid CAF archive bounds')
    at=16
    for _ in range(count):
        require(at+9<=directory,'Truncated CAF archive directory')
        offset,length=struct.unpack_from('>II',raw,at);at+=8
        end=raw.find(b'\0',at,min(at+256,directory))
        require(end>=at and directory<=offset<=size and length<=size-offset,'Invalid CAF model bounds')
        yield raw[at:end].decode('ascii'),raw[offset:offset+length]
        at=end+1


def rigs(game, names):
    require(type(names) is list and 0 < len(names) <= 32 and len(set(names)) == len(names), 'Invalid preview model list')
    require(all(type(n) is str and re.fullmatch(r'v2cp_[a-zA-Z0-9_]{1,90}', n) for n in names), 'Unsupported CAF model name')
    pending = {n.casefold(): n for n in names}; result = {}
    for filename, pin in baseline_pins()['archives'].items():
        entries=list(model_entries(original(game, 'assets/'+filename, pin)))
        for name in pending:
            require(sum(n[:-2].casefold()==name for n,_ in entries if n.lower().endswith('.o'))<=1,'Ambiguous original CAF model')
        for entry_name,raw in entries:
            key = entry_name[:-2].casefold() if entry_name.lower().endswith('.o') else ''
            if key not in pending: continue
            name = pending.pop(key); model = Model(unpack(raw)); skin = Skin(model)
            rows = skin.skeleton.rows
            meshes = {}
            for resource in skin.resources:
                match = re.fullmatch(r'__RM:::__GP_RM_.+_([0-9]+)', resource['resource'])
                require(match is not None, 'Unsupported preview render mesh identity')
                palette = resource['palette']
                selectors = skin.vertex_selectors[resource['resource']]
                meshes[match[1]] = dict(indices=[palette[n]['bones']+[0] for n in selectors],
                                       weights=[palette[n]['weights']+[0] for n in selectors])
            result[name] = dict(bones=[dict(parent=r[3],scale=list(r[:3]),quaternion=list(r[4:8]),position=list(r[8:11])) for r in rows], meshes=meshes,
                                topology=skin.skeleton.topology_sha256,source_sha256=hashlib.sha256(model.data).hexdigest())
        if not pending: break
    require(not pending, 'Preview source models not found: '+', '.join(pending.values()))
    return result


def animation(game, request):
    require(type(request) is dict and set(request) <= {'operation','core','clip','models'}, 'Unsupported animation request')
    if request.get('operation') == 'list':
        index = motion_index(game, request.get('core'))
        tokens = [name[:-2] for name in index.names if name.endswith('_s') and name[:-2]+'_t' in index.lookup]
        layout=CurveLayouts(index);supported=[];unsupported={}
        for token in tokens:
            try:tracks(index,token,layout);supported.append(token)
            except ValueError as error:unsupported[token]=str(error)
        return dict(clips=supported,unsupported=unsupported)
    require(request.get('operation', 'play') == 'play', 'Unknown animation operation')
    index = index_for(game, request); decoded = tracks(index, request['clip'])
    models = rigs(game, request.get('models')); count = min(len(r['bones']) for r in models.values())
    require(all(max(destinations, default=0) < count for _,_,_,destinations,_ in decoded), 'Clip exceeds the target skeleton')
    require(len({r['topology'] for r in models.values()}) == 1, 'Preview parts have different skeleton topologies')
    duration = max(row[4] for row in decoded)
    require(sum(len(row[3]) for row in decoded) * (duration+1) <= 400_000, 'Preview sample budget exceeded')
    channels = []
    for role, kind, curve, destinations, ticks in decoded:
        samples = [curve.sample(min(t, ticks), precision_bits=24) if kind == 13 else curve.sample(min(t, ticks))
                   for t in range(duration+1)]
        require(all(math.isfinite(n) and abs(n) < 1_000_000 for frame in samples for value in frame for n in value), 'Nonfinite preview pose')
        channels.append(dict(role=role,bones=destinations,samples=samples))
    return dict(schema='fighter-workshop-animation-1',clip=request['clip'],ticks=duration,ticks_per_second=30,
                models=models,channels=channels,notice='Source body/root tracks · 30 source ticks/s · no camera, face/hand palettes, events or runtime blending')
