"""Actual native container reader, row layout and participant choice lifetime on invented data.

The container is packed by the Python compiler and decoded by the real C readers, so the shared layout
(setup/fighter_caf_layout.py -> src/patches/fighter_caf_layout.h) is checked field by field across both languages.
"""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import pytest
from test_fighter_caf_outfits import fixture
from fighter_caf import encode
import fighter_caf_layout as layout
from test_fighter_match_teardown_native import definition

ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "patches/fighter_caf_layout.h"
static uint8_t memory[0x400000];
#define MEM32(address) (*(uint32_t *)(memory+(uint32_t)(address)))
#define CAF_MAX_ROWS (16384u*3u)
#define EXTRA_MAX (16u*1024u*1024u)
static uint32_t s_count,s_extra_count;
static uint32_t s_menu_selection[4],s_menu_outfit[4],s_service,s_contexts[4];
static uint32_t s_story_profiles[4];
static uint8_t *s_rows,*s_extras;
static const uint8_t *s_recipes[4];
static void restore_finishers(void) {}
static void defjam_caf_faces_clear(void) {} /* Sculpt lifetime is tested separately. */
@FUNCTIONS@
static uint8_t *readfile(const char *path,size_t *size) {
 FILE *file=fopen(path,"rb");assert(file);uint8_t *bytes=(uint8_t *)malloc(CAF_CONTAINER_MAX_BYTES);assert(bytes);
 *size=fread(bytes,1,CAF_CONTAINER_MAX_BYTES,file);fclose(file);return bytes;
}
int main(int argc,char **argv) {
 assert(argc==3);size_t size;const char *mode=argv[2];
 uint8_t *data=readfile(argv[1],&size);uint32_t rc,ec,eb,fc;
 if(!strcmp(mode,"bad-header")){assert(!defjam_fighter_caf_container(data,size,&rc,&ec,&eb,&fc));return 0;}
 assert(defjam_fighter_caf_container(data,size,&rc,&ec,&eb,&fc));
 s_rows=data+CAF_CONTAINER_HEADER_BYTES;s_count=rc;
 if(!strcmp(mode,"bad-recipe")){assert(!recipes_valid(s_rows,rc));return 0;}
 assert(recipes_valid(s_rows,rc));
 s_extras=s_rows+(size_t)rc*CAF_ROW_STRIDE;s_extra_count=ec;
 if(!strcmp(mode,"bad-extra")){assert(!extras_valid(s_extras,eb,ec));return 0;}
 assert(ec && extras_valid(s_extras,eb,ec));
 if(!strcmp(mode,"dump")) {
  /* Every named field the runtime reads, as the C readers see it. */
  printf("counts %u %u %u\n",rc,ec,fc);
  for(uint32_t i=0;i<rc;++i) {
   const uint8_t *row=s_rows+(size_t)i*CAF_ROW_STRIDE;
   printf("row %u %u %u %u %u %u %u %u %u %u %u %u %u\n",word(row+CAF_ROW_SELECTION),word(row+CAF_ROW_CORE),word(row+CAF_ROW_OUTFIT),
    word(row+CAF_ROW_ALIAS),word(row+CAF_ROW_VOICE),word(row+CAF_ROW_STYLE_COUNT),word(row+CAF_ROW_TRAINING_AT(0)),word(row+CAF_ROW_TRAINING_AT(4)),
    word(row+CAF_ROW_VALUE_AT(5)),word(row+CAF_ROW_VALUE_AT(12)),row[CAF_ROW_STYLE_AT(0)],row[CAF_ROW_STYLE_AT(2)],row[CAF_ROW_RETAIL]);
  }
  for(uint32_t i=0;i<ec;++i) {
   const uint8_t *row=s_extras+(size_t)i*CAF_EXTRA_STRIDE;
   printf("extra %u %u %u %u %u %u %u\n",word(row+CAF_EXTRA_SELECTION),word(row+CAF_EXTRA_OUTFIT),word(row+CAF_EXTRA_HAS_FINISHERS),
    word(row+CAF_EXTRA_FINISHER_AT(0)),word(row+CAF_EXTRA_FINISHER_AT(3)),word(row+CAF_EXTRA_ATLAS_AT(0)),word(row+CAF_EXTRA_ATLAS_AT(1)));
  }
  return 0;
 }
 assert(!defjam_fighter_caf_outfit(4,100,0));assert(!defjam_fighter_caf_outfit(0,100,3));
 assert(!defjam_fighter_caf_outfit(0,101,0));
 assert(defjam_fighter_caf_outfit(0,100,2));assert(defjam_fighter_caf_outfit(1,100,1));
 assert(defjam_fighter_caf_presentation(0,100)==0x60000001);
 assert(defjam_fighter_caf_presentation(1,100)==0x60000000);
 assert(defjam_fighter_caf_presentation(2,100)==100);
 assert(defjam_fighter_caf_presentation(0,56)==56);
 assert(word(extra_row(100,2)+CAF_EXTRA_OUTFIT)==2);
 /* Unconfirmed routes (random/CPU picks, a re-bind) play the default outfit; a confirmation only applies to its own fighter. */
 assert(confirmed_outfit(0,100)==2 && confirmed_outfit(1,100)==1);
 assert(confirmed_outfit(2,100)==0 && confirmed_outfit(0,101)==0 && confirmed_outfit(4,100)==0);
 defjam_fighter_caf_clear(); /* Native match teardown/rematch retains choices. */
 assert(s_menu_outfit[0]==2 && s_menu_outfit[1]==1);
 defjam_fighter_caf_menu_clear(0);assert(!s_menu_selection[0] && s_menu_outfit[1]==1);
 defjam_fighter_caf_menu_clear(UINT32_MAX);assert(!s_menu_selection[1]);
 free(data);return 0;
}
'''


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    cc=shutil.which('cl') if os.name=='nt' else shutil.which('cc')
    if not cc:pytest.skip('Native compiler unavailable')
    folder=tmp_path_factory.mktemp('caf-outfits')
    text=(ROOT/'src/patches/fighter_caf.c').read_text()
    names=['word','row_outfit','recipes_valid','defjam_fighter_caf_container','defjam_fighter_caf_menu_clear','defjam_fighter_caf_outfit',
           'confirmed_outfit','defjam_fighter_caf_presentation','extras_valid','defjam_fighter_caf_clear']
    functions=definition(text,'word')+'\n'+definition(text,'row_outfit')
    for name in ('recipe_row','extra_row'):
        match=re.search(r'static const uint8_t \*'+name+r'\([^)]*\)\s*\{',text);end,depth=match.end(),1
        while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
        functions+='\n'+text[match.start():end]
    functions+='\n'+'\n'.join(definition(text,n) for n in names[2:])
    source=folder/'test.c';source.write_text(DRIVER.replace('@FUNCTIONS@',functions))
    exe=folder/('test.exe' if os.name=='nt' else 'test')
    include=str(ROOT/'src')
    command=[cc,'/nologo','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS','/I'+include,str(source),'/Fe:'+str(exe)] if os.name=='nt' else [cc,'-std=c11','-Wall','-Wextra','-Werror','-I',include,str(source),'-o',str(exe)]
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return exe


def container(item=None,report=None):
    if item is None:item,report=fixture()
    return bytearray(encode({'example/fighter':item},report)),item,report


def run(native,tmp_path,raw,mode):
    path=tmp_path/'fighter-caf.bin';path.write_bytes(raw)
    return subprocess.run([native,path,mode],capture_output=True,text=True)


def row_at(index):return layout.HEADER_BYTES+index*layout.RECIPE_STRIDE
def extra_at(raw,index):return layout.unpack_header(raw)['extras_offset']+index*layout.EXTRA_STRIDE


@pytest.mark.parametrize('damage',[None,'index','gap','combat','alias','extra-index','extra-combat','extra-unbound'])
def test_pair_readers_and_independent_participant_lifetime(native,tmp_path,damage):
    raw,_,_=container()
    changes={'index':(row_at(1)+layout.RECIPE['outfit'],0),'gap':(row_at(1)+layout.RECIPE['outfit'],2),
             'combat':(row_at(1)+layout.RECIPE['training'],21),'alias':(row_at(1)+layout.RECIPE['alias'],100),
             'extra-index':(extra_at(raw,1)+layout.EXTRA['outfit'],3),'extra-combat':(extra_at(raw,1)+layout.EXTRA['finishers'],1),
             'extra-unbound':(extra_at(raw,1)+layout.EXTRA['selection'],101)}
    if damage:at,value=changes[damage];struct.pack_into('<I',raw,at,value)
    mode='bad-extra' if damage and damage.startswith('extra-') else 'bad-recipe' if damage else 'good'
    result=run(native,tmp_path,raw,mode)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('damage',[None,'missing-mode','wrong-core','reserved'])
def test_native_retail_moveset_rows_require_explicit_mode_and_original_core(native,tmp_path,damage):
    item,report=fixture();item.update(core=5,retail_moveset='retail/blaze')
    raw,_,_=container(item,report)
    if damage=='missing-mode':raw[row_at(1)+layout.RECIPE['retail']]=0
    if damage=='wrong-core':struct.pack_into('<I',raw,row_at(0)+layout.RECIPE['core'],87)
    if damage=='reserved':raw[row_at(1)+layout.RECIPE['retail']+1]=1
    result=run(native,tmp_path,raw,'bad-recipe' if damage else 'good')
    assert result.returncode==0,result.stdout+result.stderr


def test_the_runtime_reads_back_every_named_field_the_compiler_wrote(native,tmp_path):
    """Packed in Python, decoded by the real C readers through the generated layout header."""
    raw,item,report=container()
    result=run(native,tmp_path,raw,'dump')
    assert result.returncode==0,result.stdout+result.stderr
    lines=[line.split() for line in result.stdout.splitlines()]
    assert lines[0]==['counts','3','3','0']
    recipe=item['recipe']
    for index in range(3):
        # selection core outfit alias voice style_count training[0] training[4] values[5] values[12] styles[0] styles[2] retail
        expected=['row','100','101',str(index),str(item['outfit_aliases'][index]),'5','3','20','20','4',str(index),'1','3','0']
        assert lines[1+index]==expected,(lines[1+index],expected)
    for index in range(3):
        extra=lines[4+index]
        assert extra[:5]==['extra','100',str(index),'1','52'] and extra[5]=='39'
        # Atlas 0 is a block inside the extras section, so its offset starts after the three rows.
        assert int(extra[6])>=3*layout.EXTRA_STRIDE and extra[7]=='0'
    assert recipe['caf_values'][5]==4


@pytest.mark.parametrize('damage',['magic','version','total','recipe-offset','extras-offset','faces-offset','extras-bytes','truncated','trailing','recipe-count'])
def test_container_header_must_tile_the_file_exactly(native,tmp_path,damage):
    raw,_,_=container()
    h=layout.HEADER
    word=lambda name:8+4*h.index(name)
    if damage=='magic':raw[:4]=b'FCA3'
    if damage=='version':struct.pack_into('<I',raw,4,2)
    if damage=='total':struct.pack_into('<I',raw,word('total_bytes'),len(raw)+4)
    if damage=='recipe-offset':struct.pack_into('<I',raw,word('recipe_offset'),layout.HEADER_BYTES+4)
    if damage=='extras-offset':struct.pack_into('<I',raw,word('extras_offset'),layout.unpack_header(raw)['extras_offset']-4)
    if damage=='faces-offset':struct.pack_into('<I',raw,word('faces_offset'),layout.unpack_header(raw)['faces_offset']+4)
    if damage=='extras-bytes':struct.pack_into('<I',raw,word('extras_bytes'),layout.unpack_header(raw)['extras_bytes']-4)
    if damage=='truncated':raw=raw[:-4]
    if damage=='trailing':raw+=b'\0\0\0\0'
    if damage=='recipe-count':struct.pack_into('<I',raw,word('recipe_count'),0)
    result=run(native,tmp_path,raw,'bad-header')
    assert result.returncode==0,result.stdout+result.stderr
