"""Convert source paired event timelines through verified payload references.

Uses the original native first-match camera lookup. Duplicate source camera
schedules remain explicitly reported as shadowed; choosing the last appended
row would change effective source behavior. No source XML/native tag records
are copied into packages. Output is an audit receipt, optionally typed sources.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'setup'))
from fighter_animation import require
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_timelines import TagTimelines,CameraTimelines,tag_rows,camera_rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--game',type=Path,default=ROOT/'game')
    parser.add_argument('--motion-report',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--export-root',type=Path)
    args=parser.parse_args()
    require(not args.out.exists(),'Choose a new timeline audit report')
    require(args.export_root is None or not args.export_root.exists(),'Choose a new typed timeline export folder')
    pins=json.loads((ROOT/'config/fighter-native-baseline.json').read_text())
    tags=TagTimelines((args.game/'audio/animtags.dat').read_bytes(),pins['tags_sha256'])
    cameras=CameraTimelines((args.game/'motion/camera.xml').read_bytes(),pins['camera_sha256'])
    source_tags={row['name']:row for row in tag_rows((args.source/'audio/animtags.dat').read_bytes())}
    source_cameras=camera_rows((args.source/'motion/camera.xml').read_bytes())
    paired=Archive((args.game/'motion/blazin.viv').read_bytes())
    require(hashlib.sha256(paired.data).hexdigest()==pins['blazin_sha256'],'Original paired archive differs')
    retail_tokens=unpack(paired.read('blazin.mnl'))[8:-1].decode().split('.')
    source_tokens=unpack((args.source/'motion/blazin/blazin.mnl').read_bytes())[8:-1].decode().split('.')
    mapping=json.loads(args.motion_report.read_text())['finisher_behavior']['mapping']
    added_tags,added_cameras,rows={}, {}, []
    staged=[]
    for ordinal,(choice,template) in enumerate(sorted((int(k),v) for k,v in mapping.items())):
        item={'source_choice':choice,'template_choice':template,'roles':{}}
        fragments={}
        for role,offset in (('subject',0),('counterpart',1)):
            source_token,retail=source_tokens[2*choice+offset],retail_tokens[2*template+offset]
            assigned=f'P{ordinal:04d}_'+('A' if offset==0 else 'B')
            source=tags.library.export(source_tags[source_token]['events'])
            added_tags[assigned]={'template':retail,'timeline':source}
            fragments[role+'_tags']=source
            item['roles'][role]={'source_name':source_token,'template_name':retail,'assigned_name':assigned,
                                  'events':len(source['events'])}
        token=source_tokens[2*choice]
        candidates=[row for row in source_cameras if row['name']==token]
        require(candidates,'Source motion has no camera schedule')
        effective=candidates[0]
        template_name=token if token in cameras.by_name else retail_tokens[2*template]
        timeline=cameras.library.export(effective['events'])
        assigned=item['roles']['subject']['assigned_name']
        added_cameras[assigned]={'template':template_name,'timeline':timeline}
        fragments['camera']={'template':template_name,'timeline':timeline}
        item['camera']={'source_name':token,'template_name':template_name,'assigned_name':assigned,
                        'events':len(timeline['events']),'selection':'first-native-match',
                        'shadowed_schedules':[{'events':len(row['events']),
                                              'sha256':hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()}
                                             for row in candidates[1:]]}
        rows.append(item);staged.append((choice,fragments))
    tag_bytes=tags.compose(added_tags)
    camera_bytes=cameras.compose(added_cameras)
    report={'schema':'fighter-conversion-timeline-audit-1','rows':rows,
            'summary':{'pairs':len(rows),'tag_rows':len(added_tags),
                       'tag_events':sum(role['events'] for row in rows for role in row['roles'].values()),
                       'camera_rows':len(added_cameras),'camera_events':sum(row['camera']['events'] for row in rows),
                       'shadowed_camera_rows':sum(len(row['camera']['shadowed_schedules']) for row in rows)},
            'compiled_tags_sha256':hashlib.sha256(tag_bytes).hexdigest(),
            'compiled_cameras_sha256':hashlib.sha256(camera_bytes).hexdigest(),
            'source_policy':'Preserve effective native first-match schedules; retain shadowed alternatives in accounting',
            'native_playtest':False,'complete_conversion':False}
    if args.export_root is not None:
        args.export_root.mkdir(parents=True)
        for choice,fragments in staged:
            folder=args.export_root/str(choice);folder.mkdir()
            for name,value in fragments.items():
                (folder/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as output:output.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary']))


if __name__=='__main__':main()
