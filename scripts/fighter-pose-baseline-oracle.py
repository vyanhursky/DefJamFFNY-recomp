"""Exercise original skeletal pose reset with invented source records.

Run from scripts/env.ps1 with the game closed. Local generated code is extracted
only into ignored logs. This checks 22BF0/E9010, including auxiliary weights and
repeated resets; it does not execute the later component blends or a full match.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('oracle', ROOT / 'scripts/fighter-sod-oracle.py')
o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
folder = ROOT / 'logs/fighter-pose-baseline-oracle'; folder.mkdir(exist_ok=True)
body = o.extract((ROOT / 'src/recomp/gen/recomp_0007.c').read_text(), '000E9010')
body += '\n' + o.extract((ROOT / 'src/recomp/gen/recomp_0000.c').read_text(), '00022BF0')
extra = r'''
#define MEMF(a) (*(float*)address((uint32_t)(a),4))
typedef union {float f[4];} scalar_xmm;
static scalar_xmm xmm0;
static scalar_xmm XMM_SCALAR(float f) {scalar_xmm v={{f,0,0,0}};return v;}
'''
main = r'''
int main(void) {
 ram=calloc(1,64u*1024*1024);assert(ram);MEMF(0x289478)=1.;unsigned cases=0;
 const unsigned counts[]={1,2,40,94,256};
 for(unsigned n=0;n<5;n++)for(unsigned weights=0;weights<2;weights++)for(unsigned pass=0;pass<3;pass++){
  unsigned count=counts[n];MEM32(0x1004)=0x10000;MEM32(0x100C)=0x20000;
  MEM32(0x10008)=count;MEM32(0x1000C)=weights?0x30000:0;
  for(unsigned b=0;b<count;b++){
   uint32_t row=0x10010+112*b;
   for(unsigned f=0;f<28;f++)MEMF(row+4*f)=(float)(b*100+f+pass*10000);
   MEMF(0x30000+4*b)=(float)b*.25f;
  }
  memset(ram+0x1FFF0,0xA5,count*48+32);
  ecx=0x1000;esp=0x3F00000;PUSH32(esp,0);sub_00022BF0();assert(esp==0x3F00000);
  for(unsigned b=0;b<count;b++){
   uint32_t row=0x10010+112*b,out=0x20000+48*b;
   for(unsigned f=0;f<3;f++)assert(MEM32(out+4*f)==MEM32(row+4*f));
   assert(MEMF(out+12)==(weights?(float)b*.25f:1.f));
   for(unsigned f=4;f<11;f++)assert(MEM32(out+4*f)==MEM32(row+4*f));
   assert(MEMF(out+44)==1.f);
  }
  for(unsigned i=0;i<16;i++)assert(MEM8(0x1FFF0+i)==0xA5&&MEM8(0x20000+count*48+i)==0xA5);
  cases++;
 }
 printf("%u skeletal reset cases passed\n",cases);free(ram);return 0;
}
'''
(folder / 'oracle.c').write_text(o.PREAMBLE + extra + body + main, encoding='utf-8')
subprocess.run(['cl.exe', '/nologo', '/O2', '/fp:strict', '/W3', str(folder / 'oracle.c'),
                '/Fe:' + str(folder / 'oracle.exe'), '/Fo:' + str(folder / 'oracle.obj')], cwd=folder, check=True)
result = subprocess.run([str(folder / 'oracle.exe')], capture_output=True, text=True, check=True)
assert result.stdout.strip() == '30 skeletal reset cases passed'
report = {'cases': 30, 'native_body_sha256': hashlib.sha256(body.encode()).hexdigest(),
          'output': result.stdout.strip(), 'scope': 'Full unmasked source-skeleton translation/quaternion/scale reset, default/auxiliary weights, repeated changed-source copies and output guards; no later component blending or native match'}
(folder / 'comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
