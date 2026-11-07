"""Compare original unfiltered type18 evaluation with the bounded offline reader.

Run in scripts/env.ps1, with the game closed. Original bodies are extracted only
into ignored logs. Invented inputs exercise full timing/scatter, static channels,
fresh and retained caches. Block-shift zero is the source paired-body profile;
other shifts are reported separately because backward delta replay can round
differently from fresh seed replay. This does not admit a runtime resource.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'setup'), str(ROOT / 'tests/unit')]
from test_fighter_animation_curves import curves
from fighter_animation_quaternions import QuaternionCurve

spec = importlib.util.spec_from_file_location('oracle', ROOT / 'scripts/fighter-sod-oracle.py')
o = importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
folder = ROOT / 'logs/fighter-quaternion18-full-oracle'
folder.mkdir(exist_ok=True)
source = (ROOT / 'src/recomp/gen/recomp_0007.c').read_text()
functions = ('000F6460', '000F6AE0', '000F6BA0', '000F49B0', '000F64C0', '000F6610', '000F5BD0')
body = '\n'.join(o.extract(source, a) for a in functions)
extra = r'''
#define MEM16(a) (*(uint16_t*)address((uint32_t)(a),2))
#define MEMF(a) (*(float*)address((uint32_t)(a),4))
#define LO16(a) ((uint16_t)(a))
#define HI8(a) ((uint8_t)((a)>>8))
#define SET_LO16(a,b) ((a)=((a)&0xffff0000u)|(uint16_t)(b))
#define ZX16(v) ((uint16_t)(v))
#define ZX8(v) ((uint8_t)(v))
#define TEST_NZ(a,b) (((a)&(b))!=0)
#define g_esp esp
static uint32_t g_mxcsr;
#define RECOMP_ICALL_SAFE_AT(target,before,site) do {assert((site)==0xF6C03 && MEM32(esp+4)<=4096);eax=0x200000;esp+=8;}while(0)
static uint32_t RECOMP_PARITY8(uint32_t x) {x^=x>>4;x^=x>>2;x^=x>>1;return !(x&1);}
static int32_t recomp_cvt_si32(double x,uint32_t mode,int truncating) {assert(truncating&&x>=0&&x<=65535);return (int32_t)x;}
static void sub_000F55D0(void) {assert(!"filtered route outside oracle scope");}
typedef union {float f[4];} scalar_xmm;
static scalar_xmm xmm0,xmm1,xmm2,xmm3,xmm4,xmm5,xmm6;
static scalar_xmm XMM_SCALAR(float f) {scalar_xmm v={{f,0,0,0}};return v;}
'''
main = r'''
static void initialize(void) {
 memset(ram+0x1000,0,64);memset(ram+0x200000,0,4096);
 MEM32(0x100C)=0x10000+56;MEM32(0x101C)=MEM32(0x1028)=0xFFFFFFFF;
 ecx=0x1000;esp=0x3f00000;PUSH32(esp,0);sub_000F6BA0();assert(esp==0x3f00000);
}
int main(int argc,char**argv) {
 assert(argc==3);ram=calloc(1,64u*1024*1024);assert(ram);
 FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
 MEM32(0x2B5E70)=0x3A000801;MEM32(0x2B5E6C)=0x38000080;
 MEM32(0x2B5E68)=0x3C820821;MEM32(0x289478)=0x3F800000;
 MEM32(0x3A4FE4)=0x3000;MEM32(0x3000)=0x4000;
 uint32_t cases;assert(fread(&cases,4,1,in)==1);
 for(uint32_t i=0;i<cases;i++) {
  uint32_t size,count,outsize,times[256];assert(fread(&size,4,1,in)==1&&size<=65536);
  assert(fread(ram+0x10000,size,1,in)==1);
  if(MEM32(0x10000+64))MEM32(0x10000+64)+=0x10000;
  if(MEM32(0x10000+68))MEM32(0x10000+68)+=0x10000;
  assert(fread(&count,4,1,in)==1&&count<=256);
  assert(fread(&outsize,4,1,in)==1&&outsize<=16384);
  assert(fread(times,4,count,in)==count);
  for(uint32_t retained=0;retained<2;retained++) {
   initialize();
   for(uint32_t j=0;j<count;j++) {
    if(!retained)initialize();
    memset(ram+0x21FFF0,0xA5,outsize+32);
    ecx=0x1000;esp=0x3f00000;
    PUSH32(esp,0);PUSH32(esp,0x220000);PUSH32(esp,times[j]);PUSH32(esp,0);
    sub_000F5BD0();assert(esp==0x3f00000);
    for(uint32_t k=0;k<16;k++)assert(ram[0x21FFF0+k]==0xA5&&ram[0x220000+outsize+k]==0xA5);
    assert(fwrite(ram+0x220000,outsize,1,out)==1);
   }
  }
 }
 assert(fgetc(in)==EOF&&!ferror(in));fclose(in);fclose(out);free(ram);return 0;
}
'''
(folder / 'oracle.c').write_text(o.PREAMBLE + extra + body + main, encoding='utf-8')
subprocess.run(['cl.exe', '/nologo', '/O2', '/fp:strict', '/W3', str(folder / 'oracle.c'),
                '/Fe:' + str(folder / 'oracle.exe'), '/Fo:' + str(folder / 'oracle.obj')], cwd=folder, check=True)
rng = random.Random(181800)
cases = []
for channels in (0, 1, 2, 7, 40):
 for shift in (0, 1, 3):
  for keys in (1, 2, 3, 9, 17):
   for timed in (False, True):
    if timed and keys == 1:
     continue
    for constants in (0, 2):
     if not channels and not constants:
      continue
     def authored(data, pointers, record):
      data.extend(bytes(32768 - len(data)))
      data[32760:32768] = data[240:248]
      struct.pack_into('<2I', data, 32, 32760, 32764)
      data[56:32760] = bytes(32760 - 56)
      struct.pack_into('<HHHBBII', data, record, 18, 0, keys, channels, constants, 31000 if timed else 0, 32000)
      data[record + 16] = shift
      if not timed:
       pointers.remove(record + 8)
      else:
       struct.pack_into('<' + 'H' * (keys - 1), data, 31000, *range(2, 2 * keys, 2))
      data[32000:32000 + channels] = bytes(2 * c for c in range(channels))
      descriptor = [rng.randrange(65536) for _ in range(channels * 8)]
      struct.pack_into('<' + 'H' * len(descriptor), data, record + 18, *descriptor)
      width = 1 << shift
      size = (keys // width) * ((3 * channels * (width + 1) + 1) & ~1)
      if keys % width:
       size += 3 * channels * (keys % width + 1)
      start = record + 18 + 16 * channels
      data[start:start + size] = bytes(rng.randrange(256) for _ in range(size))
      end = start + size
      data[end:end + constants] = bytes(2 * (channels + c) + 1 for c in range(constants))
      static = (end + constants + 1) & ~1
      data[static:static + 6 * constants] = bytes(rng.randrange(256) for _ in range(6 * constants))
     layout = curves(18, authored)
     decoder = QuaternionCurve(layout, 56)
     section = layout.model.sections[1]
     raw = layout.model.data[section[4]:section[4] + section[5]]
     asc = sorted(set([0., .25, .5, 1., 65535.] + [float(k) + f for k in range(keys * 2) for f in (0, .25)]))
     times = asc + list(reversed(asc)) + [.25, 7.25, 8.25, 15.25, 3.25, 15.25, 0.]
     size = max(decoder.destinations) * 48 + 32
     expected = bytearray()
     for time in times:
      output = bytearray([0xA5] * size)
      for dest, values in zip(decoder.destinations, decoder.sample(time)):
       struct.pack_into('<4f', output, dest * 48 + 16, *values)
      expected.extend(output)
     cases.append((raw, times, size, bytes(expected), shift))
input_path = folder / 'input.bin'
input_path.write_bytes(struct.pack('<I', len(cases)) + b''.join(
    struct.pack('<I', len(raw)) + raw + struct.pack('<II', len(times), size) + struct.pack('<' + 'f' * len(times), *times)
    for raw, times, size, _, _ in cases))
output_path = folder / 'output.bin'
subprocess.run([str(folder / 'oracle.exe'), str(input_path), str(output_path)], check=True)
actual = output_path.read_bytes()
offset = 0
stats = {str(shift): {'cases': 0, 'samples_per_mode': 0, 'compared_bytes_per_mode': 0,
                     'fresh_mismatched_bytes': 0, 'retained_mismatched_bytes': 0} for shift in (0, 1, 3)}
first = []
for index, (_, times, size, expected, shift) in enumerate(cases):
 row = stats[str(shift)]
 row['cases'] += 1
 row['samples_per_mode'] += len(times)
 row['compared_bytes_per_mode'] += len(expected)
 for mode in ('fresh', 'retained'):
  result = actual[offset:offset + len(expected)]
  mismatch = sum(a != b for a, b in zip(result, expected)) + abs(len(result) - len(expected))
  row[mode + '_mismatched_bytes'] += mismatch
  if mismatch and len(first) < 8:
   at = next(i for i, (a, b) in enumerate(zip(result, expected)) if a != b)
   first.append({'case': index, 'mode': mode, 'shift': shift, 'time': times[at // size], 'byte': at % size})
  offset += len(expected)
report = {'native_body_sha256': hashlib.sha256(body.encode()).hexdigest(), 'block_shifts': stats,
          'first_mismatches': first, 'scope': 'Full unfiltered F5BD0, fresh/retained caches, forward/backward/random seeks, dynamic/static scatter and output guards; no filtered evaluation or runtime admission'}
(folder / 'comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
assert offset == len(actual)
assert all(not row['fresh_mismatched_bytes'] for row in stats.values())
assert all(not row['retained_mismatched_bytes'] for row in stats.values())
