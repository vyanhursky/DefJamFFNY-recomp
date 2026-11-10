"""Two logical CAFs sharing a retail core retain independent behavior bindings."""
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_behavior_identity import caf_key
from fighter_voice_compile import encode_voice_bindings
from fighter_ai import encode_ai_bindings
from fighter_cinematic_compile import CinematicArchive, bind_cinematics
from test_fighter_voice_compile import source as voice_source, voice
from test_fighter_ai import source as ai_source, profile
from test_fighter_cinematic_compile import fixture, bundle, RIG, track
import test_fighter_voice_native as vn
import test_fighter_ai_native as an
import test_fighter_cinematic_native as cn


@pytest.fixture(params=['voice','ai','cinematic'])
def caf_tool(request,tmp_path_factory,monkeypatch):
    kind=request.param;module={'voice':vn,'ai':an,'cinematic':cn}[kind]
    driver=module.DRIVER
    stub='uint32_t defjam_fighter_caf_selection(uint32_t slot) {(void)slot;return 0;}'
    lookup='static int caf_mode;\nuint32_t defjam_fighter_caf_selection(uint32_t slot) {return caf_mode && slot<3?(slot==1?1002u:1001u):0;}'
    if kind=='voice':lookup='static int caf_mode;\nuint32_t defjam_fighter_caf_selection(uint32_t slot) {return caf_mode && slot!=2?(slot==3?1002u:1001u):0;}'
    driver=driver.replace(stub,lookup)
    if kind=='voice':
        driver=driver.replace('assert(started&&!strcmp', 'caf_mode=1;\n assert(started&&!strcmp')
        driver=driver.replace('{257,258,3,260}', '{6,6,3,6}')
        driver=driver.replace('for(uint32_t slot=0;slot<4;slot++) MEM32(0x2020+slot*0x18)=3;',
                              'caf_mode=0;for(uint32_t slot=0;slot<4;slot++) MEM32(0x2020+slot*0x18)=3;')
    elif kind=='ai':
        driver=driver.replace('assert(ok&&!strcmp', 'caf_mode=1;\n assert(ok&&!strcmp')
        driver=driver.replace('{256,257,1000,4}', '{5,5,5,4}')
        driver=driver.replace('enabled=1;MEM32', 'caf_mode=0;enabled=1;MEM32')
    else:
        marker='if(argc==8){'
        body=r'''
 caf_mode=1;
 MEM32(0x3B90B8)=4;MEM32(0x3B90BC)=4;MEM32(config+0xA8)=5;MEM32(config+0xAC)=5;
 MEM32(request)=1;MEM32(request+12)=0;MEM32(request+0x20)=1;
 for(unsigned slot=0;slot<2;++slot){
  uint32_t descriptor=c+slot*0x200;MEM32(request+4)=slot;
  uint64_t previous=defjam_fighter_cinematic_enter(manager,descriptor,request);
  defjam_fighter_cinematic_name(descriptor);
  assert(!strcmp((char*)memory+descriptor+0xA8,slot?"fmc16385":"fmc16384"));
  MEM32(descriptor+0xA4)=0;MEM32(descriptor+0x19C)=1;
  strcpy((char*)memory+descriptor+0x1D,slot?"FI00001":"FI00000");
  defjam_fighter_cinematic_selected(descriptor,descriptor+0x1D);
  assert(!strcmp((char*)memory+descriptor+0x1D,slot?"FI00001":"FI00000"));
  defjam_fighter_cinematic_leave(previous,request);
 }
 caf_mode=0;MEM32(request+4)=0;
 assert(!defjam_fighter_cinematic_enter(manager,c+0x400,request));
 return 0;
 '''
        assert marker in driver;driver=driver.replace(marker,'if(!strcmp(argv[6],"good")){'+body+'}\n'+marker,1)
    assert stub not in driver
    monkeypatch.setattr(module,'DRIVER',driver)
    return kind,module.tool.__wrapped__(tmp_path_factory)


def test_two_cafs_sharing_core_and_retail_fallback(caf_tool,tmp_path):
    kind,tool=caf_tool
    a,b=caf_key(1001),caf_key(1002)
    if kind in ('voice','ai'):
        if kind=='voice':
            _,compiler=voice_source();data,receipt=compiler.compose({'a/voice':voice(1),'b/voice':voice(2)})
            table=encode_voice_bindings(data,receipt,{256:'a/voice',a:'a/voice',b:'b/voice'})
        else:
            _,compiler=ai_source();data,receipt=compiler.compose({'a/ai':profile(),'b/ai':profile()})
            table=encode_ai_bindings(data,receipt,{256:'a/ai',a:'a/ai',b:'b/ai'})
        path=tmp_path/'data.viv';path.write_bytes(data);binding=tmp_path/'binding.bin';binding.write_bytes(table)
        args=[str(path),str(binding),receipt['sha256'],'good']
    else:
        source=fixture({'CI_0001.viv':bundle(),'CE_0001.viv':bundle('CE_0001')})
        data,receipt=CinematicArchive(source,hashlib.sha256(source).hexdigest()).compose({
            key:dict(template=token,rig_sha256=RIG,bone_count=4,tracks=track())
            for key,token in [('a','CI_0001'),('b','CE_0001'),('c','CI_0001')]})
        nis=fixture({'assets/IntroExtro.xml':b'<tauntslist></tauntslist>'})
        nis,table,report=bind_cinematics(data,receipt,nis,hashlib.sha256(nis).hexdigest(),{
            a:dict(intro='a',victory='b'),b:dict(intro='c',victory='b')})
        bank=tmp_path/'bank.viv';bank.write_bytes(data);binding=tmp_path/'binding.bin';binding.write_bytes(table)
        names=tmp_path/'nis.viv';names.write_bytes(nis)
        args=[str(bank),str(binding),report['banks_sha256'],str(names),report['nis_sha256'],'good']
    result=subprocess.run([tool,*args],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
