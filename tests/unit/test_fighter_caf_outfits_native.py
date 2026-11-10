"""Actual native readers and participant choice lifetime on invented data."""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import pytest
from test_fighter_caf_outfits import fixture
from fighter_caf import encode
from fighter_caf_extras import encode as encode_extras
from test_fighter_match_teardown_native import definition

ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint8_t memory[0x400000];
#define MEM32(address) (*(uint32_t *)(memory+(uint32_t)(address)))
#define CAF_ROW 232u
#define CAF_MAX 16384u
#define EXTRA_ROW 48u
#define EXTRA_MAX (16u*1024u*1024u)
#define ATLAS_BYTES (256u*256u*4u)
static uint32_t s_row_stride=240,s_extra_stride=52,s_count=3,s_extra_count=3;
static uint32_t s_menu_selection[4],s_menu_outfit[4],s_service,s_contexts[4];
static uint32_t s_story_profiles[4];
static uint8_t *s_rows,*s_extras;
static const uint8_t *s_recipes[4];
static void restore_finishers(void) {}
static void defjam_caf_faces_clear(void) {} /* Sculpt lifetime is tested separately. */
@FUNCTIONS@
static uint8_t *readfile(const char *path,size_t *size) {
 FILE *file=fopen(path,"rb");assert(file);uint8_t *bytes=(uint8_t *)malloc(EXTRA_MAX);assert(bytes);
 *size=fread(bytes,1,EXTRA_MAX,file);fclose(file);return bytes;
}
int main(int argc,char **argv) {
 assert(argc==4);size_t size,extra_size;
 s_rows=readfile(argv[1],&size);s_extras=readfile(argv[2],&extra_size);
 if(!strcmp(argv[3],"bad-recipe")){assert(!recipes_valid(s_rows,size));return 0;}
 assert(recipes_valid(s_rows,size));
 if(!strcmp(argv[3],"bad-extra")){assert(!extras_valid(s_extras,extra_size));return 0;}
 assert(extras_valid(s_extras,extra_size));
 assert(!defjam_fighter_caf_outfit(4,100,0));assert(!defjam_fighter_caf_outfit(0,100,3));
 assert(!defjam_fighter_caf_outfit(0,101,0));
 assert(defjam_fighter_caf_outfit(0,100,2));assert(defjam_fighter_caf_outfit(1,100,1));
 assert(defjam_fighter_caf_presentation(0,100)==0x60000001);
 assert(defjam_fighter_caf_presentation(1,100)==0x60000000);
 assert(defjam_fighter_caf_presentation(2,100)==100);
 assert(defjam_fighter_caf_presentation(0,56)==56);
 assert(word(extra_row(100,2)+48)==2);
 defjam_fighter_caf_clear(); /* Native match teardown/rematch retains choices. */
 assert(s_menu_outfit[0]==2 && s_menu_outfit[1]==1);
 defjam_fighter_caf_menu_clear(0);assert(!s_menu_selection[0] && s_menu_outfit[1]==1);
 defjam_fighter_caf_menu_clear(UINT32_MAX);assert(!s_menu_selection[1]);
 free(s_rows);free(s_extras);return 0;
}
'''


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else shutil.which('cc')
    if not cc:pytest.skip('Native compiler unavailable')
    folder=tmp_path_factory.mktemp('caf-outfits')
    text=(ROOT/'src/patches/fighter_caf.c').read_text()
    names=['word','row_outfit','recipes_valid','defjam_fighter_caf_menu_clear','defjam_fighter_caf_outfit','defjam_fighter_caf_presentation','extras_valid','defjam_fighter_caf_clear']
    functions=definition(text,'word')+'\n'+definition(text,'row_outfit')
    for name in ('recipe_row','extra_row'):
        match=re.search(r'static const uint8_t \*'+name+r'\([^)]*\)\s*\{',text);end,depth=match.end(),1
        while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
        functions+='\n'+text[match.start():end]
    functions+='\n'+'\n'.join(definition(text,n) for n in names[2:])
    source=folder/'test.c';source.write_text(DRIVER.replace('@FUNCTIONS@',functions))
    exe=folder/('test.exe' if os.name=='nt' else 'test')
    command=[cc,'/nologo','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS',str(source),'/Fe:'+str(exe)] if os.name=='nt' else [cc,'-std=c11','-Wall','-Wextra','-Werror',str(source),'-o',str(exe)]
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


@pytest.mark.parametrize('damage',[None,'index','gap','combat','alias','extra-index','extra-combat','extra-unbound'])
def test_pair_readers_and_independent_participant_lifetime(native,tmp_path,damage):
    item,report=fixture();rows=bytearray(encode({'example/fighter':item},report));extras=bytearray(encode_extras({'example/fighter':item},report))
    changes={'index':(rows,16+240+232,0),'gap':(rows,16+240+232,2),'combat':(rows,16+240+8,21),'alias':(rows,16+240+236,100),
             'extra-index':(extras,16+52+48,3),'extra-combat':(extras,16+52+8,1),'extra-unbound':(extras,16+52,101)}
    if damage:target,at,value=changes[damage];struct.pack_into('<I',target,at,value)
    recipe=tmp_path/'recipes.bin';recipe.write_bytes(rows);extra=tmp_path/'extras.bin';extra.write_bytes(extras)
    mode='bad-extra' if damage and damage.startswith('extra-') else 'bad-recipe' if damage else 'good'
    result=subprocess.run([native,recipe,extra,mode],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('damage',[None,'old-header','missing-mode','wrong-core','reserved'])
def test_native_v3_retail_moveset_rows_require_explicit_mode_and_original_core(native,tmp_path,damage):
    item,report=fixture();item.update(core=5,retail_moveset='retail/blaze')
    rows=bytearray(encode({'example/fighter':item},report));extras=encode_extras({'example/fighter':item},report)
    if damage=='old-header':rows[:8]=b'FCA2'+struct.pack('<I',2)
    if damage=='missing-mode':rows[16+225]=0
    if damage=='wrong-core':struct.pack_into('<I',rows,20,87)
    if damage=='reserved':rows[16+226]=1
    recipe=tmp_path/'retail.bin';recipe.write_bytes(rows);extra=tmp_path/'extras.bin';extra.write_bytes(extras)
    result=subprocess.run([native,recipe,extra,'bad-recipe' if damage else 'good'],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
