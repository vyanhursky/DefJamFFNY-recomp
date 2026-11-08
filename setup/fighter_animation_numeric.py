"""Lossless typed18/20/21 block reconstruction for offline cinematic research.

Preserve seeds/deltas, dynamic/constant order, times and unused header bytes.
No resampling, raw native records or pointers enter the typed document. Caller
must supply a verified template control and an audited output allocation. This
module does not grant package/runtime admission to a cinematic bank.
"""
import math
import struct

from fighter_animation import require
from fighter_animation_graphs import fields, integer, array, matrix, pack_seed, unpack_seed, times
from fighter_animation_curves import CurveLayouts
from fighter_animation_scalars import f32

FORMAT = 'fighter-numeric-curve-draft-1'
MAX_KEYS = 4096


def read_numeric(layout, record):
    info = layout.records[record]
    kind, keys, channels, constants, shift = (info[k] for k in ('kind', 'keys', 'channels', 'constants', 'block_shift'))
    require(kind in (18, 20, 21) and keys <= MAX_KEYS, 'Unsupported numeric curve profile')
    dimension = 4 if kind == 18 else 3 if kind == 20 else 1
    width = 1 << shift
    if kind == 18:
        dynamic = list(layout.values(layout.pointer(record + 12, channels), channels, 'B')) if channels else []
        coefficients = [list(layout.values(record + 18 + 16*c, 8)) for c in range(channels)]
        at = record + 18 + 16*channels
    else:
        dynamic = list(layout.values(layout.pointer(record + 4, channels*2), channels)) if channels else []
        coefficients = [{'base': list(layout.values(record + 20 + 12*dimension*c, dimension, 'f')),
                         'extent': list(layout.values(record + 20 + 12*dimension*c + 4*dimension, dimension, 'f')),
                         'offset': list(layout.values(record + 20 + 12*dimension*c + 8*dimension, dimension)),
                         'range': list(layout.values(record + 20 + 12*dimension*c + 10*dimension, dimension))}
                        for c in range(channels)]
        at = record + 20 + 12*dimension*channels
    blocks = []
    for key in range(0, keys, width):
        count = min(width, keys-key)
        if kind == 18:
            seeds = [unpack_seed(layout.values(at + 6*c, 3)) for c in range(channels)]
            deltas = []
            for step in range(count-1):
                row = []
                for c in range(channels):
                    a,b,d = layout.values(at + 6*channels + 3*(step*channels+c), 3, 'B')
                    row.append([a>>2,b>>2,d>>2,((a&3)<<4)|((b&3)<<2)|(d&3)])
                deltas.append(row)
            at += 3*channels*(count+1)
            if count == width:
                at = (at+1)&~1
        else:
            seeds = [list(layout.values(at + 2*dimension*c, dimension)) for c in range(channels)]
            deltas = [[list(layout.values(at + 2*dimension*channels + dimension*(step*channels+c), dimension, 'B'))
                       for c in range(channels)] for step in range(count-1)]
            at = (at + dimension*channels*(count+1)+1)&~1
        blocks.append({'seeds': seeds, 'deltas': deltas})
    if kind == 18:
        destinations = list(layout.values(at, constants, 'B'))
        start = (at+constants+1)&~1
        static = [unpack_seed(layout.values(start+6*c,3)) for c in range(constants)]
    else:
        destinations = list(layout.values(at, constants))
        start = (at+2*constants+3)&~3
        static = [list(layout.values(start+4*dimension*c,dimension,'f')) for c in range(constants)]
    stamps = layout.times(record+8,keys,transitions=True,optional=True)
    return {'format': FORMAT, 'kind': kind, 'keys': keys, 'block_shift': shift,
            'destinations': dynamic, 'constant_destinations': destinations, 'coefficients': coefficients,
            'blocks': blocks, 'static': static, 'times': None if stamps is None else list(stamps),
            'unused_header': [] if kind == 18 else list(layout.values(record+18,2,'B'))}


def validate_numeric(value, output_floats):
    fields(value, 'format kind keys block_shift destinations constant_destinations coefficients blocks static times unused_header')
    require(value['format'] == FORMAT and type(value['kind']) is int and value['kind'] in (18,20,21), 'Unsupported numeric document')
    integer(output_floats,1,49152)
    kind = value['kind']; dimension = 4 if kind == 18 else 3 if kind == 20 else 1
    keys,shift = integer(value['keys'],1,MAX_KEYS),integer(value['block_shift'],0,8)
    dynamic = array(value['destinations'],0,255)
    static = array(value['constant_destinations'],0,255)
    destinations = dynamic+static
    require(len(destinations) <= 256 and len(set(destinations)) == len(destinations), 'Numeric destinations duplicate or exceed budget')
    for destination in destinations:
        integer(destination,0,255 if kind == 18 else 65535)
        require((12*destination+8 if kind == 18 else destination+dimension) <= output_floats,
                'Numeric destination escapes output allocation')
    times(value['times'],keys-1,optional=True)
    if kind == 18:
        require(value['unused_header'] == [], 'Quaternion header has no unused vector bytes')
        matrix(value['coefficients'],len(dynamic),8,65535)
        matrix(value['static'],len(static),4,4095)
    else:
        matrix([value['unused_header']],1,2,255)
        for coefficient in array(value['coefficients'],len(dynamic),len(dynamic)):
            fields(coefficient,'base extent offset range')
            for name in ('base','extent'):
                for v in array(coefficient[name],dimension,dimension):
                    require(type(v) in (int,float) and math.isfinite(v) and abs(v)<=1_000_000, 'Invalid numeric coefficient')
                    f32(v)
            matrix([coefficient['offset'],coefficient['range']],2,dimension,65535)
        for row in array(value['static'],len(static),len(static)):
            for v in array(row,dimension,dimension):
                require(type(v) in (int,float) and math.isfinite(v) and abs(v)<=1_000_000, 'Invalid numeric constant')
                f32(v)
    width = 1<<shift
    blocks = array(value['blocks'],(keys+width-1)//width,(keys+width-1)//width)
    for index,block in enumerate(blocks):
        fields(block,'seeds deltas')
        count = min(width,keys-index*width)
        matrix(block['seeds'],len(dynamic),dimension,4095 if kind == 18 else 65535)
        for row in array(block['deltas'],count-1,count-1):
            matrix(row,len(dynamic),dimension,63 if kind == 18 else 255)


def write_numeric(writer, value, control, output_floats):
    validate_numeric(value,output_floats)
    integer(control,0,65535)
    kind,keys,shift = value['kind'],value['keys'],value['block_shift']
    channels,constants = len(value['destinations']),len(value['constant_destinations'])
    dimension = 4 if kind == 18 else 3 if kind == 20 else 1
    if kind == 18:
        data = bytearray(struct.pack('<HHHBBIIBB',kind,control,keys,channels,constants,0,0,shift,0))
        data.extend(b''.join(struct.pack('<8H',*c) for c in value['coefficients']))
    else:
        data = bytearray(struct.pack('<HHIIHH4B',kind,control,0,0,keys,channels,shift,constants,*value['unused_header']))
        for c in value['coefficients']:
            data.extend(struct.pack('<'+'f'*(2*dimension)+'H'*(2*dimension),*c['base'],*c['extent'],*c['offset'],*c['range']))
    width = 1<<shift
    for index,block in enumerate(value['blocks']):
        count = min(width,keys-index*width)
        for row in block['seeds']:
            data.extend(pack_seed(row) if kind == 18 else struct.pack('<'+'H'*dimension,*row))
        for step in block['deltas']:
            for row in step:
                if kind == 18:
                    a,b,c,d = row
                    data.extend(bytes(((a<<2)|(d>>4),(b<<2)|((d>>2)&3),(c<<2)|(d&3))))
                else:
                    data.extend(bytes(row))
        if kind != 18 or count == width:
            data.extend(bytes(-len(data)%2))
    data.extend(bytes(value['constant_destinations']) if kind == 18 else
                struct.pack('<'+'H'*constants,*value['constant_destinations']))
    data.extend(bytes(-len(data)%(2 if kind == 18 else 4)))
    for row in value['static']:
        data.extend(pack_seed(row) if kind == 18 else struct.pack('<'+'f'*dimension,*row))
    at = writer.append(data)
    if channels:
        raw = bytes(value['destinations']) if kind == 18 else struct.pack('<'+'H'*channels,*value['destinations'])
        writer.pointer(at+(12 if kind == 18 else 4),writer.append(raw))
    if value['times'] is not None:
        writer.pointer(at+8,writer.append(struct.pack('<'+'H'*len(value['times']),*value['times'])))
    return at
