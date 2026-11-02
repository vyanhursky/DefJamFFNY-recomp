#!/usr/bin/env python3
"""Exercise the owner's generated SODB reader against a local database (no game).

Run from an MSVC environment (scripts/env.ps1). Extracts six fixed functions
from the user's own generated C, builds a disposable CPU-only harness beneath
logs/fighter-sod-oracle, and reports loader/index/string behavior. Generated
source/executable/data never enter the source tree. File IO is stubbed solely to
return the already loaded image; lookup/parser bodies are the generated ones.

This oracle covers the SODB loader, sorted indexes and packed handle roundtrip.
It does not
exercise the game's selection menus, saves, assets or combat, nor prove that a
large roster is playable. It needs no network or graphics/audio/input devices.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time


FUNCTIONS = ('000BE310', '000BE3D0', '000BE480', '000BE4E0', '000BE760', '000BE870')
ROOT = Path(__file__).resolve().parents[1]

PREAMBLE = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char *ram;
static uint32_t eax,ebx,ecx,edx,esi,edi,ebp,esp,g_ebp,g_seh_ebp;
static void *address(uint32_t a,size_t n) { assert(a<=64u*1024*1024 && n<=64u*1024*1024-a); return ram+a; }
#define MEM32(a) (*(uint32_t*)address((uint32_t)(a),4))
#define MEM8(a) (*(uint8_t*)address((uint32_t)(a),1))
#define PUSH32(s,v) do { (s)-=4; MEM32(s)=(uint32_t)(v); } while(0)
#define POP32(s,v) do { (v)=MEM32(s); (s)+=4; } while(0)
#define SET_LO8(r,v) ((r)=((r)&0xffffff00u)|(uint8_t)(v))
#define LO8(r) ((uint8_t)(r))
#define CMP_EQ(a,b) ((a)==(b))
#define CMP_NE(a,b) ((a)!=(b))
#define CMP_L(a,b) ((a)<(b))
#define CMP_LE(a,b) ((a)<=(b))
#define CMP_G(a,b) ((a)>(b))
#define CMP_GE(a,b) ((a)>=(b))
#define CMP_BE(a,b) ((uint32_t)(a)<=(uint32_t)(b))
#define CMP_AE(a,b) ((uint32_t)(a)>=(uint32_t)(b))
#define CMP_B(a,b) ((uint32_t)(a)<(uint32_t)(b))
#define CMP_A(a,b) ((uint32_t)(a)>(uint32_t)(b))
#define RECOMP_ABI_CALL(va,fn) fn()
static void sub_001E3FB0(void) { eax=0x10000; esp+=4; }
'''

MAIN = r'''
static uint32_t hash_name(const char *s) { uint32_t h=5381; do { h=h*33+(unsigned char)*s; } while(*s++); return h; }
static void parse_index(uint32_t cell,uint32_t out,uint32_t tagged) {
  esp=0x3f00000; PUSH32(esp,tagged); PUSH32(esp,0x1000); PUSH32(esp,MEM32(cell)); PUSH32(esp,0);
  ecx=out; sub_000BE310(); assert(esp==0x3f00000);
}
static uint32_t lookup(uint32_t view,uint32_t key) {
  esp=0x3f00000; PUSH32(esp,0); PUSH32(esp,MEM32(view+8)); PUSH32(esp,0); PUSH32(esp,key); PUSH32(esp,0);
  ecx=view; sub_000BE3D0(); assert(esp==0x3f00000); assert(LO8(eax));
  return MEM32(view+0x10)+MEM32(view+0x14)*MEM32(view+4)*4;
}
int main(int argc,char **argv) {
  FILE *f; long size; uint32_t table, group, member, count, row, sid, entry, string_offset, expected, handle;
  if(argc!=4) return 2;
  ram=(unsigned char*)calloc(64u*1024*1024,1); assert(ram);
  f=fopen(argv[1],"rb"); assert(f); assert(!fseek(f,0,SEEK_END)); size=ftell(f); assert(size>=24 && size<32*1024*1024);
  rewind(f); assert(fread(ram+0x10000,1,(size_t)size,f)==(size_t)size); fclose(f);
  esp=0x3f00000; ecx=0x1000; PUSH32(esp,0); PUSH32(esp,0); sub_000BE4E0();
  assert(esp==0x3f00000 && LO8(eax));
  assert(MEM32(0x1000)==0x10000);
  table=MEM32(lookup(0x1004,hash_name("Character")));
  count=MEM32(0x10000+table+12); expected=(uint32_t)strtoul(argv[2],NULL,10); assert(count==expected);
  parse_index(0x10000+table+4,0x3000,0);
  member=lookup(0x3000,hash_name("Character"));
  parse_index(member,0x4000,1);
  assert(MEM32(0x4008)==count);
  row=MEM32(lookup(0x4000,hash_name(argv[3])));
  sid=MEM32(0x10000+row); assert(sid<MEM32(0x1044));
  entry=MEM32(0x1048)+sid*8; assert(MEM32(entry)==hash_name(argv[3]));
  string_offset=MEM32(entry+4); assert(!strcmp((char*)address(0x10000+string_offset,1),argv[3]));
  esp=0x3f00000; PUSH32(esp,hash_name(argv[3])); PUSH32(esp,hash_name("Character")); PUSH32(esp,0x6000); PUSH32(esp,0);
  ecx=0x1000; sub_000BE870(); assert(esp==0x3f00000);
  handle=MEM32(0x6000); assert(handle!=0xffffffffu && MEM32(0x6004)==0x1000);
  esp=0x3f00000; PUSH32(esp,0); PUSH32(esp,handle); PUSH32(esp,0x6100); PUSH32(esp,0);
  ecx=0x1000; sub_000BE760(); assert(esp==0x3f00000 && MEM32(0x6100)==0x10000+row);
  printf("{\"ok\":true,\"character_count\":%u,\"probe_found\":true,\"selection_key\":%u,\"handle_roundtrip\":true,\"native_handle\":%u}\n",count,MEM32(0x10000+row+32),handle);
  free(ram); return 0;
}
'''


def extract(source, address):
    match = re.search(r'void sub_' + address + r'(?:_gen)?\(void\)\s*\{.*?^\}', source, re.S | re.M)
    if not match:
        raise ValueError('Missing generated parser function: ' + address)
    return match.group().replace('sub_' + address + '_gen(', 'sub_' + address + '(')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', required=True, type=Path)
    parser.add_argument('--sod', required=True, type=Path)
    parser.add_argument('--expect-count', required=True, type=int)
    parser.add_argument('--probe', required=True)
    args = parser.parse_args()
    compiler = shutil.which('cl.exe')
    if not compiler:
        parser.error('Run from scripts/env.ps1 so cl.exe is available')
    if not 1 <= args.expect_count <= 1_000_000 or not args.probe.isascii() or '\0' in args.probe:
        parser.error('Invalid count/probe')
    source_path = args.generated.resolve() / 'recomp_0005.c'
    original = source_path.read_bytes()
    source = original.decode('utf-8-sig')
    output = ROOT / 'logs/fighter-sod-oracle' / str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    source_out, executable = output / 'oracle.c', output / 'oracle.exe'
    prototypes = '\n'.join('void sub_' + va + '(void);' for va in FUNCTIONS)
    source_out.write_text(PREAMBLE + prototypes + '\n' + '\n'.join(extract(source, va) for va in FUNCTIONS)
                          + MAIN, encoding='utf-8')
    build = subprocess.run([compiler, '/nologo', '/TC', '/Od', str(source_out), '/Fe' + str(executable)],
                           cwd=output, capture_output=True, text=True)
    (output / 'build.txt').write_text(build.stdout + build.stderr, encoding='utf-8')
    if build.returncode:
        raise SystemExit('Oracle build failed; see ' + str(output / 'build.txt'))
    run = subprocess.run([str(executable), str(args.sod.resolve()), str(args.expect_count), args.probe],
                         cwd=output, capture_output=True, text=True, timeout=10)
    result = {'generated_sha256': hashlib.sha256(original).hexdigest(),
              'sod_sha256': hashlib.sha256(args.sod.read_bytes()).hexdigest(),
              'functions': list(FUNCTIONS), 'exit_code': run.returncode,
              'native_output': run.stdout.strip(), 'diagnostics': run.stderr[-4096:],
              'scope': 'CPU-only generated SODB loader/index oracle; not gameplay acceptance'}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if run.returncode:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
