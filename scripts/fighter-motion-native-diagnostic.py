"""Internal motion fixture layered on the guarded fighter-runtime-probe CLI.

Uses the verified local game/motion/main_all.dat. FIGHTER_CORE_PADDING adds
inherited cores to exercise wider IDs; FIGHTER_MOVESET_SELECTIONS enables the
bounded action-selection fixture. Requires --binding-window and reviewed local
appearance manifests. This script is a development fixture, not pack admission.
"""
import copy, hashlib, importlib.util, json, os, shutil, struct, sys, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('probe', ROOT/'scripts/fighter-runtime-probe.py')
probe=importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
from fighter_motion_compile import MotionCoreTemplates, encode_core_bindings
from fighter_sod import Database, CORE_FIELD, CHARACTER
from fighter_bindings import encode_bindings
from fighter_window import encode_window
original_prepare=probe.prepare
native_run=probe.subprocess.run
state={}
def prepare(*args,**kwargs):
    cache,old=original_prepare(*args,**kwargs)
    report=copy.deepcopy(old)
    if report.get('binding_mode')!='participant-window': raise ValueError('Motion fixture requires window')
    source=(ROOT/'game/motion/main_all.dat').read_bytes()
    compiler=MotionCoreTemplates(source,'f81f89f25d8a7d39a425dc45aead5858be03590873d360d78b65f53e24aa1ed4')
    custom={k:v for k,v in report['bindings'].items() if not k.startswith('retail/')}
    donors={k:v['core_id']-1 for k,v in custom.items()}
    padding=int(os.environ.get('FIGHTER_CORE_PADDING','0'))
    donors.update({f'a-probe-padding/core-{n:04}':4 for n in range(padding)})
    selected=None
    if os.environ.get('FIGHTER_MOVESET_SELECTIONS'):
        from fighter_moveset import compose_selected_cores
        from fighter_animation import AnimationEnvelope
        from fighter_archive import Archive
        from fighter_assets import unpack
        archive=Archive((ROOT/'game/motion/wres_all.viv').read_bytes())
        envelope=AnimationEnvelope(*(unpack(archive.read('wres005.'+suffix)) for suffix in ('ord','orl','mnl')))
        resources=dict(donors)
        for key in custom:
            resources[key]={'donor':donors[key],'envelope':envelope,
                            'bank_sha256':hashlib.sha256(envelope.model.data).hexdigest(),
                            'selections':{6:5,54:55} if 'alpha' in key else {5:6,56:54}}
        motion,receipt,selected=compose_selected_cores(compiler,resources)
    else:
        motion,receipt=compiler.compose(donors)
    data=bytearray((cache/'assets/djv2.sod').read_bytes())
    if Database(bytes(data)).schema.get(CORE_FIELD)!=(10,2): raise ValueError('Core schema differs')
    for key,row in custom.items():
        core=receipt['bindings'][key]['character_core']
        if struct.unpack_from('<I',data,row['record_offset']+40)[0]!=row['core_id']: raise ValueError('Core record differs')
        struct.pack_into('<I',data,row['record_offset']+40,core)
        row['core_id']=core
        if report['handle_bindings'][key]['available']: report['handle_bindings'][key]['core_id']=core
        report['native']['bindings'][key]['inherited_core_id']=core
        for binding in report['window']['fighters']:
            if binding['record_offset']==row['record_offset']: binding['core_id']=core
    destination=ROOT/'logs/fighter-motion-probes'/uuid.uuid4().hex
    shutil.copytree(cache,destination)
    (destination/'motion').mkdir()
    (destination/'motion/main_all.dat').write_bytes(motion)
    (destination/'fighter-motion.bin').write_bytes(selected if selected is not None else encode_core_bindings(motion,receipt))
    (destination/'assets/djv2.sod').write_bytes(data)
    (destination/'fighter-bindings.bin').write_bytes(encode_bindings(report['handle_bindings']))
    (destination/'fighter-window.bin').write_bytes(encode_window(report['window']))
    (destination/'motion-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    state.update(path=destination,sha=receipt['sha256'])
    print('owned motion fixture: '+str(destination),flush=True)
    return destination,report

def run(command,*args,**kwargs):
    if len(command)>1 and str(command[1]).endswith('harness.py'):
        command=list(command)
        if os.environ.get('FIGHTER_VOICE_WATCH'):
            command+=['--env','RECOMP_WATCH_WRITE=0x003403B4','--env','RECOMP_WATCH_LEN=4']
        elif os.environ.get('FIGHTER_MOTION_WATCH'):
            command+=['--env','RECOMP_WATCH_EXEC=0x001B2090,0x001B4930,0x001A7F30,0x001B2C60','--env','RECOMP_WATCH_EXEC_ALL=1']
        for key,value in {'RECOMP_FIGHTER_MOTION':state['path']/'motion/main_all.dat',
                          'RECOMP_FIGHTER_MOTION_BINDINGS':state['path']/'fighter-motion.bin',
                          'RECOMP_FIGHTER_MOTION_SHA256':state['sha']}.items():
            command+=['--env',key+'='+str(value)]
    return native_run(command,*args,**kwargs)
probe.prepare=prepare
probe.subprocess.run=run
if __name__=='__main__': raise SystemExit(probe.main())
