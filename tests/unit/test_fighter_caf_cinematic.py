"""Invented CAF cinematic proofs and bounded donor cue descriptors; no game data."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"setup"))
from test_fighter_ui_native import TYPES
from fighter_caf_cinematic import validate,FORMAT

ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('edit',[
    {'selector':2,'key':3,'expected':4,'sample':7},
    {'selector':0,'key':3,'expected':4,'sample':13},
    {'selector':0,'key':-1,'expected':4,'sample':7},
    {'selector':0,'key':3,'expected':4,'sample':True},
    {'selector':0,'key':3,'expected':4,'sample':7,'pointer':123},
])
def test_caf_cue_bounds(edit):
    with pytest.raises(ValueError):validate(dict(format=FORMAT,template='CI_132A',edits=[edit]))

def test_caf_donor_identity_and_duplicate_edits():
    validate(dict(format=FORMAT,template='CI_132A',edits=[]))
    edit=dict(selector=0,key=3,expected=4,sample=7)
    with pytest.raises(ValueError):validate(dict(format=FORMAT,template='CI_132A',edits=[edit,edit]))
    validate(dict(format=FORMAT,template='CI_113A',edits=[]))
    with pytest.raises(ValueError):validate(dict(format=FORMAT,template='CI_113B',edits=[]))

DRIVER=r'''
#define _CRT_SECURE_NO_WARNINGS
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_film_proof.h"
unsigned char memory[0x400000];static unsigned current;
int defjam_fighter_cinematic_absolute(uint32_t d){(void)d;return 0;}
int defjam_fighter_cinematic_proofs(void){return 1;}
unsigned defjam_fighter_cpu_film(uint32_t p){(void)p;return current;}
int defjam_fighter_cpu_range(uint32_t p,uint32_t n){return p>=0x10000 && p<0x60000 && n<=64;}
int defjam_fighter_events_has(const char*n,unsigned flags){return !strcmp(n,"FV00000")&&!flags;}
int defjam_fighter_graph_visual(uint32_t v,uint32_t b,const uint8_t*r,unsigned count,const uint32_t*f,const uint32_t*h){
 assert(v==0x200000&&b==94&&count==2&&r[0]==0x10&&r[32]==0x14);
 assert(f&&f[0]==5&&f[1]==15&&h[0]==23&&h[1]==22);return 1;
}
int main(int argc,char**argv){
 assert(argc==5);
#ifdef _WIN32
 _putenv_s("RECOMP_FIGHTER_FILM_PROOFS",argv[1]);_putenv_s("RECOMP_FIGHTER_CINEMATIC_BANKS",argv[2]);_putenv_s("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256",argv[3]);
#else
 setenv("RECOMP_FIGHTER_FILM_PROOFS",argv[1],1);setenv("RECOMP_FIGHTER_CINEMATIC_BANKS",argv[2],1);setenv("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256",argv[3],1);
#endif
 int ok=defjam_fighter_film_start();if(!strcmp(argv[4],"reject")){assert(!ok);return 0;}assert(ok);
 if(!strcmp(argv[4],"mismatch")){assert(!defjam_fighter_film_caf("FV00000"));return 0;}
 assert(defjam_fighter_film_caf("FV00000"));assert(!defjam_fighter_film_caf("FI00000"));
 /* Sorted members: body, EYE, TARGET, face, hands. */
 const unsigned roles[]={1,2,3,4,5};
 for(unsigned i=1;i<=5;++i){unsigned base=i*0x10000;current=i;MEM32(base)=base+40;MEM32(base+4)=roles[i-1];assert(defjam_fighter_film_preconstruct(base+16));}
 uint32_t e=0x1000,d=0x2000,t=0x8000,v=0x200000;
 MEM32(e+0x24)=0x10010;MEM32(e+0x30)=0x40010;MEM32(e+0x3c)=0x50010;
 MEM32(d+0x88)=t;MEM32(d+0x8c)=2;MEM32(d+0xa4)=1;MEM32(d+0x13c)=0x9000;
 strcpy((char*)memory+t,"CAM_TARGET");strcpy((char*)memory+t+0x2c,"CAM_EYE");MEM32(t+0x24)=0x30010;MEM32(t+0x50)=0x20010;MEM8(v+0xabb4)=1;
 assert(defjam_fighter_film_bind("FV00000",e,v,d));
 MEM8(v+0xabb4)=0;assert(!defjam_fighter_film_bind("FV00000",e,v,d));MEM8(v+0xabb4)=1;
 MEM32(e+0x30)=0x10010;assert(!defjam_fighter_film_bind("FV00000",e,v,d));MEM32(e+0x30)=0x40010;
 defjam_fighter_film_release();assert(!defjam_fighter_film_bind("FV00000",e,v,d));return 0;
}
'''

@pytest.fixture(scope='module')
def caf_tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else shutil.which('cc')
    if not cc:pytest.skip('C compiler unavailable')
    d=tmp_path_factory.mktemp('caf-film');(d/'recomp/gen').mkdir(parents=True)
    (d/'recomp/gen/recomp_types.h').write_text(TYPES);(d/'test.c').write_text(DRIVER)
    exe=d/('test.exe' if os.name=='nt' else 'test')
    src=[str(d/'test.c'),str(ROOT/'src/patches/fighter_film_proof.c'),str(ROOT/'src/patches/fighter_config.c')]
    cmd=([cc,'/nologo','/W4','/WX','/I'+str(d),'/I'+str(ROOT/'src'),*src,'/Fe:'+str(exe)] if os.name=='nt'
         else [cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror','-I',str(d),'-I',str(ROOT/'src'),*src,'-o',str(exe)])
    r=subprocess.run(cmd,capture_output=True,text=True,cwd=d);assert r.returncode==0,r.stdout+r.stderr
    return exe

@pytest.fixture
def caf_files(tmp_path):
    archive=tmp_path/'banks';archive.write_bytes(b'invented CAF cinematic archive')
    digest=hashlib.sha256(archive.read_bytes()).digest();rows=[]
    for ordinal,(suffix,role) in enumerate([('.o',1),('_EYE.o',4),('_TARGET.o',4),('_f.o',2),('_h.o',3)],1):
        payload=bytearray(64);struct.pack_into('<2I',payload,0,40,ordinal)
        row=struct.pack('<32s8I',('FV00000'+suffix).encode(),64,16,1,94,23,22,role,0)
        row+=bytes.fromhex('10'*32)+hashlib.sha256(payload).digest()+struct.pack('<4I',1,5,15,2)+bytes.fromhex('14'*32)+struct.pack('<2I',0,40)
        rows.append(row)
    proof=tmp_path/'proof';proof.write_bytes(b'FCP2'+struct.pack('<4I',2,5,len(archive.read_bytes()),0)+digest+b''.join(rows))
    return proof,archive,digest.hex()

def test_caf_seals_both_rigs_face_requirements_and_actual_context(caf_tool,caf_files):
    r=subprocess.run([str(caf_tool),*map(str,caf_files),'good'],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr

@pytest.mark.parametrize('offset,value',[(128,2),(132,0),(132,14),(136,16),(140,1),(44,93),(48,33)])
def test_caf_extended_metadata_rejects(caf_tool,caf_files,offset,value):
    p,a,h=caf_files;data=bytearray(p.read_bytes());struct.pack_into('<I',data,52+offset,value);p.write_bytes(data)
    r=subprocess.run([str(caf_tool),str(p),str(a),h,'reject'],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr

def test_caf_members_cannot_disagree_on_context(caf_tool,caf_files):
    p,a,h=caf_files;data=bytearray(p.read_bytes());struct.pack_into('<I',data,52+184+132,6);p.write_bytes(data)
    r=subprocess.run([str(caf_tool),str(p),str(a),h,'mismatch'],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr


def test_camera_constructor_order_keeps_locals_and_export_bindings():
    from types import SimpleNamespace
    from fighter_caf_cinematic import bank_before_model
    local=[('',0,0,0,0),('',0,0,3,1)]
    exports=[('__Model:::CAM_TARGET',900,224,0x10,1),
             ('__AnimationBank:::FV00000_TARGET',832,24,0x10,1),
             ('__BBOX:::CAM_TARGET',1124,24,0x10,1)]
    payload=object();source=SimpleNamespace(symbols=local+exports,payload=payload)
    emitted=bank_before_model(source)
    assert emitted.symbols[:2]==local
    assert emitted.symbols[2][0].startswith('__AnimationBank:::')
    assert set(emitted.symbols[2:])==set(exports)
    assert source.symbols==local+exports and emitted.payload is payload
