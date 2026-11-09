"""Sealed event files, coupled identity claims and native routing admission."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest
from test_fighter_timelines import tags,cameras
from test_fighter_ui_native import TYPES
from fighter_timelines import encode_timeline_bindings

ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "patches/fighter_events.h"
static int enabled=1;
int defjam_fighter_research_active(void){return enabled;}
static void environment(const char *k,const char *v){
#ifdef _WIN32
 assert(!_putenv_s(k,v));
#else
 assert(!setenv(k,v,1));
#endif
}
int main(int argc,char **argv){
 assert(argc==7);
 environment("RECOMP_FIGHTER_TAGS",argv[1]);environment("RECOMP_FIGHTER_CAMERAS",argv[2]);
 environment("RECOMP_FIGHTER_TIMELINE_BINDINGS",argv[3]);
 environment("RECOMP_FIGHTER_TAGS_SHA256",argv[4]);environment("RECOMP_FIGHTER_CAMERAS_SHA256",argv[5]);
 if(!strcmp(argv[6],"inactive"))enabled=0;
 int ok=defjam_fighter_events_start();
 if(strcmp(argv[6],"good")){assert(!ok);return 0;}
 assert(ok);assert(!strcmp(defjam_fighter_events_tags_path(),argv[1]));
 assert(!strcmp(defjam_fighter_events_cameras_path(),argv[2]));
 assert(defjam_fighter_events_has("P0000_A",3));assert(defjam_fighter_events_has("P0000_B",1));
 assert(!defjam_fighter_events_has("P0000_B",2));assert(!defjam_fighter_events_has("P0000_C",0));
 assert(!defjam_fighter_events_has("P0000_A",4));assert(!defjam_fighter_events_has("verylongname",1));
 assert(!defjam_fighter_events_start());return 0;
}
'''


@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:pytest.skip('native C compiler unavailable')
    folder=tmp_path_factory.mktemp('events-native');(folder/'recomp/gen').mkdir(parents=True)
    (folder/'recomp/gen/recomp_types.h').write_text(TYPES,encoding='utf-8')
    driver=folder/'driver.c';driver.write_text(DRIVER,encoding='utf-8')
    exe=folder/('events.exe' if os.name=='nt' else 'events')
    sources=[str(driver),str(ROOT/'src/patches/fighter_events.c')]
    command=([cc,'/nologo','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS','/I'+str(folder),'/I'+str(ROOT/'src'),*sources,'/Fe:'+str(exe)]
             if os.name=='nt' else [cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror',
                                    '-I',str(folder),'-I',str(ROOT/'src'),*sources,'-o',str(exe)])
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


@pytest.fixture
def files(tmp_path):
    tag,camera=tags(),cameras()
    tag_source=tag.library.export(tag.by_name['N0001_A']['events'])
    tag_data=tag.compose({name:{'template':'N0001_A','timeline':tag_source} for name in ('P0000_A','P0000_B')})
    camera_data=camera.compose({'P0000_A':{'template':'N0001_A',
                                           'timeline':camera.library.export(camera.by_name['N0001_A']['events'])}})
    bindings=encode_timeline_bindings(tag_data,camera_data,{'P0000_A':3,'P0000_B':1})
    paths=[tmp_path/name for name in ('tags.dat','camera.xml','events.bin')]
    for path,data in zip(paths,[tag_data,camera_data,bindings]):path.write_bytes(data)
    return [*paths,hashlib.sha256(tag_data).hexdigest(),hashlib.sha256(camera_data).hexdigest()]


@pytest.mark.parametrize('mode',['good','inactive'])
def test_timeline_generation_and_claims(tool,files,mode):
    result=subprocess.run([str(tool),*map(str,files),mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('offset,value',[(4,2),(8,0),(8,65536),(12,0),(16,0),(20,1),(24,1),(28,1),
                                       (32,0),(96,0),(104,4),(108,0)])
def test_corrupt_timeline_metadata_rejected(tool,files,offset,value):
    data=bytearray(files[2].read_bytes());struct.pack_into('<I',data,offset,value);files[2].write_bytes(data)
    result=subprocess.run([str(tool),*map(str,files),'reject'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


def test_changed_native_event_files_rejected(tool,files):
    files[0].write_bytes(files[0].read_bytes()+b'changed')
    result=subprocess.run([str(tool),*map(str,files),'reject'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
