"""Local owned PCM acceptance fixture; no public package or original edits."""
import importlib.util, json, math, struct, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('motion_probe',ROOT/'scripts/fighter-motion-native-diagnostic.py')
motion=importlib.util.module_from_spec(spec);spec.loader.exec_module(motion)
from fighter_voice import encode_stream
from fighter_voice_compile import VoiceCompiler, encode_voice_bindings, CATEGORIES
from fighter_voice_bank import VoiceBankTemplate
old_prepare=motion.probe.prepare
old_run=motion.native_run
state={}

def prepare(*args,**kwargs):
    destination,report=old_prepare(*args,**kwargs)
    receipt=json.loads((destination/'motion-receipt.json').read_text(encoding='utf-8'))
    data=(ROOT/'game/audio/speech2.viv').read_bytes()
    compiler=VoiceCompiler(data,'6bbccf36278df2bec76801f79ec07178c0dc6414934a6d53fae17bd920288a75')
    voices={};cores={}
    for ordinal,(key,binding) in enumerate(sorted(report['bindings'].items())):
        if key.startswith('retail/'): continue
        # Fixed synthetic tones make routing audible without pretending to be
        # human speech. Four keys cover both independent appearance packs.
        rate=24000;frequency=997+502*len(voices) if os.environ.get('FIGHTER_VOICE_DISTINCT') else 330+110*len(voices);count=4800
        values=[int(2500*math.sin(2*math.pi*frequency*i/rate)*min(1,i/240,(count-1-i)/240)) for i in range(count)]
        pcm=encode_stream(struct.pack('<'+'h'*count,*values),rate)
        replacements={}
        for category in CATEGORIES:
            h=compiler.archive.read(f'speech/{category}/Def_Jam_Characters/022.hdr')
            replacements[category]={i:pcm for i in range(h[5])}
        voices[key]={'template_voice':22,'samples':replacements,'intro':pcm,'extro':pcm}
        cores[receipt['bindings'][key]['descriptor_index']]=key
    archive,voice_report=compiler.compose(voices)
    (destination/'audio').mkdir(exist_ok=True)
    (destination/'audio/speech2.viv').write_bytes(archive)
    (destination/'fighter-voices.bin').write_bytes(encode_voice_bindings(archive,voice_report,cores))
    (destination/'voice-receipt.json').write_text(json.dumps(voice_report,indent=2),encoding='utf-8')
    state.update(path=destination,sha=voice_report['sha256'])
    print('owned voice fixture: '+str(destination),flush=True)
    print('voice bindings: '+json.dumps({k:v['voice_id'] for k,v in voice_report['bindings'].items()}),flush=True)
    return destination,report

def run(command,*args,**kwargs):
    if len(command)>1 and str(command[1]).endswith('harness.py'):
        command=list(command)
        if os.environ.get('FIGHTER_VOICE_DECODE_WATCH'):
            command += ['--env','RECOMP_WATCH_EXEC=0x0012E490,0x0012E520,0x00130EA0', '--env','RECOMP_WATCH_EXEC_ALL=1']
        if os.environ.get('FIGHTER_VOICE_CAPTURE'):
            command += ['--env', 'RECOMP_AUDIO_WAV='+str(state['path']/'device-audio.wav')]
        for key,value in {'RECOMP_FIGHTER_VOICES':state['path']/'audio/speech2.viv',
                          'RECOMP_FIGHTER_VOICE_BINDINGS':state['path']/'fighter-voices.bin',
                          'RECOMP_FIGHTER_VOICES_SHA256':state['sha']}.items():
            command+=['--env',key+'='+str(value)]
    return old_run(command,*args,**kwargs)
motion.probe.prepare=prepare
motion.native_run=run
if __name__=='__main__':raise SystemExit(motion.probe.main())
