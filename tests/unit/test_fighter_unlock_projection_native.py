"""Selection clearing must retire live custom unlock marks, retaining history."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from test_fighter_match_teardown_native import definition
from test_fighter_ui_native import TYPES
from test_fighter_native import catalog, pack
from fighter_window import encode_window

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "fighter_window.h"
#include "fighter_bindings.h"
#include "fighter_unlocks.h"
unsigned char memory[0x10000];
uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
int g_fp_top;
static FighterWindow s_window;
static FighterBindings s_bindings;
static FighterWindowRow rows[5];
static uint32_t s_settings=0x1000,s_validated_database=1,s_custom_count=5;
static uint32_t s_custom_keys[5],s_custom_metadata[5];
void defjam_fighter_caf_menu_clear(uint32_t slot){assert(slot<4 || slot==UINT32_MAX);}
int defjam_fighter_caf_outfit(uint32_t slot,uint32_t selection,uint32_t index){(void)slot;(void)selection;(void)index;abort();}
#ifdef _MSC_VER
__declspec(noreturn)
#else
_Noreturn
#endif
static void fighter_stop(const char *message){fprintf(stderr,"%s\n",message);exit(23);}
int fighter_bindings_find(const FighterBindings *bindings,FighterBindingKey domain,uint32_t key,FighterBinding *out){
 assert(bindings==&s_bindings&&domain==FIGHTER_BINDING_STABLE);
 memset(out,0,sizeof *out);out->stable_handle=key;
 if(key>=0x1000&&key<0x1000+75)return 1;
 for(unsigned i=0;i<5;i++)if(rows[i].stable_handle==key){out->flags=1;return 1;}
 for(unsigned i=0;i<4;i++)if(s_window.banks[i].private_handle==key){out->flags=1;return 1;}
 return 0;
}
static void validate_immutable_banks(void){}
static int remember_custom(uint32_t mark){(void)mark;return 0;}
static void custom_progress_changed(void){assert(!"existing historical progress must not change");}
static void defjam_fighter_selection_gate(uint32_t selection){(void)selection;assert(!"missing window");}
@FUNCTIONS@
static void submit(int participant,uint32_t selection){
 char text[4][32];int values[4]={participant,participant<0?-1:0,(int)selection,0};
 for(unsigned i=0;i<4;i++){
  snprintf(text[i],sizeof text[i],"%d",values[i]);
  strcpy((char*)memory+0x9000+i*32,text[i]);MEM32(0x8000+i*4)=0x9000+i*32;
 }
 (void)defjam_fighter_controller_submission(0x8000);
}
int main(int argc,char **argv){
 assert(argc==3);FILE *file=fopen(argv[1],"rb");assert(file);
 unsigned char bytes[1024];size_t size=fread(bytes,1,sizeof bytes,file);fclose(file);
 assert(fighter_window_decode(&s_window,bytes,size));s_bindings.bytes=bytes;
 for(unsigned i=0;i<5;i++){
  assert(fighter_window_at(&s_window,i,&rows[i]));
  s_custom_keys[i]=rows[i].stable_handle;s_custom_metadata[i]=FIGHTER_UNLOCK_METADATA;
  if(i<4){FighterWindowRow row;assert(fighter_window_bind(&s_window,i,rows[i].selection_key,&row));}
 }
 MEM32(s_settings+0x20)=MEM32(s_settings+0x1264)=79;
 for(unsigned i=0;i<75;i++)MEM32(s_settings+0x12E0+4*i)=0x1000+i;
 for(unsigned i=0;i<4;i++)MEM32(s_settings+0x12E0+4*(75+i))=rows[i].stable_handle|FIGHTER_UNLOCK_METADATA;
 MEM32(s_settings+0x12E0+79*4)=0xDEAD;
 unsigned expected=78;
 if(!strcmp(argv[2],"bad-count"))MEM32(s_settings+0x20)=81;
 if(!strcmp(argv[2],"all")){submit(-1,0);expected=75;}
 else if(!strcmp(argv[2],"ready")){
  strcpy((char*)memory+0xA000,"Fighters.KeepReady(2)");
  assert(defjam_fighter_ui_command(0xA000)==1);expected=76;
 }else{
  submit(0,1);
  if(!strcmp(argv[2],"bind")){submit(0,rows[4].selection_key);expected=79;}
 }
 assert(MEM32(s_settings+0x20)==expected&&MEM32(s_settings+0x1264)==expected);
 for(unsigned retail=0;retail<75;retail++){
  unsigned found=0;
  for(unsigned i=0;i<expected;i++)if(MEM32(s_settings+0x12E0+i*4)==0x1000+retail)found++;
  assert(found==1);
 }
 for(unsigned i=expected;i<80;i++)assert(MEM32(s_settings+0x12E0+i*4)==0);
 for(unsigned i=0;i<expected;i++){
  uint32_t mark=MEM32(s_settings+0x12E0+i*4),identity=mark&~FIGHTER_UNLOCK_METADATA;
  assert(identity!=rows[0].stable_handle);
  if(identity<0x1000)assert(mark&FIGHTER_UNLOCK_METADATA);
 }
 for(unsigned i=0;i<5;i++)assert(s_custom_keys[i]==rows[i].stable_handle&&s_custom_metadata[i]==FIGHTER_UNLOCK_METADATA);
 assert(s_custom_count==5);return 0;
}
'''


@pytest.fixture(scope='module')
def projection(tmp_path_factory):
    cc = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not cc:
        pytest.skip('Native compiler unavailable')
    folder = tmp_path_factory.mktemp('fighter-unlock-projection')
    (folder / 'recomp/gen').mkdir(parents=True)
    (folder / 'recomp/gen/recomp_types.h').write_text(TYPES, encoding='utf-8')
    runtime = (ROOT / 'src/patches/fighter_runtime.c').read_text(encoding='utf-8')
    names = ['submission_integer', 'defjam_fighter_controller_submission', 'defjam_fighter_ui_command']
    helper = 'prune_participant_unlocks'
    if 'static void ' + helper + '(' in runtime:
        names.insert(0, helper)
    functions = '\n'.join(definition(runtime, name) for name in names)
    source = folder / 'probe.c'
    source.write_text(DRIVER.replace('@FUNCTIONS@', functions), encoding='utf-8')
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    inputs = [str(source), str(ROOT / 'src/hooks/fighter_window.c')]
    command = ([cc, '/nologo', '/W4', '/WX', '/D_CRT_SECURE_NO_WARNINGS', '/I' + str(folder),
                '/I' + str(ROOT / 'src/hooks'), *inputs, '/Fe:' + str(exe)] if os.name == 'nt'
               else [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(folder),
                     '-I', str(ROOT / 'src/hooks'), *inputs, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    _, report = catalog(menu=True)[0].compile([pack(count=5)], binding_window=True)
    window = folder / 'window.bin'
    window.write_bytes(encode_window(report['window']))
    return exe, window


@pytest.mark.parametrize('mode', ['retail', 'all', 'ready', 'bind', 'bad-count'])
def test_actual_selection_clear_prunes_only_unbound_live_marks(projection, mode):
    exe, window = projection
    result = subprocess.run([str(exe), str(window), mode], capture_output=True, text=True, timeout=10)
    assert result.returncode == (23 if mode == 'bad-count' else 0), result.stdout + result.stderr
