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
from fighter_animation import AnimationIndex
spec=importlib.util.spec_from_file_location('peek',ROOT/'scripts/peek-guest.py')
peek=importlib.util.module_from_spec(spec);spec.loader.exec_module(peek)
cache,pid,seconds=Path(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3])
output=Path(sys.argv[4]) if len(sys.argv)>4 else cache/'cinematic-live-named-proof.json'
owners={}
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
peek.k32.OpenProcess.restype=wt.HANDLE
handle=peek.k32.OpenProcess(0x410,False,pid)
if not handle:raise RuntimeError('Cannot read test process')
results=[];seen=set();errors=0;mismatches=[]
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
     seen.add(identity)
     row={'time':time.time(),'phase':word(0x3B8F30),'indexed_name_checked':True,'slot':slot,'core':word(0x3B90B8+4*slot),'key':key,'native_name':name,
          'pose':hex(pose),'wrapper':hex(wrapper),'parent':hex(parent),'child':hex(child),
          'evaluated_child_wrapper':evaluated,'descriptor_sha256':digest}
     if owners:
      row['owner_matches_binding']=row['core'] in owners.get(name,set())
      if evaluated and not row['owner_matches_binding']:mismatches.append(row)
     results.append(row);print(json.dumps(row),flush=True)
   except (ValueError,TypeError,OverflowError):errors+=1
  time.sleep(.1)
finally:
 peek.k32.CloseHandle(handle)
 output.write_text(json.dumps({'pid':pid,'snapshots':results,'unreadable_samples':errors,
                              'ownership_mismatches':mismatches},indent=2),encoding='utf-8')
if mismatches:raise SystemExit('Evaluated cinematic resource belongs to a different fighter')
