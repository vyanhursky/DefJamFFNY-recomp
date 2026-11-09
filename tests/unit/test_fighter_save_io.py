"""Actual C write/close recognizer: failed attempts cannot produce receipts."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from test_fighter_profile_store import container

PROBE = r'''
#include "fighter_save_io.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static FighterSaveIO io;
static unsigned char source[FIGHTER_SAVE_IO_MAX];
int main(int argc,char **argv) {
    const uint8_t *out=0; uint32_t size=0;
    FILE *f=fopen(argv[1],"rb"); if(!f)return 1;
    uint32_t n=(uint32_t)fread(source,1,sizeof source,f);fclose(f);
    int mode=atoi(argv[2]), result;
    if(mode==10) {
        if(fighter_save_io_write(&io,7,source+0x4c,64,64,1))return 20;
        return fighter_save_io_close(&io,7,1,&out,&size)!=0;
    }
    if(mode==11) {
        for(uint32_t i=0;i<16;++i)if(fighter_save_io_write(&io,i,source,0x4c,0x4c,1)!=1)return 21;
        if(fighter_save_io_write(&io,16,source,0x4c,0x4c,1)!=-1)return 22;
        for(uint32_t i=0;i<16;++i)if(fighter_save_io_close(&io,i,1,&out,&size)!=-1)return 23;
        return 0;
    }
    if(mode==7)source[4]^=1;
    result=fighter_save_io_write(&io,7,source,mode==9?n:0x4c,mode==9?n:0x4c,mode!=2);
    if(mode==2 || mode==7) {
        if(result!=-1)return 2;
    } else {
        if(result!=1)return 3;
        if(mode==3)fighter_save_io_seek(&io,7);
        if(mode!=9 && mode!=6) {
            result=fighter_save_io_write(&io,7,source+0x4c,64,64,1);
            if(mode==3) {if(result!=-1)return 4;}
            else if(result!=1)return 5;
            result=fighter_save_io_write(&io,7,source+0x8c,n-0x8c,n-0x8c-(mode==1),1);
            if(mode==1 || mode==3) {if(result!=-1)return 6;}
            else if(result!=1)return 7;
        }
        if(mode==5 && fighter_save_io_write(&io,7,source,1,1,1)!=-1)return 8;
    }
    result=fighter_save_io_close(&io,7,mode!=4,&out,&size);
    if(mode>=1 && mode<=7) return result!=-1;
    if(result!=1 || size!=n || memcmp(out,source,n))return 9;
    if(fighter_save_io_close(&io,7,1,&out,&size)!=0)return 10;
    if(mode==8) {
        if(fighter_save_io_write(&io,7,source,n,n,1)!=1)return 11;
        if(fighter_save_io_close(&io,7,1,&out,&size)!=1)return 12;
    }
    return 0;
}
'''


@pytest.fixture(scope='module')
def io_probe(tmp_path_factory):
    compiler = shutil.which('cl') if os.name == 'nt' else shutil.which('cc')
    if not compiler:
        pytest.skip('Native C compiler unavailable')
    root = Path(__file__).resolve().parents[2]
    folder = tmp_path_factory.mktemp('fighter-save-io-c')
    source = folder / 'probe.c'; source.write_text(PROBE)
    exe = folder / ('probe.exe' if os.name == 'nt' else 'probe')
    inputs = [str(source), str(root / 'src/hooks/fighter_save_io.c')]
    command = ([compiler, '/nologo', '/TC', '/I' + str(root / 'src/hooks'), *inputs, '/Fe' + str(exe)]
               if os.name == 'nt' else [compiler, '-std=c11', '-I', str(root / 'src/hooks'), *inputs, '-o', str(exe)])
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return exe


@pytest.mark.parametrize('mode', range(12))
@pytest.mark.parametrize('payload_size', [0x1490, 0x5904])
def test_native_full_write_and_close_witness(io_probe, tmp_path, mode, payload_size):
    path = tmp_path / 'synthetic-mc02.bin'; path.write_bytes(container(bytes(payload_size)))
    result = subprocess.run([str(io_probe), str(path), str(mode)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, (mode, result.stdout, result.stderr, result.returncode)
