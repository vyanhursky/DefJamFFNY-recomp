"""Local authored animation acceptance fixture; original game assets stay untouched."""
import importlib.util,json,math,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('voice_probe',ROOT/'scripts/fighter-authored-voice-diagnostic.py')
voice=importlib.util.module_from_spec(spec);spec.loader.exec_module(voice)
from fighter_animation_archive import AnimationArchive,encode_animation_bindings
from fighter_animation import AnimationEnvelope,AnimationIndex
from fighter_animation_tracks import QuaternionTracks
from fighter_assets import unpack
from fighter_elf import Model
from fighter_rig import Skeleton
old_prepare=voice.motion.probe.prepare
old_run=voice.old_run
state={}

def multiply(q,r):
 x,y,z,w=q;a,b,c,d=r
 return (w*a+x*d+y*c-z*b,w*b-x*c+y*d+z*a,w*c+x*b-y*a+z*d,w*d-x*a-y*b-z*c)

def prepare(*args,**kwargs):
 destination,report=old_prepare(*args,**kwargs)
 compiler=AnimationArchive((ROOT/'game/motion/wres_all.viv').read_bytes(),'02447acb0fa38ac0f94a625727d90dccd1c282709b52674a3dc4e3cc75407d80')
 envelope=AnimationEnvelope(*(unpack(compiler.archive.read('wres005.'+s)) for s in ('ord','orl','mnl')))
 bank=AnimationIndex(envelope);model=bank.model
 motion=json.loads((destination/'motion-receipt.json').read_text(encoding='utf-8'))
 resources={};cores={}
 for key in sorted(k for k in report['bindings'] if not k.startswith('retail/')):
  pack=key.split('/')[0]
  rig=Skeleton(Model(unpack((ROOT/'logs/fighter-appearance-packs'/pack/'model.bin').read_bytes())))
  amplitude=.20+.07*len(resources)
  arm=rig.bones['__Bone:::root.L_arm1']
  replacements={}
  for token in (*envelope.tokens[:10], *envelope.tokens[67:86]):
   parent=bank.records[bank.lookup[token+'_s']];at=model.data_range(parent,12)
   import struct
   duration=struct.unpack_from('<H',model.data,at+10)[0]
   poses=[]
   for tick in range(duration+1):
    angle=amplitude*math.sin(2*math.pi*tick/max(1,duration))
    values=[tuple(row[4:8]) for row in rig.rows]
    values[arm]=multiply(values[arm],(math.sin(angle/2),0.,0.,math.cos(angle/2)))
    poses.append(tuple(values))
   replacements[token]=QuaternionTracks(rig.pose_sha256,len(rig.rows),tuple(range(len(rig.rows))),tuple(poses))
  resources[key]={'template_bank':5,'rig_sha256':rig.pose_sha256,'bone_count':len(rig.rows),'replacements':replacements}
  if key in motion.get('selections',{}):
   from fighter_moveset import MovesetPlan
   from fighter_motion import MotionIndex
   import hashlib
   plan=MovesetPlan(MotionIndex((ROOT/'game/motion/main_all.dat').read_bytes()),4,envelope,hashlib.sha256(envelope.model.data).hexdigest())
   resources[key]['moveset']={'plan':plan,'selections':{int(a):b for a,b in motion['selections'][key]['selections'].items()}}
  cores[motion['bindings'][key]['descriptor_index']]=key
 archive,receipt=compiler.compose(resources)
 (destination/'motion/wres_all.viv').write_bytes(archive)
 (destination/'fighter-animations.bin').write_bytes(encode_animation_bindings(archive,receipt,cores))
 (destination/'animation-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 state.update(path=destination,sha=receipt['sha256'])
 print('owned animation fixture: '+str(destination),flush=True)
 print('animation banks: '+json.dumps({k:v['bank_number'] for k,v in receipt['bindings'].items()}),flush=True)
 return destination,report

def run(command,*args,**kwargs):
 if len(command)>1 and str(command[1]).endswith('harness.py'):
  command=list(command)
  if os.environ.get('FIGHTER_ANIMATION_WATCH'):
   command+=['--env','RECOMP_WATCH_EXEC=0x000ED000','--env','RECOMP_WATCH_EXEC_ALL=1','--env','RECOMP_WATCH_EXEC_FIELD=0xC']
  for key,value in {'RECOMP_FIGHTER_ANIMATIONS':state['path']/'motion/wres_all.viv',
                    'RECOMP_FIGHTER_ANIMATION_BINDINGS':state['path']/'fighter-animations.bin',
                    'RECOMP_FIGHTER_ANIMATIONS_SHA256':state['sha']}.items():
   command+=['--env',key+'='+str(value)]
 return old_run(command,*args,**kwargs)
voice.motion.probe.prepare=prepare
voice.old_run=run
if __name__=='__main__':raise SystemExit(voice.motion.probe.main())
