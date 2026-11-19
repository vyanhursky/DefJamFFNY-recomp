"""Production native stat writes and admission on compiler-produced outfit rows."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"setup"))
from fighter_caf import encode_rows
from fighter_caf_layout import RECIPE as R
from test_fighter_caf_outfits import fixture
from test_fighter_caf_outfits_native import native as reader, container, run, row_at
from test_fighter_match_teardown_native import definition
ROOT=Path(__file__).resolve().parents[2]


def test_native_final_attribute_writes_are_participant_local_and_opt_in(tmp_path):
    cc=shutil.which('cc') if os.name!='nt' else shutil.which('cl')
    if not cc: pytest.skip('native C compiler unavailable')
    item,report=fixture()
    for o in item['outfits']:o['recipe']['final_stats']=dict(zip(('upper','lower','speed','toughness','health','charisma'),(30,47,37,27,47,30)))
    _,raw=encode_rows({'example/fighter':item},report);(tmp_path/'rows.bin').write_bytes(raw)
    production=(ROOT/'src/patches/fighter_caf.c').read_text(encoding='utf-8')
    source=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "patches/fighter_caf_layout.h"
static unsigned char memory[0x400000];
static uint32_t s_service,s_story_profiles[4];
static const uint8_t *s_recipes[4];
#define MEM32(a) (*(uint32_t *)(memory+(a)))
@FUNCTIONS@
int main(int argc,char **argv) {
 assert(argc==2);unsigned char rows[3*CAF_ROW_STRIDE];FILE *f=fopen(argv[1],"rb");assert(f);
 assert(fread(rows,1,sizeof rows,f)==sizeof rows);fclose(f);
 const uint32_t expected[]={6,9,7,5,9,6};
 for(unsigned slot=0;slot<4;++slot) {
  memset(memory,0xA5,sizeof memory);apply_final_stats(1024,slot,rows+(slot%3)*CAF_ROW_STRIDE);
  for(unsigned i=0;i<4;++i)for(unsigned j=0;j<7;++j) {
   uint32_t value=MEM32(1024+0x2b0+i*0x1c+j*4);
   assert(value==(i!=slot||j==5?0xA5A5A5A5:expected[j==6?5:j]));
  }
 }
 static unsigned char before[sizeof memory];memcpy(before,memory,sizeof memory);
 apply_final_stats(1024,4,rows);assert(!memcmp(before,memory,sizeof memory));
 rows[CAF_ROW_FINAL_STATS]=0;apply_final_stats(1024,0,rows);assert(!memcmp(before,memory,sizeof memory));
 rows[CAF_ROW_FINAL_STATS]=1;s_service=1024;
 for(unsigned slot=0;slot<4;++slot) {
  uint32_t actor=0x3b92e0+slot*0x12e8;s_recipes[slot]=rows;
  MEM32(actor+0x28)=slot;MEM32(actor+0x2c)=word(rows+CAF_ROW_CORE)-1;
  defjam_fighter_caf_actor_stats(actor);
  for(unsigned j=0;j<7;++j)assert(MEM32(actor+0xb34+j*4)==(j==5?0:expected[j==6?5:j]));
  /* Explicit zero attributes must not fall back to original motion parameters. */
  unsigned char zero[CAF_ROW_STRIDE];memcpy(zero,rows,sizeof zero);
  memset(zero+CAF_ROW_TRAINING,0,20);zero[CAF_ROW_CHARISMA]=0;s_recipes[slot]=zero;
  defjam_fighter_caf_actor_stats(actor);
  for(unsigned j=0;j<7;++j)assert(!MEM32(actor+0xb34+j*4));
  /* Story-owned, mismatched and legacy actors retain every parameter. */
  memset(memory+actor+0xb34,0xA5,28);s_story_profiles[slot]=1;
  defjam_fighter_caf_actor_stats(actor);s_story_profiles[slot]=0;
  assert(MEM32(actor+0xb34)==0xA5A5A5A5);
  MEM32(actor+0x2c)=999;defjam_fighter_caf_actor_stats(actor);
  assert(MEM32(actor+0xb34)==0xA5A5A5A5);
  MEM32(actor+0x2c)=word(rows+CAF_ROW_CORE)-1;zero[CAF_ROW_FINAL_STATS]=0;
  defjam_fighter_caf_actor_stats(actor);assert(MEM32(actor+0xb34)==0xA5A5A5A5);
  s_recipes[slot]=rows;
 }
 defjam_fighter_caf_actor_stats(0);defjam_fighter_caf_actor_stats(0x3b92e1);
 return 0;
}
'''.replace('@FUNCTIONS@',definition(production,'word')+'\n'+definition(production,'apply_final_stats')+'\n'+definition(production,'defjam_fighter_caf_actor_stats'))
    file=tmp_path/'test.c';file.write_text(source);exe=tmp_path/('test.exe' if os.name=='nt' else 'test')
    args=[cc,'/nologo','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS','/I'+str(ROOT/'src'),str(file),'/Fe:'+str(exe)] if os.name=='nt' else [cc,'-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'src'),str(file),'-o',str(exe)]
    result=subprocess.run(args,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
    result=subprocess.run([exe,tmp_path/'rows.bin'],capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('damage', [None,'mode','charisma','range','outfit-mismatch','legacy-charisma'])
def test_native_reader_validates_final_stat_contract(reader,tmp_path,damage):
    item,report=fixture()
    for o in item['outfits']:o['recipe']['final_stats']=dict.fromkeys(('upper','lower','speed','toughness','health','charisma'),50)
    raw,_,_=container(item,report)
    if damage=='mode':raw[row_at(0)+R['final_stats']]=2
    if damage=='charisma':raw[row_at(0)+R['charisma']]=51
    if damage=='range':struct.pack_into('<I',raw,row_at(0)+R['training'],51)
    if damage=='outfit-mismatch':raw[row_at(1)+R['charisma']]=99
    if damage=='legacy-charisma':raw[row_at(0)+R['final_stats']]=0
    result=run(reader,tmp_path,raw,'bad-recipe' if damage else 'dump')
    assert result.returncode==0,result.stdout+result.stderr
