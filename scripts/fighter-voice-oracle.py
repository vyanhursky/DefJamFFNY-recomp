#!/usr/bin/env python3
"""Compare authored PCM voice streams with the owner's native parser/decoder.

Run in scripts/env.ps1's MSVC environment. Generated C, samples and binaries
stay in ignored logs/. No audio device/game/save interaction. This exercises
header parsing, packet pointer setup and PCM conversion, not streaming/mixing,
voice-event selection, resource registration or playback lifetime.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_voice import encode_stream

spec = importlib.util.spec_from_file_location('sod_oracle', ROOT / 'scripts/fighter-sod-oracle.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)

FUNCTIONS = ('0012C6E0', '00129E60', '00129F00', '00126970', '001264F0',
             '00130EA0', '0012E520', '0012E490', '0011F300')
EXTRA = r'''
#define MEM16(a) (*(uint16_t*)address((uint32_t)(a),2))
#define SMEM16(a) (*(int16_t*)address((uint32_t)(a),2))
#define MEMF(a) (*(float*)address((uint32_t)(a),4))
#define MEMD(a) (*(double*)address((uint32_t)(a),8))
#define LO16(a) ((uint16_t)(a))
#define HI8(a) ((uint8_t)((a)>>8))
#define SET_LO16(a,b) ((a)=((a)&0xffff0000u)|(uint16_t)(b))
#define ZX16(v) ((uint16_t)(v))
#define ZX8(v) ((uint8_t)(v))
#define TEST_NZ(a,b) (((a)&(b))!=0)
#define XBOX_PTR(a) address((uint32_t)(a),1)
#define RECOMP_DF_STEP(n) (g_df?-(n):(n))
static int g_df;
static double g_fp_stack[8];
static uint32_t g_fp_top;
static uint32_t packet_count,packet_pointer;
static void sub_00122DD0(void) {assert(!"unexpected allocating property");}
static void sub_00129F60(void) {assert(!"unexpected GSTR profile");}
static void sub_001E8340(void) {assert(!"unexpected empty packet");}
static void sub_00125FA0(void) {
 uint32_t info=MEM32(esp+8);
 packet_count=MEM32(info+4)&0x7fffffffu;
 packet_pointer=MEM32(info+0xC);
 esp+=4;
}
'''
MAIN = r'''
int main(int argc,char **argv) {
 assert(argc==3);ram=calloc(1,64u*1024*1024);assert(ram);
 FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
 uint32_t cases;assert(fread(&cases,4,1,in)==1);
 for(uint32_t i=0;i<cases;i++) {
  uint32_t size;assert(fread(&size,4,1,in)==1);assert(size<1024*1024);
  assert(fread(ram+0x10000,size,1,in)==1);
  memset(ram+0x1000,0xA5,0x400);
  esp=0x3f00000;
  PUSH32(esp,0x1300);PUSH32(esp,0x1200);PUSH32(esp,0x1100);
  PUSH32(esp,0x1000);PUSH32(esp,0x10008);PUSH32(esp,0);PUSH32(esp,0);
  sub_001264F0();assert(esp==0x3f00000-24);
  assert(MEM8(0x1300)==0&&MEM8(0x1002)==1&&MEM8(0x1003)==8);
  assert(MEM8(0x1004)==0xA5&&MEM8(0x1168)==0xA5&&MEM8(0x121C)==0xA5);
  assert(fwrite(ram+0x1000,4,1,out)==1);assert(fwrite(ram+0x1200,4,1,out)==1);
  uint32_t samples=0;
  for(uint32_t at=0;at<size;at+=MEM32(0x10000+at+4)) {
   uint32_t p=0x10000+at;
   if(MEM32(p)!=0x6c444353) continue;
   uint32_t n=MEM32(p+8);assert(n&&n<=16384);
   memset(ram+0x2000,0,0x800);MEM32(0x2134)=0x2200;MEM8(0x2016)=1;
   esp=0x3f00000;PUSH32(esp,p);PUSH32(esp,0x2000);PUSH32(esp,0);
   sub_0011F300();assert(esp==0x3f00000-8);
   assert(packet_count==n&&packet_pointer==p+16);
   MEM32(0x2400)=packet_pointer;MEM32(0x240C)=n;MEM32(0x2418)=1;
   esp=0x3f00000;PUSH32(esp,0x2400);PUSH32(esp,0x2500);PUSH32(esp,0);
   sub_0012E520();assert(esp==0x3f00000-8&&MEM32(0x2500)==0x12e490);
   uint32_t stride=(i%5==0)?1:(i%5==1)?7:(i%5==2)?64:(i%5==3)?511:16384;
   for(uint32_t pos=0;pos<n;pos+=stride) {
    memset(ram+0x100000-16,0xA5,stride*4+32);
    esp=0x3f00000;PUSH32(esp,0x100000);PUSH32(esp,0);
    PUSH32(esp,stride);PUSH32(esp,0x2500);PUSH32(esp,0);
    sub_0012E490();assert(esp==0x3f00000-16);
    uint32_t available=(stride<n-pos)?stride:n-pos;
    for(uint32_t j=0;j<16;j++)
     assert(ram[0x100000-16+j]==0xA5&&ram[0x100000+stride*4+j]==0xA5);
    for(uint32_t j=available;j<stride;j++) assert(MEMF(0x100000+j*4)==0);
    assert(fwrite(ram+0x100000,4,available,out)==available);
   }
   esp=0x3f00000;PUSH32(esp,0x100000);PUSH32(esp,0);
   PUSH32(esp,1);PUSH32(esp,0x2500);PUSH32(esp,0);
   sub_0012E490();assert(eax==0xFFFFFFFFu&&esp==0x3f00000-16);
   samples+=n;
  }
  assert(samples==MEM32(0x1200));
 }
 assert(fgetc(in)==EOF&&!ferror(in));fclose(in);fclose(out);free(ram);return 0;
}
'''


def main():
    folder = ROOT / 'logs/fighter-voice-oracle'
    folder.mkdir(exist_ok=True)
    sources = {name: (ROOT / 'src/recomp/gen' / name).read_text()
               for name in ('recomp_0008.c', 'recomp_0009.c')}
    body = '\n'.join(oracle.extract(sources['recomp_0008.c' if address == '0011F300'
                                           else 'recomp_0009.c'], address)
                     for address in FUNCTIONS)
    (folder / 'oracle.c').write_text(oracle.PREAMBLE + EXTRA + body + MAIN, encoding='utf-8')
    subprocess.run(['cl.exe', '/nologo', '/O2', '/fp:strict', '/W3',
                    str(folder / 'oracle.c'), '/Fe:' + str(folder / 'oracle.exe'),
                    '/Fo:' + str(folder / 'oracle.obj')], cwd=folder, check=True)
    rng = random.Random(11616)
    cases, expected, samples = [], bytearray(), 0
    for rate in (8000, 11025, 24000, 32768, 48000):
        for count in (1, 7, 8, 9, 127, 128, 4097, 16385):
            for packet_samples in (7, 4096, 16384):
                values = [rng.randrange(-32768, 32768) for _ in range(count)]
                values[0] = -32768
                if count > 1:
                    values[-1] = 32767
                cases.append(encode_stream(struct.pack('<' + 'h' * count, *values),
                                           rate, packet_samples))
                expected.extend(struct.pack('<HBBI', rate, 1, 8, count))
                expected.extend(struct.pack('<' + 'f' * count, *values))
                samples += count
    input_path, output_path = folder / 'input.bin', folder / 'output.bin'
    input_path.write_bytes(struct.pack('<I', len(cases)) + b''.join(
        struct.pack('<I', len(case)) + case for case in cases))
    subprocess.run([str(folder / 'oracle.exe'), str(input_path), str(output_path)], check=True)
    actual = output_path.read_bytes()
    report = {'cases': len(cases), 'samples': samples,
              'mismatched_bytes': sum(a != b for a, b in zip(actual, expected))
                                  + abs(len(actual) - len(expected)),
              'native_body_sha256': hashlib.sha256(body.encode()).hexdigest(),
              'functions': list(FUNCTIONS), 'runtime_ready': False,
              'scope': 'native header parsing, mono packet pointers, PCM decoder initialization, '
                       'partial reads, tail zero-fill and exhaustion; no mixer or resource lifetime'}
    (folder / 'comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    assert actual == expected


if __name__ == '__main__':
    main()
