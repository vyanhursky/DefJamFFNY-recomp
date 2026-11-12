"""Full-handle async ownership, reentrancy and narrow final-copy routing."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from test_fighter_ui_native import TYPES
ROOT=Path(__file__).resolve().parents[2]

DRIVER=r'''
#include <assert.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "patches/fighter_film_async.h"
unsigned char memory[0x400000];
static unsigned routed;
unsigned defjam_fighter_film_file(const char *path){return !strcmp(path,"assets/v2ta.viv|FI00000.viv")?7u:0u;}
uint32_t defjam_fighter_cpu_film_flags(unsigned owner,uint32_t bytes,uint32_t flags){assert(owner==7&&bytes==4096&&flags==0x500);routed++;return flags|0x8000003fu;}
int main(int argc,char **argv){
 assert(argc==2);strcpy((char *)memory+0x1000,"assets/v2ta.viv|FI00000.viv");strcpy((char *)memory+0x1100,"unowned.viv");
 unsigned previous=defjam_fighter_film_request_begin(0x1000);assert(!previous);
 defjam_fighter_film_opened(0x1234);
 /* Register before return, covering immediate callback registration. */
 FighterFilmAsyncScope before=defjam_fighter_film_callback_begin(0x1234);
 MEM32(0x3319A0)=0x1234;MEM32(0x3319AC)=0x500;memory[0x3319B0]=1;
 assert(defjam_fighter_film_allocation(0x11111,0,4096,0x500)==0x500);
 if(!strcmp(argv[1],"wrong-handle"))MEM32(0x3319A0)=0x1334;
 if(!strcmp(argv[1],"wrong-slot"))MEM32(0x3319A0)=0;
 if(!strcmp(argv[1],"wrong-flags"))MEM32(0x3319AC)=0;
 if(!strcmp(argv[1],"wrong-copy"))memory[0x3319B0]=0;
 assert(defjam_fighter_film_allocation(0x1AA99,0,4096,0x500)==0x8000053f);
 /* Unowned nested completion cannot borrow its parent's owner. */
 FighterFilmAsyncScope nested=defjam_fighter_film_callback_begin(0x1334);
 assert(defjam_fighter_film_allocation(0x1AACF,0,4096,0x500)==0x500);
 defjam_fighter_film_callback_end(nested);
 assert(defjam_fighter_film_allocation(0x1AACF,0,4096,0x500)==0x8000053f);
 defjam_fighter_film_callback_end(before);defjam_fighter_film_request_end(previous);
 assert(routed==2&&defjam_fighter_film_allocation(0x1AACF,0,4096,0x500)==0x500);
 /* A recycled low-byte row with a different generation is not that request. */
 previous=defjam_fighter_film_request_begin(0x1000);defjam_fighter_film_opened(0x2234);defjam_fighter_film_request_end(previous);
 before=defjam_fighter_film_callback_begin(0x1234);assert(defjam_fighter_film_allocation(0x1AA99,0,4096,0x500)==0x500);defjam_fighter_film_callback_end(before);
 defjam_fighter_film_cancel(0x2234);before=defjam_fighter_film_callback_begin(0x2234);assert(defjam_fighter_film_allocation(0x1AA99,0,4096,0x500)==0x500);defjam_fighter_film_callback_end(before);
 /* Nested unrelated request scopes restore the previous request owner. */
 previous=defjam_fighter_film_request_begin(0x1000);unsigned other=defjam_fighter_film_request_begin(0x1100);assert(other==7);defjam_fighter_film_opened(0x3334);defjam_fighter_film_request_end(other);defjam_fighter_film_opened(0x4434);defjam_fighter_film_request_end(previous);
 before=defjam_fighter_film_callback_begin(0x3334);assert(defjam_fighter_film_allocation(0x1AA99,0,4096,0x500)==0x500);defjam_fighter_film_callback_end(before);
 MEM32(0x3319A0)=0x4434;before=defjam_fighter_film_callback_begin(0x4434);assert(defjam_fighter_film_allocation(0x1AA99,0,4096,0x500)==0x8000053f);defjam_fighter_film_callback_end(before);
 return 0;
}
'''

@pytest.fixture(scope='module')
def tool(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else (shutil.which('cc') or shutil.which('clang'))
    if not cc:pytest.skip('native C compiler unavailable')
    folder=tmp_path_factory.mktemp('film-async-native');(folder/'recomp/gen').mkdir(parents=True)
    (folder/'recomp/gen/recomp_types.h').write_text(TYPES,encoding='utf-8')
    driver=folder/'driver.c';driver.write_text(DRIVER,encoding='utf-8')
    exe=folder/('async.exe' if os.name=='nt' else 'async')
    sources=[str(driver),str(ROOT/'src/patches/fighter_film_async.c'),str(ROOT/'src/patches/fighter_fatal.c'),str(ROOT/'tests/unit/native_stubs/host_fatal.c')]
    command=([cc,'/nologo','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS','/I'+str(folder),'/I'+str(ROOT/'src'),*sources,'/Fe:'+str(exe)]
             if os.name=='nt' else [cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror',
                                    '-I',str(folder),'-I',str(ROOT/'src'),*sources,'-o',str(exe)])
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


@pytest.mark.parametrize('mode',['good','wrong-handle','wrong-slot','wrong-flags','wrong-copy'])
def test_scoped_cinematic_async_allocation(tool,mode):
    result=subprocess.run([str(tool),mode],capture_output=True,text=True)
    assert result.returncode==(0 if mode=='good' else 1),result.stdout+result.stderr
