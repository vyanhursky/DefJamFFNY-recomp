"""Actual normal annex admission, private clone rollback and draw-consumer guards."""
import os
import shutil
import struct
import subprocess
import pytest
from test_fighter_caf_outfits_native import native as container_tool
from test_fighter_caf_face import fixture
from test_fighter_caf_face_native import DRIVER, ROOT
from test_fighter_motion_native import TYPES
from fighter_caf_face import encode_rows, encode_normals
from fighter_caf import encode
from fighter_neck_normals import validate
import fighter_caf_layout as layout


def normal():
    return dict(slot=3,rm=0,vertex=1,position=[0.,18.,0.],original=511<<22,replacement=(500<<22)|210)


def entries():
    face,recipe=fixture();face.update(schema='caf-face-coordinates-2',neck_normals=[normal()])
    recipe.update(stats=dict.fromkeys(('upper','lower','speed','toughness','health'),10),styles=[0],caf_colors=[0]*38)
    return {'a/b':dict(core=87,audio_core=5,recipe=recipe,extras=None,outfits=[dict(recipe=recipe,face=face)])},{'bindings':{'a/b':{'selection_key':100}}}


def test_v1_stays_identical_and_v2_annex_tiles_and_preserves_face_bytes():
    e,r=entries();v2=encode(e,r);h,*sections=layout.split(v2)
    assert struct.unpack_from('<I',v2,4)==(2,)
    assert h['normals_count']==1 and h['normals_bytes']==4108
    assert layout.normal_rows(v2)==encode_normals(e,r)[1]
    assert len(sections[-1])==layout.FACE_STRIDE
    e['a/b']['outfits'][0]['face'].pop('neck_normals');e['a/b']['outfits'][0]['face']['schema']='caf-face-coordinates-1'
    v1=encode(e,r);h1,*sections1=layout.split(v1)
    assert v1[52:64]==bytes(12) and struct.unpack_from('<I',v1,4)==(1,)
    assert sections1==sections and layout.normal_rows(v1)==b''
    assert layout.split(v2[:-1]) is None
    for offset,value in ((4,3),(52,64),(56,0),(60,1)):
        bad=bytearray(v2);struct.pack_into('<I',bad,offset,value);assert layout.split(bad) is None
    bad=bytearray(v1);bad[52]=1;assert layout.split(bad) is None


@pytest.mark.parametrize('mutation',[
 lambda x:x.update(slot=2),lambda x:x.update(rm=16),lambda x:x.update(vertex=-1),
 lambda x:x.update(position=[0,float('nan'),0]),lambda x:x.update(position=[0,20.,0]),
 lambda x:x.update(original=0),lambda x:x.update(replacement=512<<22),lambda x:x.update(extra=1),
])
def test_rejects_unsafe_normal_documents(mutation):
    n=normal();mutation(n)
    with pytest.raises(ValueError):validate([n])

EXTRA=r'''
static void make_neck(uint32_t visual) {
 unsigned model=0x400000,table=0x400200,rm=0x401000,program=0x402000,xyz=0x403000,vb=0x404000,res=0x405000;
 MEM32(visual+0x140+3*0x420+0x12c)=model;MEM32(model+0x9c)=1;MEM32(model+0xcc)=table;
 MEM32(table+4)=1;MEM32(table+8)=rm+0x38;MEM32(rm+0x38)=rm;MEM32(rm)=program;MEM32(rm+8)=program+36;
 MEM32(program)=0x90004;MEM32(program+4)=0x640;MEM32(program+12)=12;MEM32(program+16)=0x90004;MEM32(program+24)=3;MEM32(program+28)=4;
 MEM32(rm+0x3c)=3;MEM32(rm+0x40)=xyz;MEM32(rm+0x44)=3;MEM32(rm+0x48)=vb+20;
 MEM32(vb)=res;MEM32(vb+4)=12;MEM32(vb+8)=4;MEM32(vb+16)=vb+20;
 MEM32(res)=1;MEM32(res+4)=vb+20;MEMF(xyz+12+4)=18.f;
 MEM32(vb+24)=511u<<22;
}
'''

@pytest.fixture(scope='module')
def normal_tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else shutil.which('cc')
    if not cc:pytest.skip('C compiler unavailable')
    f=tmp_path_factory.mktemp('neck-native');(f/'recomp/gen').mkdir(parents=True);(f/'recomp/gen/recomp_types.h').write_text(TYPES)
    driver=DRIVER.replace('@SOURCE@',(ROOT/'src/patches/fighter_caf_face.c').as_posix())
    driver=driver.replace('void sub_0021BB10(void) {assert(!"unexpected stream unbind");}',
        'void sub_0021BB10(void) {unsigned stream=MEM32(g_esp+4);assert(stream==3&&!MEM32(g_esp+8));MEM32(0x236c18+stream*12)=0;g_esp+=16;}')
    driver=driver.replace('assert(MEM32(g_esp+4)==0x4000);g_eax=0x600000;', 'assert(MEM32(g_esp+4)==0x4000||MEM32(g_esp+4)==65536);g_eax=MEM32(g_esp+4)==0x4000?0x600000:0x700000;')
    driver=driver.replace('int main(',EXTRA+'\nint main(')
    driver=driver.replace('CAF_FACE_STRIDE*4u+16','CAF_FACE_STRIDE*4u+CAF_NORMAL_STRIDE')
    driver=driver.replace('assert(size==(size_t)count*CAF_FACE_STRIDE);','assert(size==(size_t)count*CAF_FACE_STRIDE+CAF_NORMAL_STRIDE);')
    driver=driver.replace('if(!strcmp(mode,"bad-read")) {assert(!defjam_caf_faces_start(lookup,rows,count));return 0;}', '')
    driver=driver.replace('assert(s_count==1);','assert(s_count==1);\n if(!strcmp(mode,"bad-read")){assert(!defjam_caf_normals_start(rows+count*CAF_FACE_STRIDE,1));return 0;}\n assert(defjam_caf_normals_start(rows+count*CAF_FACE_STRIDE,1));')
    driver=driver.replace('wrong_result=!strcmp(mode,"result");','make_neck(0x30000);\n if(!strcmp(mode,"normal-source"))MEM32(0x404018)=1;\n if(!strcmp(mode,"normal-position"))MEMF(0x403010)=19.f;\n wrong_result=0;')
    driver=driver.replace('assert(!strcmp(mode,"good")&&calls==1);','assert(calls==1);')
    marker=' defjam_caf_faces_clear();assert(!s_live[0][1]&&!s_live[1][1]);return 0;'
    assert marker in driver
    driver=driver.replace(marker,r''' uint32_t part=0x30000+0x140+3*0x420;
 if(!strncmp(mode,"normal-",7)) {
   assert(MEM32(part+0x12c)==0x400000&&s_normals[1].blocked);return 0;
 }
 assert(MEM32(part+0x12c)!=0x400000&&MEM32(0x404018)==(511u<<22));
 uint32_t clone=MEM32(part+0x12c),rm=MEM32(MEM32(MEM32(clone+0xcc)+8)),param=rm+0x44;
 assert(MEM32(MEM32(rm+0x48)+4)==((500u<<22)|210));assert(MEM32(0x400208)==0x401038);
 if(!strcmp(mode,"draw-data"))MEM32(MEM32(param+4)+4)=0;
 if(!strcmp(mode,"draw-resource"))MEM32(MEM32(param+4)-20)=0x405000;
 if(!strcmp(mode,"draw-stride"))MEM32(MEM32(param+4)-12)=8;
 if(!strcmp(mode,"draw-count"))MEM32(param)=4;
 if(!strcmp(mode,"draw-gpu"))MEM32(s_normal_resources[1][0][0]+4)=0x403000;
 if(!strncmp(mode,"draw-",5)) {
   assert(!defjam_caf_normals_stream(0x402010,param));assert(!defjam_caf_normals_stream(0x402010,param));assert(MEM32(part+0x12c)==0x400000&&s_normals[1].blocked);return 0;
 }
 assert(defjam_caf_normals_stream(0x402010,param));assert(s_normal_drawn[1][0][0]);
 defjam_caf_normals_release(0x30000,12);assert(MEM32(part+0x12c)==clone);
 MEM32(0x236c18+3*12)=s_normal_resources[1][0][0];MEM32(0x3a6e20+3*4)=s_normal_resources[1][0][0];
 if(!strcmp(mode,"owner"))MEM32(part+0x12c)=0x400100;
 defjam_caf_normals_release(0x30000,3);
 if(!strcmp(mode,"owner")) {assert(MEM32(part+0x12c)==0x400100&&s_normals[1].blocked);return 0;}
 assert(MEM32(part+0x12c)==0x400000&&!MEM32(0x236c18+3*12)&&!MEM32(0x3a6e20+3*4));
 defjam_caf_normals_release(0x30000,3);
 normals_apply(0x30000,1,s_data);assert(MEM32(part+0x12c)==clone);
 defjam_caf_normals_release(0x30000,3);defjam_caf_faces_release();assert(!s_normal_count&&!s_normal_data);
 defjam_caf_faces_clear();assert(!s_live[0][1]&&!s_live[1][1]);return 0;''')
    (f/'driver.c').write_text(driver);exe=f/('test.exe' if os.name=='nt' else 'test')
    sources=[str(f/'driver.c'),str(ROOT/'src/patches/fighter_fatal.c'),str(ROOT/'src/patches/fighter_config.c'),str(ROOT/'tests/unit/native_stubs/host_fatal.c')]
    cmd=([cc,'/nologo','/W4','/WX','/wd5105','/D_CRT_SECURE_NO_WARNINGS','/I'+str(f),'/I'+str(ROOT/'src'),*sources,'/Fe:'+str(exe)] if os.name=='nt'
         else [cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror','-I',str(f),'-I',str(ROOT/'src'),*sources,'-lm','-o',str(exe)])
    result=subprocess.run(cmd,capture_output=True,text=True,cwd=f);assert result.returncode==0,result.stdout+result.stderr
    return exe


def payload():
    e,r=entries();return encode_rows(e,r)[1]+encode_normals(e,r)[1]


@pytest.mark.parametrize('mode',['good','normal-source','normal-position','draw-data','draw-resource','draw-count','draw-stride','draw-gpu','owner'])
def test_private_normal_restore_reuse_and_safe_mismatch_fallback(normal_tool,tmp_path,mode):
    p=tmp_path/'normals';p.write_bytes(payload())
    result=subprocess.run([str(normal_tool),str(p),'1',mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    if mode.startswith('normal-'):assert 'rejected participant=1' in result.stderr
    elif mode.startswith('draw-'):assert 'upload skipped' in result.stderr
    elif mode=='owner':assert 'ownership changed' in result.stderr
    else:assert 'shared-source=unchanged' in result.stderr and 'restored' in result.stderr


@pytest.mark.parametrize('offset,value',[(0,999),(4,3),(8,0),(8,129),(12,2),(16,16),(20,1024),(28,0x7fc00000),(36,0),(40,512<<22),(44,1)])
def test_native_annex_rejects_unbound_rows_invalid_samples_and_nonzero_padding(normal_tool,tmp_path,offset,value):
    raw=bytearray(payload());struct.pack_into('<I',raw,layout.FACE_STRIDE+offset,value)
    p=tmp_path/'bad';p.write_bytes(raw)
    result=subprocess.run([str(normal_tool),str(p),'1','bad-read'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


def test_rejected_upload_preserves_native_dispatcher_cursor_and_guest_return_abi(tmp_path):
    cc=shutil.which('cc')
    if not cc:pytest.skip('POSIX compiler fixture')
    source=(ROOT/'src/recomp_manual.c').read_text()
    wrapper=source[source.index('void sub_00118030(void) {'):].split('\n}',1)[0]+'\n}'
    driver=r'''#include <assert.h>
#include <stdint.h>
static uint32_t mem[0x400000/4],g_esp,g_eax;static unsigned called,accept;
#define MEM32(p) mem[(p)/4]
int defjam_caf_normals_stream(uint32_t c,uint32_t p){assert(c==0x20000&&p==0x10000);return accept;}
void sub_00118030_gen(void){called++;}
'''+wrapper+r'''
int main(void){
 MEM32(0x3a597c)=0x20000;MEM32(0x3a5978)=0x10000;MEM32(0x3a5388)=123;g_esp=100;
 sub_00118030();assert(!called&&g_esp==104&&MEM32(0x3a5978)==0x10008&&g_eax==123);
 accept=1;MEM32(0x3a5978)=0x10000;sub_00118030();assert(called==1&&g_esp==104);return 0;
}
'''
    p=tmp_path/'test.c';p.write_text(driver);exe=tmp_path/'test'
    result=subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror',str(p),'-o',str(exe)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert subprocess.run([str(exe)]).returncode==0


def test_python_v2_container_and_corrupt_annex_headers_against_actual_c_reader(container_tool,tmp_path):
    e,r=entries();raw=encode(e,r);p=tmp_path/'container';p.write_bytes(raw)
    result=subprocess.run([str(container_tool),str(p),'normal-header'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    for offset,value in ((4,3),(52,64),(56,0),(56,0xffffffff),(60,1)):
        bad=bytearray(raw);struct.pack_into('<I',bad,offset,value);p.write_bytes(bad)
        result=subprocess.run([str(container_tool),str(p),'bad-header'],capture_output=True,text=True)
        assert result.returncode==0,result.stderr
