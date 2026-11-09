"""Local AI plus voice/animation/appearance acceptance fixture."""
import importlib.util,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('animation_probe',ROOT/'scripts/fighter-authored-animation-diagnostic.py')
animation=importlib.util.module_from_spec(spec);spec.loader.exec_module(animation)
from fighter_ai import AIProfiles,encode_ai_bindings
old_prepare=animation.voice.motion.probe.prepare
old_run=animation.voice.old_run
state={}
def prepare(*args,**kwargs):
 destination,report=old_prepare(*args,**kwargs)
 motion=json.loads((destination/'motion-receipt.json').read_text(encoding='utf-8'))
 compiler=AIProfiles((ROOT/'game/assets/ai/ai.viv').read_bytes(),'6b91192d87694b10fb00c4d4fd394b0826a6a8034dab909865a4cb4e55ceeb24')
 resources={};cores={}
 for key in sorted(k for k in report['bindings'] if not k.startswith('retail/')):
  value=1+len(resources)
  resources[key]={'template_profile':'char0005','tendencies':{difficulty:{slot:{'Attack_versus_Defend':value,'Punch_versus_Kick':value} for slot in range(4)} for difficulty in ('easy','normal','hard')}}
  cores[motion['bindings'][key]['descriptor_index']]=key
 data,receipt=compiler.compose(resources)
 (destination/'assets/ai').mkdir()
 (destination/'assets/ai/ai.viv').write_bytes(data)
 (destination/'fighter-ai.bin').write_bytes(encode_ai_bindings(data,receipt,cores))
 (destination/'ai-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 state.update(path=destination,sha=receipt['sha256'])
 print('owned AI fixture: '+str(destination),flush=True)
 return destination,report

def run(command,*args,**kwargs):
 if len(command)>1 and str(command[1]).endswith('harness.py'):
  command=list(command)
  for key,value in {'RECOMP_FIGHTER_AI':state['path']/'assets/ai/ai.viv','RECOMP_FIGHTER_AI_BINDINGS':state['path']/'fighter-ai.bin','RECOMP_FIGHTER_AI_SHA256':state['sha']}.items():
   command+=['--env',key+'='+str(value)]
 return old_run(command,*args,**kwargs)
animation.voice.motion.probe.prepare=prepare
animation.voice.old_run=run
if __name__=='__main__':raise SystemExit(animation.voice.motion.probe.main())
