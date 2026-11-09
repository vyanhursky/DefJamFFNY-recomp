"""Internal end-to-end typed fighter behavior fixture using guarded saves.

Layers motion, synthetic voice, full-rig quaternion tracks, AI and simple
intro/victory resources on fighter-runtime-probe.py. It expects the locally
prepared appearance-alpha/beta assets under logs/fighter-appearance-packs and
the verified original game junction. No assets are shipped with this script.
Each layer retains its own CLI for targeted diagnosis. This is test scaffolding,
not a supported pack format or a bypass for the normal activation gates.
"""
import hashlib,importlib.util,json,math,os,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ai_probe',ROOT/'scripts/fighter-authored-ai-diagnostic.py')
ai=importlib.util.module_from_spec(spec);spec.loader.exec_module(ai)
from fighter_cinematic_compile import CinematicArchive,bind_cinematics,envelope
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_animation import AnimationIndex
from fighter_animation_tracks import QuaternionTracks
from fighter_elf import Model
from fighter_rig import Skeleton
old_prepare=ai.animation.voice.motion.probe.prepare
old_run=ai.animation.voice.old_run
state={}

def prepare(*args,**kwargs):
 destination,report=old_prepare(*args,**kwargs)
 motion=json.loads((destination/'motion-receipt.json').read_text(encoding='utf-8'))
 compiler=CinematicArchive((ROOT/'game/assets/v2ta.viv').read_bytes(),'7385473c185e40525c2b821888b1e29da3a4d21e6fb69fcdc73725fb6d5da6c7')
 resources={};cores={}
 for ordinal,key in enumerate(sorted(k for k in report['bindings'] if not k.startswith('retail/'))):
  pack=key.split('/')[0]
  rig=Skeleton(Model(unpack((ROOT/'logs/fighter-appearance-packs'/pack/'model.bin').read_bytes())))
  arm=rig.bones['__Bone:::root.L_arm1']
  pair={}
  for kind,token in [('intro','CI_113A'),('victory','CE_113A')]:
   nested=Archive(unpack(compiler.archive.read(token+'.viv')))
   idx=AnimationIndex(envelope(unpack(nested.read(token+'.o')),token))
   parent=idx.records[idx.lookup[token+'_s']]
   duration=struct.unpack_from('<H',idx.model.data,idx.model.data_range(parent+10,2))[0]
   poses=[]
   for tick in range(duration+1):
    values=[tuple(row[4:8]) for row in rig.rows]
    angle=(.35+.15*ordinal)*math.sin(2*math.pi*tick/max(1,duration))
    values[arm]=ai.animation.multiply(values[arm],(math.sin(angle/2),0.,0.,math.cos(angle/2)))
    poses.append(tuple(values))
   resource=key+'/'+kind
   resources[resource]={'template':token,'rig_sha256':rig.pose_sha256,'bone_count':len(rig.rows),
                        'tracks':QuaternionTracks(rig.pose_sha256,len(rig.rows),tuple(range(len(rig.rows))),tuple(poses))}
   pair[kind]=resource
  cores[motion['bindings'][key]['descriptor_index']]=pair
 banks,receipt=compiler.compose(resources)
 nis_path=destination/'assets/nis.viv'
 nis,table,binding=bind_cinematics(banks,receipt,nis_path.read_bytes(),report['appearance_files']['assets/nis.viv'],cores)
 (destination/'assets/v2ta.viv').write_bytes(banks);nis_path.write_bytes(nis)
 (destination/'fighter-cinematics.bin').write_bytes(table)
 (destination/'cinematic-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 (destination/'cinematic-binding-receipt.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
 report['appearance_files']['assets/nis.viv']=binding['nis_sha256']
 state.update(path=destination,sha=receipt['sha256'])
 print('owned cinematic fixture: '+str(destination),flush=True)
 return destination,report

def run(command,*args,**kwargs):
 if len(command)>1 and str(command[1]).endswith('harness.py'):
  command=list(command)
  for key,value in {'RECOMP_FIGHTER_CINEMATIC_BANKS':state['path']/'assets/v2ta.viv','RECOMP_FIGHTER_CINEMATIC_BINDINGS':state['path']/'fighter-cinematics.bin','RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256':state['sha']}.items():
   command+=['--env',key+'='+str(value)]
  command+=['--env','RECOMP_WATCH_EXEC=0x000A3160,0x00024290,0x000ED000','--env','RECOMP_WATCH_EXEC_ALL=1','--env','RECOMP_WATCH_EXEC_STR=1','--env','RECOMP_WATCH_EXEC_FIELD=0xC']
 return old_run(command,*args,**kwargs)
ai.animation.voice.motion.probe.prepare=prepare
ai.animation.voice.old_run=run
if __name__=='__main__':raise SystemExit(ai.animation.voice.motion.probe.main())
