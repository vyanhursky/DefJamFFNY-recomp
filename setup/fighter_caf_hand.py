"""Bounded participant-owned left-finger pose; no caller-supplied destinations.

The reviewed CE_113A hand controller evaluates _s then _p. Replace only its
left palette writer with a dense native type13 writer, keeping the original
right palette leaf. The global hand palette and retail bank stay untouched.
"""
import copy
import math
from bisect import bisect_right
from fighter_animation import require
from fighter_animation_scalars import f32
from fighter_animation_timed_quaternions import blend

DESTINATIONS = tuple(b * 12 + 4 for b in (21,22,23,24,26,25,27,28,29,34,33,35,30,31,32))
FORMAT = 'fighter-native-left-hand-1'


def validate_hand(value, template):
    require(template == 'CE_113A', 'Left fingers require the reviewed CE_113A hand controller')
    require(type(value) is dict and set(value) == {'format','pose','envelope'}
            and value['format'] == FORMAT, 'Unsupported left-hand document')
    pose=value['pose']
    require(type(pose) is list and len(pose)==15, 'Left hand needs exactly fifteen native finger quaternions')
    for q in pose:
        require(type(q) is list and len(q)==4 and all(type(v) in (int,float) and math.isfinite(v)
                and abs(v)<=1 for v in q) and abs(sum(v*v for v in q)-1)<.0002,
                'Finger quaternion must be finite and unit length')
    rows=value['envelope'];require(type(rows) is list and 2<=len(rows)<=16, 'Hand envelope exceeds budget')
    previous=-1
    for row in rows:
        require(type(row) is list and len(row)==2 and type(row[0]) is int and previous<row[0]<=106
                and type(row[1]) in (int,float) and math.isfinite(row[1]) and 0<=row[1]<=1,
                'Hand envelope requires bounded increasing source ticks and weights')
        previous=row[0]
    require(rows[0]==[0,0] and rows[-1]==[106,0], 'Hand must return to its donor pose at both endpoints')
    return value


def weight_at(rows,tick):
    i=max(0,bisect_right([r[0] for r in rows],tick)-1)
    if i==len(rows)-1:return rows[i][1]
    a,b=rows[i:i+2];w=(tick-a[0])/(b[0]-a[0]);w=w*w*(3-2*w)
    return a[1]+(b[1]-a[1])*w


def palette_at(leaf,palette,tick):
    times=leaf['times'];i=max(0,bisect_right(times,tick)-1)
    if i==len(times)-1 or tick<=times[0] or tick==times[i]:return palette.frames[leaf['samples'][i]]
    w=f32(f32(tick-times[i])/(times[i+1]-times[i]));w=f32(f32(f32(3.-f32(w*2.))*w)*w)
    return [blend(a,b,w,precision_bits=24) for a,b in zip(palette.frames[leaf['samples'][i]],palette.frames[leaf['samples'][i+1]])]


def hand_leaf(poses):
    # All channels use the native sixteen-bit scalar accumulator. Multiple
    # four-bit quaternion groups are deliberately refused by the decoder.
    flat=[[f32(v) for q in pose for v in q] for pose in poses];coefficients=[];deltas=[[0]*60 for _ in poses[1:]]
    for c in range(60):
        differences=[b[c]-a[c] for a,b in zip(flat,flat[1:])];low,high=min(differences),max(differences)
        offset,scale=f32(low),f32((high-low)/65535) if high!=low else 0.
        coefficients.append([offset,scale,flat[0][c]])
        for k,d in enumerate(differences):deltas[k][c]=max(0,min(65535,round((d-offset)/scale))) if scale else 0
    from fighter_caf_mouth import decoded_jaw
    leaf=dict(kind=13,destinations=list(DESTINATIONS),times=list(range(1,107)),bits=16,coefficients=coefficients,deltas=deltas)
    decoded=decoded_jaw(leaf)
    require(max(abs(a-b) for p,q in zip(flat,decoded) for a,b in zip(p,q))<.0002,'Finger quantization exceeds error budget')
    require(all(abs(sum(v*v for v in row[c:c+4])-1)<.001 for row in decoded for c in range(0,60,4)), 'Quantized finger norm differs')
    return leaf


def apply_graphs(graphs,value,token,hands):
    validate_hand(value,token);result=copy.deepcopy(graphs);require(set(result)=={token+'_p'},'Unexpected hand donor parent')
    parent=result[token+'_p'];children=parent['children']
    require(parent['duration_ticks']==106 and parent['time_scale']==29 and len(children)==2
            and [x['kind'] for x in children]==[25,25] and [x['selector'] for x in children]==[0,1], 'Hand donor shape differs')
    palette=hands.palettes[0]
    require(tuple(palette.quaternion_destinations)==DESTINATIONS and not palette.vector_destinations,
            'Left hand palette does not match the verified native finger destination set')
    poses=[]
    for tick in range(107):
        original=palette_at(children[0],palette,tick);weight=weight_at(value['envelope'],tick)
        poses.append(original if weight==0 else [blend(a,b,weight,precision_bits=24) for a,b in zip(original,value['pose'])])
    result[token+'_s']=dict(duration_ticks=106,time_scale=29,children=[hand_leaf(poses)])
    # Leave the selector1 leaf itself unchanged. The _p writer would otherwise
    # overwrite the new selector0 _s pose on every native evaluation.
    parent['children']=[children[1]]
    return result
