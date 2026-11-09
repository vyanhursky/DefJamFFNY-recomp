"""Join sealed full-component audits into an exhaustive local input ledger.

Converted denotes offline typed conversion. It never substitutes for native
acceptance, platform testing, or a resolved legacy camera-policy ambiguity.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def document(path):return json.loads(path.read_text(encoding='utf-8'))
def need(condition,message):
    if not condition:raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','previous','global-report','grid-report','appearance-pack','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();need(not args.out.exists(),'Choose a new report path')
    source=args.source.resolve();report=document(args.previous);global_report=document(args.global_report);grid=document(args.grid_report)
    need(report['schema']=='fighter-conversion-source-accounting-1'
         and global_report['schema']=='fighter-conversion-global-audit-1'
         and grid['schema']=='fighter-grid-source-audit-1','Unsupported audit receipt')
    files={row['path']:row for row in report['files']}
    need(len(files)==1883 and set(files)=={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()},'Source population changed')
    for name,row in files.items():
        data=(source/name).read_bytes()
        need(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'Source hash changed: '+name)
    def claim(name,digest,reason,evidence):
        need(name in files and files[name]['sha256']==digest,'Audit input differs: '+name)
        if files[name]['status']=='blocked':files[name].update(status='converted',reason=reason,evidence=evidence)
    for name,digest in global_report['inputs'].items():
        claim(name,digest,'Hash-sealed component export or complete shared-file semantic reconstruction',args.global_report.name)
    for name,row in global_report['rows'].items():
        need(row['passed'],'Shared-file audit did not pass')
        need(name in global_report['inputs'],'Shared-file audit omitted input hash')
        files[name]['semantic_audit']=row
    for row in grid['rows']:
        need(row['passed'] and row['original_actions_constants_and_drawables_preserved']
             and row.get('complete_native_model_tail_verified') is True,'Grid source audit incomplete')
        claim(row['path'],row['sha256'],'All original script/drawables preserved;92 independent normal/selected state closures rebuilt',args.grid_report.name)
    pack=document(args.appearance_pack/'fighters.json')
    resource_by_key={pack['id']+'/'+row['id']:row for row in pack['resources']}
    extra_models=[]
    for override in pack['overrides']:
        if set(override['components'])!={'appearance'}:continue
        resource=resource_by_key[override['components']['appearance']];spec=resource['source']
        need(spec['format']=='eagl-appearance-2','Extra appearance lacks explicit texture names')
        data=(args.appearance_pack/spec['model']['path']).read_bytes();digest=hashlib.sha256(data).hexdigest()
        need(digest==spec['model']['sha256'],'Extra appearance changed')
        candidates=[name for name,row in files.items() if name.startswith('assets/v2ip/') and row['sha256']==digest]
        need(len(candidates)==1,'Extra appearance source is ambiguous')
        claim(candidates[0],digest,'Explicit ordinary retail appearance override; original own-dump textures/face, explicit isolated shape names',override['target'])
        extra_models.append({'path':candidates[0],'target':override['target']})
    need(len(extra_models)==1,'Expected extra source appearance is unaccounted')
    for fighter in report['fighters']:
        fighter['source_tier']=global_report['source_tiers'][str(fighter['source_core'])]
        fighter['components'].update(stats='converted',portrait='converted24roles',paired_motion='converted; native acceptance incomplete',
            intro='converted full graph',victory='converted full graph',activation='converted full graph; owned absolute phase4 per pinned legacy runtime reference',tier='converted')
    report['files']=[files[name] for name in sorted(files)]
    report['summary']=dict(Counter(row['status'] for row in report['files']))
    need(report['summary']=={'converted':1697,'exactly-inherited':184,'excluded':2},'Unaccounted source files remain: '+str(report['summary']))
    report.update(schema='fighter-conversion-source-accounting-1',native_acceptance=False,complete_faithfulness=False,
        source_population_reverified=True,extra_appearances=extra_models,
        subrecord_exclusions=[{'files':['assets/IntroExtro.xml','assets/entity.xml'],'models':['V2IP_606A','V2IP_607A'],
          'reason':'Dangling nonfighter registrations: no Character references and no supplied/original appearance; retained as explicit accounting exclusions'}],
        remaining_gates=['Owned absolute phase4 native/component coverage and remaining legacy runtime semantics require acceptance',
            'Whole-pack native acceptance, expanded lifetime/save/input and release-candidate platform/owner tests'],
        evidence={'previous':str(args.previous),'globals':str(args.global_report),'grid':str(args.grid_report)})
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary']))


if __name__=='__main__':main()
