"""Sample currently bound cinematic poses without modifying the game.

Usage: python scripts/fighter-cinematic-live-proof.py CACHE PID SECONDS [OUTPUT]
CACHE is a generated cinematic diagnostic or ordinary preview directory. Windows-only; requires
read access to the exact test process and the matching executable map. Output
is CACHE/cinematic-live-named-proof.json. Samples check current ownership and
indexed names; absence of a sample does not prove failure to play a sequence.
"""
import ctypes,ctypes.wintypes as wt,hashlib,importlib.util,json,struct,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'setup'))
from fighter_archive import Archive
from fighter_cinematic_compile import envelope
from fighter_animation import AnimationEnvelope,AnimationIndex
spec=importlib.util.spec_from_file_location('peek',ROOT/'scripts/peek-guest.py')
peek=importlib.util.module_from_spec(spec);spec.loader.exec_module(peek)
cache,pid,seconds=Path(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3])
output=Path(sys.argv[4]) if len(sys.argv)>4 else cache/'cinematic-live-named-proof.json'
owners={};pairs={};pair_slots={}
if (cache/'report.json').is_file():
 report=json.loads((cache/'report.json').read_text(encoding='utf-8'))
 receipt=report['behavior_receipts']['cinematic']
 for core,pair in report['behavior_receipts']['cinematic_bindings']['bindings'].items():
  for category in ('intro','victory'):owners.setdefault(pair[category],set()).add(int(core))
 if 'blazin' in report['behavior_receipts']:
  table=(cache/'fighter-blazin.bin').read_bytes()
  assert table[:4]==b'FBZ1' and len(table)==48+36*struct.unpack_from('<I',table,8)[0]
  for at in range(48,len(table),36):
   core,*names=struct.unpack_from('<I8s8s8s8s',table,at)
   for name in names:owners.setdefault(name.rstrip(b'\0').decode('ascii'),set()).add(core)
 items=list(receipt['bindings'].items())
 for key,shots in report['behavior_receipts'].get('blazin',{}).get('bindings',{}).items():
  items.extend((key+':'+str(shot['phase']),shot) for shot in shots)
else:
 receipt=json.loads((cache/'cinematic-receipt.json').read_text(encoding='utf-8'))
 items=list(receipt['bindings'].items())
archive=Archive((cache/'assets/v2ta.viv').read_bytes());expected=[]
for key,item in items:
 if 'bindings' not in item['animation']:continue # inherited body has no authored descriptor oracle
 name=item['native_name'];nested=Archive(archive.read(name+'.viv'))
 idx=AnimationIndex(envelope(nested.read(name+'.o')));model=idx.model
 row=item['animation']['bindings'][item['template']];child=row['child'];parent=row['parent']
 descriptor=model.pointers[child+4]['target'];size=4+12*row['scalars']+2*row['scalars']*(row['keys']-1)
 at=model.data_range(descriptor,size);digest=hashlib.sha256(model.data[at:at+size]).hexdigest()
 root=model.export_offset(idx.envelope.bank);cell=model.pointers[root+16]['target']+idx.lookup[name+'_s']*4
 names=model.pointers[root+20]['target'];name_at=model.pointers[names+idx.lookup[name+'_s']*4]['target']
 expected.append((key,name,parent,child,descriptor,size,digest,cell,name_at))
if (cache/'fighter-finishers.bin').is_file():
 table=(cache/'fighter-finishers.bin').read_bytes()
 stride=32 if table[:8]==b'FBP2\x02\0\0\0' else 28
 assert (stride==32 or table[:8]==b'FBP1\x01\0\0\0') and len(table)==52+stride*struct.unpack_from('<I',table,8)[0]
 for at in range(52,len(table),stride):
  if stride==32:core,slot,choice,ordinal,a,b=struct.unpack_from('<IIII8s8s',table,at)
  else:core,choice,ordinal,a,b=struct.unpack_from('<III8s8s',table,at)
  for role,raw in enumerate((a,b)):
   name=raw.rstrip(b'\0').decode('ascii')
   owners.setdefault(name,set()).add(core);pairs[name]=(role,ordinal+role)
   if stride==32:pair_slots.setdefault(name,set()).add((core,slot,choice))
 archive=Archive((cache/'motion/blazin.viv').read_bytes())
 for key,pair in report['behavior_receipts']['finishers']['bindings'].items():
  for role,item in pair['roles'].items():
   name=item['native_name']
   env=AnimationEnvelope(*(archive.read(name+'.'+ext) for ext in ('ord','orl')),
                         struct.pack('<II',1,0)+name.encode('ascii')+b'.')
   idx=AnimationIndex(env);model=idx.model
   row=item['animation']['bindings'][item['template']];child=row['child'];parent=row['parent']
   descriptor=model.pointers[child+4]['target'];size=4+12*row['scalars']+2*row['scalars']*(row['keys']-1)
   at=model.data_range(descriptor,size);digest=hashlib.sha256(model.data[at:at+size]).hexdigest()
   root=model.export_offset(env.bank);cell=model.pointers[root+16]['target']+idx.lookup[name+'_s']*4
   names=model.pointers[root+20]['target'];name_at=model.pointers[names+idx.lookup[name+'_s']*4]['target']
   expected.append((key+':'+role,name,parent,child,descriptor,size,digest,cell,name_at))
peek.k32.OpenProcess.restype=wt.HANDLE
handle=peek.k32.OpenProcess(0x410,False,pid)
if not handle:raise RuntimeError('Cannot read test process')
results=[];seen=set();errors=0;mismatches=[];manager_states=[];manager_seen=set()
try:
 symbol=peek.map_symbol(ROOT/'build/win-x64-release/defjam_recomp.map','g_xbox_mem_offset')
 offset=0
 ready=time.monotonic()+15
 while time.monotonic()<ready:
  raw=peek.read(handle,symbol,8)
  offset=int.from_bytes(raw,'little') if raw else 0
  check=peek.read(handle,0x234768+offset,4) if offset else None
  if check and int.from_bytes(check,'little')==0x234770:break
  time.sleep(.1)
 def read(a,n):
  value=peek.read(handle,a+offset,n)
  if value is None or len(value)!=n:raise ValueError('Unreadable current pointer')
  return value
 def word(a):return int.from_bytes(read(a,4),'little')
 assert word(0x234768)==0x234770
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  try:
   manager=0x349760
   state={name:word(manager+relative) for name,relative in
          (('delta_bits',4),('previous_delta_bits',8),('state',0x2D820),('mode',0x2B9EC),('owner',0x2D844),('selection',0x2D84C),
           ('winner',0x2D858),('winner_aux',0x2D85C))}
   state.update({name:word(address) for name,address in
                 (('phase',0x3B8F30),('match_flags',0x3B9054),('snapshot_flags',0x3BE0F4),
                  ('snapshot_aux',0x3BE0F8),('completion',0x3B8598),('input_flags',0x3BE120),
                  ('finish_timer_bits',0x3B9064),('scale_bits',0x3B8F2C),
                  ('camera_mode',0x377330),('camera_scale_bits',0x377354),
                  ('camera_restore_bits',0x377358),('camera_cursor',0x377380))})
   state['camera_label']=read(0x377384,32).split(b'\0',1)[0].decode('ascii',errors='replace')
   setup=word(manager+0x2FF5C)
   state['setup_flags']=word(setup+0x198) if setup else 0
   identity=tuple(state.values())
   if identity not in manager_seen and len(manager_states)<2000:
    manager_seen.add(identity)
    requests=word(manager+0x2D834);count=word(manager+0x2D868)
    if requests and 12<=count<=29:
     state['private_requests']=[word(requests+(count+i)*0x24+0x14) for i in range(40)]
    state['time']=time.time();manager_states.append(state)
    if state['phase']>=2:print(json.dumps({'manager_snapshot':state}),flush=True)
  except (ValueError,TypeError,OverflowError):errors+=1
  for slot in range(4):
   try:
    visual=word(0x375120+4*slot)
    if not visual:continue
    pose=word(visual+0x9D0) if word(visual+0xABB4)&1 else visual+0x30
    wrapper=word(pose+0x1E8);parent=word(wrapper+12)
    if struct.unpack('<H',read(parent,2))[0]!=15:continue
    if struct.unpack('<H',read(parent+8,2))[0]!=1:continue
    child=word(parent+12)
    if struct.unpack('<H',read(child,2))[0]!=11:continue
    for key,name,relative_parent,relative_child,relative_descriptor,size,digest,cell,name_at in expected:
     base=parent-relative_parent
     if child!=base+relative_child or word(child+4)!=base+relative_descriptor or word(base+cell)!=parent:continue
     if read(base+name_at,len(name)+3)!=(name+'_s').encode('ascii')+bytes(1):continue
     if hashlib.sha256(read(word(child+4),size)).hexdigest()!=digest:continue
     if word(pose+0x1E8)!=wrapper or word(wrapper+12)!=parent or word(parent+12)!=child:continue
     children=word(wrapper+0x10);evaluated=bool(children and word(word(children)+12)==child)
     identity=(slot,key,parent,evaluated)
     if identity in seen:continue
     row={'time':time.time(),'phase':word(0x3B8F30),'indexed_name_checked':True,'slot':slot,'core':word(0x3B90B8+4*slot),'key':key,'native_name':name,
          'pose':hex(pose),'wrapper':hex(wrapper),'parent':hex(parent),'child':hex(child),
          'evaluated_child_wrapper':evaluated,'descriptor_sha256':digest}
     if name in pairs:
      role,ordinal=pairs[name];actor=0x3B92E0+slot*0x12E8
      subject=word(actor) if role else actor
      if subject<0x3B92E0 or subject>=0x3B92E0+4*0x12E8 or (subject-0x3B92E0)%0x12E8:continue
      # A sampled transition is not an ownership verdict: require both actor
      # motion IDs and the paired link to still describe this exact playback.
      if word(actor+0x88)!=ordinal or word(subject+0x88)!=ordinal-role:continue
      if role and word(subject)!=actor:continue
      row['role']='counterpart' if role else 'subject'
      row['subject_slot']=(subject-0x3B92E0)//0x12E8;row['subject_core']=word(subject+0x2C)
      row['external_ordinal']=ordinal
      row['owner_matches_binding']=row['subject_core'] in owners[name]
      if name in pair_slots:
       action=word(subject+0xF50)
       action_slot=action-31 if 31<=action<=34 else action-38 if 38<=action<=41 else None
       if action_slot is None:continue
       choice=word(subject+0xBB8+action_slot*4)
       if word(subject+0x88)!=ordinal-role or word(subject+0xF50)!=action:continue
       row['action_slot']=action_slot;row['template_choice']=choice
       row['owner_matches_binding']=row['owner_matches_binding'] and (row['subject_core'],action_slot,choice) in pair_slots[name]
      if evaluated and not row['owner_matches_binding']:mismatches.append(row)
     elif owners:
      row['owner_matches_binding']=row['core'] in owners.get(name,set())
      if evaluated and not row['owner_matches_binding']:mismatches.append(row)
     seen.add(identity);results.append(row);print(json.dumps(row),flush=True)
   except (ValueError,TypeError,OverflowError):errors+=1
  time.sleep(.1)
finally:
 peek.k32.CloseHandle(handle)
 output.write_text(json.dumps({'pid':pid,'snapshots':results,'unreadable_samples':errors,
                              'ownership_mismatches':mismatches,'manager_states':manager_states},indent=2),encoding='utf-8')
if mismatches:raise SystemExit('Evaluated cinematic resource belongs to a different fighter')
