"""Reconcile legacy shared files with typed component-export receipts, offline.

This is a source-fidelity audit, not native acceptance or an installer. All
outputs remain private. Original files and the supplied extraction are read only.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'setup'))
from fighter_build import retail_catalog
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_motion import MotionIndex
from fighter_motion_records import PackedRecord
from fighter_sod import Database,CHARACTER
from fighter_timelines import TagTimelines,CameraTimelines,tag_rows,camera_rows


def sha(data):return hashlib.sha256(data).hexdigest()
def doc(path):return json.loads(path.read_text(encoding='utf-8'))
def need(condition,message):
    if not condition:raise ValueError(message)


def audit(source,game,pair_root,film_root,motion_report):
    rows={};inputs={}
    def read(relative,original=False):
        data=(unpack(Archive((game/'assets/nis.viv').read_bytes()).read(relative))
              if original and relative=='assets/IntroExtro.xml' else ((game if original else source)/relative).read_bytes())
        if not original:inputs[relative]=sha(data)
        return data
    catalog=retail_catalog(game/'assets/djv2.sod')
    original=Database(read('assets/djv2.sod',True));changed=Database(read('assets/djv2.sod'))
    original_names={row['name'] for row in catalog.rows.values()}
    added=[row for row in changed.character_metadata()['characters'] if row['name'] not in original_names]
    actors={row['source_core']:row for row in motion_report['fighters']}
    need(len(added)==len(actors)==46,'Added roster population differs')
    need(original.schema==changed.schema and changed.strings[:len(original.strings)]==original.strings,
         'SOD schema/original strings changed')
    # Five pointer/count words are the ONLY modifications to the complete
    # original byte prefix. Derive inline index-value sites from native layout.
    header=original.directory[CHARACTER];allowed={20,header+12}
    for offset in original.words(header+4,2):
        count,stride=original.words(offset,2)
        need(stride==1,'Unexpected Character member map')
        allowed.update(offset+8+4*count+4*i for i in range(count))
    diffs={i for i in range(len(original.data)) if original.data[i]!=changed.data[i]}
    need(all(i//4*4 in allowed for i in diffs),'Source changes unrelated original SOD bytes')
    tier_counts=Counter()
    for row in added:
        actor=actors[row['native_binding']['core_id']];donor=catalog.rows[actor['donor']]
        before=original.words(donor['record_offset'],26);after=changed.words(row['record_offset'],26)
        need(all(before[i]==after[i] for i in range(26) if i not in {0,5,8,10,14,24}),
             'Unaccounted added-character field change')
        need(changed.field('Character','Tier')==(24,6) and after[24] in (1,2,4,8),'Unproved source Tier')
        tier_counts[after[24]]+=1
    rows['assets/djv2.sod']={'passed':True,'original_records':75,'added_records':46,
        'changed_original_word_sites':sorted({i//4*4 for i in diffs}),'tiers':dict(tier_counts)}

    baseline=MotionIndex(read('motion/main_all.dat',True));source_motion=MotionIndex(read('motion/main_all.dat'))
    mapping=motion_report['finisher_behavior']['mapping'];owned=set(actors);padding=0
    for core,actor in actors.items():
        record=source_motion.record('core',core-1);values=list(record.values)
        donor_core=catalog.rows[actor['donor']]['native_binding']['core_id']
        donor=baseline.record('core',donor_core-1)
        need(values[88:92]==actor['slots'],'Source four-slot mapping differs from motion receipt')
        need(source_motion.cores[core-1]['moves_sha256']==baseline.cores[donor_core-1]['moves_sha256'],
             'Unaccounted source WWAZ change')
        values[88:92]=donor.values[88:92]
        rebuilt=PackedRecord('core',tuple(values),record.tail)
        need(rebuilt.native_bytes()==donor.native_bytes(),'Source core contains unconverted behavior')
        padding+=record.tail!=donor.tail
    for i in range(len(source_motion.cores)):
        if i+1 not in owned:
            need(i<len(baseline.cores) and source_motion.record('core',i).encode()==baseline.record('core',i).encode(),
                 'Source changes an unowned character core')
    rows['motion/main_all.dat']={'passed':True,'added_cores':len(source_motion.cores)-len(baseline.cores),
        'mapped_source_cores':46,'ignored_native_unpack_padding_differences':padding,
        'shared_behavior_proof':motion_report['finisher_behavior']}

    tags=TagTimelines(read('audio/animtags.dat',True),sha(read('audio/animtags.dat',True)))
    additions={};overrides={};pairs=0;source_tokens=set()
    def descriptor(folder,item):
        data=(folder/item['path']).read_bytes();need(sha(data)==item['sha256'],'Export changed after compilation')
        return json.loads(data)
    for folder in sorted(pair_root.iterdir()):
        if not folder.is_dir() or not (folder/'pair-export.json').is_file():continue
        report=doc(folder/'pair-export.json');fragment=doc(folder/'pair-source.json');pairs+=1
        for path,digest in report['inputs'].items():
            path=Path(path)
            need(path.is_relative_to(source) and sha(path.read_bytes())==digest,'Pair input receipt changed')
            inputs[path.relative_to(source).as_posix()]=digest
        for role in ('subject','counterpart'):
            claim=report['roles'][role];token=claim['source_token'];source_tokens.add(token)
            value={'template':claim['template_token'],'timeline':descriptor(folder,fragment[role+'_tags'])}
            if token in tags.by_name:
                overrides[token]={'original_sha256':sha(tags.by_name[token]['raw']),**value}
            else:additions[token]=value
    need(pairs==47 and len(source_tokens)==94 and len(overrides)==10,'Pair tag population differs')
    before_names=unpack(Archive((game/'motion/blazin.viv').read_bytes()).read('blazin.mnl'))
    after_names=unpack(read('motion/blazin/blazin.mnl'))
    def tokens(data):
        count,size=struct.unpack_from('<2I',data)
        need(size==0 and data.endswith(b'.'),'Unsupported paired name envelope')
        values=data[8:-1].decode('ascii').split('.')
        need(len(values)==count and len(set(values))==count,'Paired names are not unique')
        return values
    original_tokens=tokens(before_names);added_tokens=tokens(after_names)
    need(len(original_tokens)==164 and added_tokens[:164]==original_tokens
         and len(added_tokens)==258 and set(added_tokens[164:])==source_tokens,'Unaccounted paired names')
    rows['motion/blazin/blazin.mnl']={'passed':True,'original_prefix_names':164,'owned_added_names':94,
        'all_source_names_accounted':True}
    films=0
    for folder in sorted(film_root.iterdir()):
        if not folder.is_dir() or not (folder/'cinematic-export.json').is_file():continue
        report=doc(folder/'cinematic-export.json');fragment=doc(folder/'cinematic-source.json');films+=1
        for path,digest in report['inputs'].items():
            path=Path(path)
            need(path.is_relative_to(source) and sha(path.read_bytes())==digest,'Cinematic input receipt changed')
            inputs[path.relative_to(source).as_posix()]=digest
        token=report['source_token']
        if fragment['tags']=={'state':'absent'}:continue
        profile=('cinematic-intro-1' if token.startswith('CI_') else
                 'cinematic-victory-1' if token.startswith('CE_') else 'cinematic-activation-1')
        need(token not in additions and token not in tags.by_name,'Cinematic tag identity collides')
        additions[token]={'profile':profile,'timeline':descriptor(folder,fragment['tags'])}
    need(films==184,'Cinematic population differs')
    source_tag_data=read('audio/animtags.dat')
    need(tags.compose(additions,overrides=overrides)==source_tag_data,'Typed timelines do not reconstruct complete source TAGS')
    rows['audio/animtags.dat']={'passed':True,'byte_exact_typed_reconstruction':True,
        'new_rows':len(additions),'explicit_existing_row_overrides':len(overrides),'total_rows':len(tag_rows(source_tag_data))}
    before=camera_rows(read('motion/camera.xml',True));after=camera_rows(read('motion/camera.xml'))
    cameras=CameraTimelines(read('motion/camera.xml',True),sha(read('motion/camera.xml',True)))
    need(after[:len(before)]==before and len(after)-len(before)==47,'Original camera schedules changed')
    for row in after[len(before):]:cameras.library.export(row['events'])
    shadowed=[row['name'] for row in after[len(before):] if row['name'] in cameras.by_name]
    need(len(shadowed)==5,'Shadowed camera population differs')
    rows['motion/camera.xml']={'passed':True,'original_rows':len(before),'appended_rows':47,
        'shadowed_appended_labels':shadowed,'policy':'Native first match; appended duplicates are unused'}

    # Whole XML additions are simple registrations. Two dangling registrations
    # have no Character reference or source appearance, and are reported rather
    # than promoted into playable fighters or substituted with donor assets.
    expected={actor['model'] for actor in actors.values()};unbound={'V2IP_606A','V2IP_607A'}
    for relative,closing,tag in [('assets/IntroExtro.xml',b'</tauntslist>','taunt'),
                                ('assets/entity.xml',b'</entitylist>','entity')]:
        before=read(relative,True);after=read(relative)
        if tag=='taunt':
            at=before.index(closing);need(after[:at]==before[:at] and after.endswith(before[at:]),'Original cinematic XML changed')
            new_nodes=ET.fromstring(after)[len(ET.fromstring(before)):]
            need(len(new_nodes)==48 and {node.findtext('name') for node in new_nodes}==expected|unbound,
                 'Unexpected cinematic registrations')
            for node in new_nodes:
                name=node.findtext('name');suffix=name.removeprefix('V2IP_')
                clips=('CI_'+suffix,'CE_'+suffix) if name in expected else (
                    ('CI_301A','CE_301A') if suffix=='606A' else ('CI_123A','CE_123A'))
                need([child.tag for child in node]==['name','intro','extro']
                     and (node.findtext('intro'),node.findtext('extro'))==clips,'Cinematic registration has unconverted controls')
        else:
            at=43040;need(after[:at]==before[:at] and after[at+7488:]==before[at:],'Original entity XML changed')
            new_nodes=ET.fromstring(b'<insert>'+after[at:at+7488]+b'</insert>')
            need(len(new_nodes)==48 and {node.findtext('name') for node in new_nodes}==expected|unbound,
                 'Unexpected entity registrations')
            for node in new_nodes:
                name=node.findtext('name')
                def shape(element):
                    return (element.tag,element.attrib,(element.text or '').strip(),tuple(shape(child) for child in element))
                target=ET.fromstring('<entity><name>'+name+'</name><model><name>'+name+'</name><texture><name>'+name+'</name></texture></model></entity>')
                need(shape(node)==shape(target),'Entity registration has unconverted controls')
        referenced={row['fields']['Model']['symbol'] for row in changed.character_metadata()['characters']}
        need(not unbound&referenced and not any((source/'assets/v2ip'/(name+suffix)).exists()
             for name in unbound for suffix in ('.o','.xsh','_F.o')),'Excluded registration is a source fighter dependency')
        rows[relative]={'passed':True,'converted_fighter_registrations':46,
            'excluded_unbound_registrations':sorted(unbound),'original_bytes_preserved':True,
            'exclusion_reason':'No Character references or source/original appearance payload; not a playable source fighter'}
    source_by_core={row['native_binding']['core_id']:row for row in added};activation=[];source_tags={row['name']:row for row in tag_rows(source_tag_data)}
    for line in read('blazin_activation.txt').decode().splitlines():
        words=line.split('#',1)[0].split()
        if not words:continue
        need(len(words) in (3,4) and (len(words)==3 or words[3]=='cri'),'Unknown activation annotation')
        core=int(words[0]);suffix=source_by_core[core]['fields']['Model']['symbol'].removeprefix('V2IP_')
        need(words[1:3]==['BZ_'+suffix,'BY_'+suffix],'Activation differs from actual model')
        need('BY_'+suffix not in source_tags,'Unexpected BY callbacks')
        events=source_tags.get(words[1],{}).get('events')
        need(events==([(4,[65,[4]]),(12,[65,[4]]),(20,[65,[4]])] if len(words)==4 else None),'Activation annotation differs from typed tags')
        activation.append(core)
    need(len(activation)==46 and set(activation)==owned,'Activation roster differs')
    rows['blazin_activation.txt']={'passed':True,'fighters':46,'annotation_preserved_by_actual_tags':True,
        'phase4_camera_policy':'Owned absolute; additional legacy runtime reference aca317a0a84dd6522dd68f02ef7a5e82fb749989, src/recomp_manual.c lines1219-1234',
        'phase4_policy_evidence':'https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1219-L1234'}
    return {'schema':'fighter-conversion-global-audit-1','rows':rows,'inputs':inputs,
            'source_tiers':{str(row['native_binding']['core_id']):row['fields']['Tier']['word'] for row in added},
            'native_acceptance':False,'complete_faithfulness':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','game','pair-root','film-root','motion-report','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();need(not args.out.exists(),'Choose a new report path')
    report=audit(args.source.resolve(),args.game.resolve(),args.pair_root,args.film_root,doc(args.motion_report))
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'shared_files':len(report['rows']),'input_receipts':len(report['inputs']),'passed':True}))


if __name__=='__main__':main()
