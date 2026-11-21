"""Bounded neck/torso normal overrides; no topology, pointers or programs."""
import math
MAX_NORMALS = 128

def unpack(word):
    out=[]
    for shift,bits in ((0,11),(11,11),(22,10)):
        v=(word>>shift)&((1<<bits)-1)
        if v&(1<<(bits-1)):v-=1<<bits
        out.append(max(-1.,v/((1<<(bits-1))-1)))
    length=math.sqrt(sum(v*v for v in out))
    if length<.5:raise ValueError('Degenerate packed normal')
    return [v/length for v in out]

def validate(rows):
    if type(rows) is not list or not 0<len(rows)<=MAX_NORMALS:raise ValueError('Invalid neck normal count')
    seen=set()
    for r in rows:
        if type(r) is not dict or set(r)!={'slot','rm','vertex','position','original','replacement'}:raise ValueError('Invalid neck normal fields')
        if any(type(r[k]) is not int for k in ('slot','rm','vertex','original','replacement')):raise ValueError('Invalid normal integer')
        if r['slot'] not in (3,12) or not 0<=r['rm']<16 or not 0<=r['vertex']<1024:raise ValueError('Normal outside neck/torso scope')
        key=(r['slot'],r['rm'],r['vertex'])
        if key in seen:raise ValueError('Duplicate normal vertex')
        seen.add(key)
        p=r['position']
        if type(p) is not list or len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) or not (abs(p[0])<=1.1 and 17.5<=p[1]<=19.5 and abs(p[2])<=1.1):raise ValueError('Normal outside neck boundary bounds')
        if not all(0<=r[k]<=0xffffffff for k in ('original','replacement')):raise ValueError('Packed normal outside uint32')
        a,b=unpack(r['original']),unpack(r['replacement'])
        if sum(x*y for x,y in zip(a,b))<math.cos(math.radians(35)):raise ValueError('Normal rotation exceeds 35 degrees')
    return rows
