"""Native-clock retiming preserves complete verified event payloads and order."""
import copy
import hashlib
from pathlib import Path
import struct
import sys

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_assets import AssetError
from fighter_timelines import TagTimelines,CameraTimelines,tag_rows,camera_rows


def tags():
    rows=[]
    for name,events in [('A106',[(0,65,[4])]),('N0001_A',[(1,1,[2]),(2,1,[2]),(2,25,[1,0,0,0,0])])]:
        row=bytearray(name.encode().ljust(8,b'\0')[::-1]+struct.pack('<I',len(events)))
        for tick,opcode,args in events:
            row.extend(struct.pack('<3h',tick,len(args),opcode)+struct.pack('<'+'h'*len(args),*args))
        rows.append(bytes(row))
    data=b'TAGS'+struct.pack('<3I',2,16,16+len(rows[0]))+b''.join(rows)
    return TagTimelines(data,hashlib.sha256(data).hexdigest())


def cameras():
    data=(b'<specialcamera>\r\n<?opaque verified metadata\x80>\r\n<timetable><name>N0001_A</name>'
          b'<frame>1,A,B,0,C,S</frame><frame>2,0,0,shake,M,0</frame>'
          b'<frame>3,0,0,back,0,0</frame></timetable>'
          b'<timetable><name>Z1</name><frame>1,0,0,shake,S,0</frame></timetable></specialcamera>')
    return CameraTimelines(data,hashlib.sha256(data).hexdigest())


def test_tag_retiming_preserves_native_payload_order_and_original_rows():
    bank=tags();source=bank.library.export(bank.by_name['N0001_A']['events'])
    for event,tick in zip(source['events'],[4,32767,32767]):event['tick']=tick
    output=bank.compose({'P0000_A':{'template':'N0001_A','timeline':source}})
    rows={row['name']:row for row in tag_rows(output)}
    assert all(rows[row['name']]['raw']==row['raw'] for row in bank.rows)
    assert [tick for tick,_ in rows['P0000_A']['events']]==[4,32767,32767]
    assert [payload for _,payload in rows['P0000_A']['events']]==[payload for _,payload in bank.by_name['N0001_A']['events']]
    with pytest.raises(AssetError,match='sequence differs'):
        bank.compose({'P0000_A':{'template':'A106','timeline':source}})
    source['events'].reverse()
    for event,tick in zip(source['events'],[1,2,3]):event['tick']=tick
    with pytest.raises(AssetError,match='sequence differs'):
        bank.compose({'P0000_A':{'template':'N0001_A','timeline':source}})


def test_explicit_existing_tag_override_checks_original_row_and_donor_sequence():
    bank=tags();timeline=bank.library.export(bank.by_name['N0001_A']['events'])
    value={'original_sha256':hashlib.sha256(bank.by_name['A106']['raw']).hexdigest(),
           'template':'N0001_A','timeline':timeline}
    rows={row['name']:row for row in tag_rows(bank.compose({},overrides={'A106':value}))}
    assert rows['N0001_A']['raw']==bank.by_name['N0001_A']['raw']
    assert rows['A106']['events']==bank.by_name['N0001_A']['events']
    with pytest.raises(AssetError,match='original target row'):
        bank.compose({},overrides={'A106':{**value,'original_sha256':'0'*64}})
    with pytest.raises(AssetError,match='sequence differs'):
        bank.compose({},overrides={'A106':{**value,'template':'A106'}})
    with pytest.raises(AssetError,match='collides'):
        bank.compose({'A106':{'template':'N0001_A','timeline':timeline}})


def test_camera_retiming_and_shake_selection_keep_nonshake_sequence():
    bank=cameras();events=bank.by_name['N0001_A']['events']
    events=[events[0],bank.by_name['Z1']['events'][0],events[2]]
    source=bank.library.export([(10,payload) if i==0 else (20*i,payload) for i,(_,payload) in enumerate(events)])
    output=bank.compose({'P0000_A':{'template':'N0001_A','timeline':source}})
    assert output.startswith(bank.data[:bank.data.index(b'</specialcamera>')])
    rows=camera_rows(output)
    assert rows[:2]==bank.rows and [tick for tick,_ in rows[-1]['events']]==[10,20,40]
    wrong=copy.deepcopy(source);wrong['events'][0]['template']=wrong['events'][1]['template']
    with pytest.raises(AssetError,match='non-shake sequence'):
        bank.compose({'P0000_A':{'template':'N0001_A','timeline':wrong}})


@pytest.mark.parametrize('change',[lambda s:s['events'][0].update(tick=True),
    lambda s:s['events'][0].update(tick=-1),lambda s:s['events'][0].update(tick=32768),
    lambda s:s['events'][0].update(template='native/opcode-65'),lambda s:s['events'][0].update(opcode=65),
    lambda s:s.update(code='execute')])
def test_untrusted_timeline_values_rejected(change):
    bank=tags();source=bank.library.export(bank.by_name['A106']['events']);change(source)
    with pytest.raises(AssetError):bank.library.compile(source)


def test_tag_row_offsets_names_and_counts_fail_closed():
    bank=tags()
    for offset,value in [(4,65536),(8,0),(12,16)]:
        data=bytearray(bank.data);struct.pack_into('<I',data,offset,value)
        with pytest.raises(AssetError):tag_rows(bytes(data))
    with pytest.raises(AssetError,match='verified original'):TagTimelines(bank.data,'0'*64)
    with pytest.raises(AssetError,match='collides'):bank.compose({'A106':{}})


def test_camera_order_and_duplicate_baseline_names_are_explicit():
    bank=cameras();source=bank.library.export(bank.by_name['N0001_A']['events'])
    source['events'][1]['tick']=source['events'][0]['tick']
    with pytest.raises(AssetError,match='ordered native clock'):bank.library.compile(source)
    duplicate=bank.data.replace(b'<name>Z1</name>',b'<name>N0001_A</name>')
    assert len(camera_rows(duplicate))==3-1
    with pytest.raises(AssetError,match='duplicate identities'):
        CameraTimelines(duplicate,hashlib.sha256(duplicate).hexdigest())
