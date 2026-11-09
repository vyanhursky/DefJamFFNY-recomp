"""Compare original type20/21 evaluators with fresh and retained offline samples.

Run inside scripts/env.ps1 with the game closed. Original generated bodies and
invented fixtures stay in ignored logs. No filtered route or runtime admission
is implied. Use --kind 20 or --kind 21.
"""
from pathlib import Path
import argparse, importlib.util, struct, subprocess, sys, json, hashlib, random
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--kind",type=int,choices=(20,21),default=20)
kind=parser.parse_args().kind;dimension=3 if kind==20 else 1
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'setup'),str(ROOT/'tests/unit')]
from test_fighter_animation_vectors import vector_fixture
from fighter_animation_vectors import VectorCurve
spec=importlib.util.spec_from_file_location('oracle',ROOT/'scripts/fighter-sod-oracle.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
folder=ROOT/f'logs/fighter-vector{kind}-cache-oracle';folder.mkdir(exist_ok=True)
source=(ROOT/'src/recomp/gen/recomp_0007.c').read_text()
body='\n'.join(o.extract(source,a) for a in (('000F1250','000F14F0') if kind==20 else ('000EFBD0','000EFD80')))
extra=r'''
#include <math.h>
#define MEM16(a) (*(uint16_t*)address((uint32_t)(a),2))
#define MEMF(a) (*(float*)address((uint32_t)(a),4))
#define LO16(a) ((uint16_t)(a))
#define HI8(a) ((uint8_t)((a)>>8))
#define SET_LO16(a,b) ((a)=((a)&0xffff0000u)|(uint16_t)(b))
#define ZX16(v) ((uint16_t)(v))
#define ZX8(v) ((uint8_t)(v))
#define g_esp esp
static uint32_t allocation,g_mxcsr;
#define RECOMP_ICALL_SAFE_AT(target,before,site) do {assert((site)==0xF1274||(site)==0xF1290||(site)==0xF12AF);eax=allocation;allocation+=0x1000;esp+=8;}while(0)
static uint32_t RECOMP_PARITY8(uint32_t x) {x^=x>>4;x^=x>>2;x^=x>>1;return !(x&1);}
static int32_t recomp_cvt_si32(double x,uint32_t mode,int truncating) {assert(truncating&&x>=0&&x<=65535);return (int32_t)x;}
static void sub_000F0700(void) {assert(!"filtered route outside oracle scope");}
typedef union {float f[4];} scalar_xmm;
static scalar_xmm xmm0,xmm1,xmm2,xmm3,xmm4,xmm5;
static scalar_xmm XMM_SCALAR(float f) {scalar_xmm v={{f,0,0,0}};return v;}
'''
main=r'''
int main(int argc,char**argv) {
 assert(argc==3);ram=calloc(1,64u*1024*1024);assert(ram);
 FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
 MEM32(0x2B5D40)=0x37800080;MEM32(0x2B5D38)=0x3B808081;MEM32(0x2B5D1C)=0x38000080;
 MEM32(0x289478)=0x3F800000;MEM32(0x28947C)=0;
 MEM32(0x3A4FE4)=0x3000;MEM32(0x3000)=0x4000;
 uint32_t cases;assert(fread(&cases,4,1,in)==1);
 for(uint32_t i=0;i<cases;i++) {
  uint32_t size,count,outsize;assert(fread(&size,4,1,in)==1);assert(size<=4096);
  assert(fread(ram+0x10000,size,1,in)==1);
  MEM32(0x10000+56+4)+=0x10000;
  if(MEM32(0x10000+56+8))MEM32(0x10000+56+8)+=0x10000;
  assert(fread(&count,4,1,in)==1);assert(fread(&outsize,4,1,in)==1);assert(outsize<4096);
  uint32_t times[256];assert(count<=256&&fread(times,4,count,in)==count);
  for(uint32_t retained=0;retained<2;retained++) for(uint32_t j=0;j<count;j++) {
   uint32_t time=times[j];
   if(!retained||!j){
    memset(ram+0x1000,0,64);MEM32(0x100C)=0x10000+56;
    MEM32(0x1010)=MEM32(0x101C)=0xFFFFFFFF;allocation=0x200000;
    memset(ram+allocation,0,0x3000);
   }
   memset(ram+0x21FFF0,0xA5,outsize+32);
   ecx=0x1000;esp=0x3f00000;
   PUSH32(esp,0);PUSH32(esp,0x220000);PUSH32(esp,time);PUSH32(esp,0);
   sub_000F14F0();assert(esp==0x3f00000);
   for(uint32_t k=0;k<16;k++)assert(ram[0x21FFF0+k]==0xA5&&ram[0x220000+outsize+k]==0xA5);
   assert(fwrite(ram+0x220000,outsize,1,out)==1);
  }
 }
 assert(fgetc(in)==EOF&&!ferror(in));fclose(in);fclose(out);free(ram);return 0;
}
'''
if kind==21:
 for before,after in [('F1274','EFBF4'),('F1290','EFC10'),('F12AF','EFC2C'),('F0700','EF370'),('F14F0','EFD80'),('2B5D40','2B5CB8'),('2B5D38','2B5CB0')]:
  extra=extra.replace(before,after);main=main.replace(before,after)
(folder/'oracle.c').write_text(o.PREAMBLE+extra+body+main,encoding='utf-8')
subprocess.run(['cl.exe','/nologo','/O2','/fp:strict','/W3',str(folder/'oracle.c'),'/Fe:'+str(folder/'oracle.exe'),'/Fo:'+str(folder/'oracle.obj')],cwd=folder,check=True)
rng=random.Random(2020);cases=[];sample_count=0
for channels in (0,1,2,4,7):
 for shift in (0,1,3):
  for keys in (1,2,3,5,9):
   for timed in (False,True):
    if timed and keys==1:continue
    for variant in range(3):
     def change(data,record,start):
      if not variant:return
      for c in range(channels):
       struct.pack_into('<'+str(dimension*2)+'f'+str(dimension*2)+'H',data,record+20+c*dimension*12,
                        *(rng.uniform(-100,100) for _ in range(dimension*2)),*(rng.randrange(65536) for _ in range(dimension*2)))
      width=1<<shift;size=(keys//width)*((dimension*channels*(width+1)+1)&~1)
      if keys%width:size=(size+dimension*channels*(keys%width+1)+1)&~1
      data[start:start+size]=bytes(rng.randrange(256) for _ in range(size))
     layout=vector_fixture(channels=channels,keys=keys,shift=shift,timed=timed,change=change,kind=kind)
     decoder=VectorCurve(layout,56);section=layout.model.sections[1]
     raw=layout.model.data[section[4]:section[4]+section[5]]
     times=sorted(set([0.,.25,.5,1.,65535.]+[float(i)+f for i in range(keys*2) for f in (0,.25,.5)]))
     times=times+list(reversed(times))+[.25,7.25,8.25,15.25,3.25,15.25,0.]
     outsize=(max(decoder.destinations)+dimension)*4;expected=bytearray()
     for time in times:
      output=bytearray([0xA5]*outsize)
      for dest,values in zip(decoder.destinations,decoder.sample(time)):struct.pack_into('<'+'f'*dimension,output,dest*4,*values)
      expected.extend(output)
     cases.append((raw,times,outsize,bytes(expected)*2));sample_count+=len(times)
input=folder/'input.bin';input.write_bytes(struct.pack('<I',len(cases))+b''.join(struct.pack('<I',len(raw))+raw+struct.pack('<II',len(times),size)+struct.pack('<'+'f'*len(times),*times) for raw,times,size,_ in cases))
output=folder/'output.bin';subprocess.run([str(folder/'oracle.exe'),str(input),str(output)],check=True)
actual=output.read_bytes();expected=b''.join(x[3] for x in cases)
report={'cases':len(cases),'samples':sample_count*2,'compared_bytes':len(expected),'mismatched_bytes':sum(a!=b for a,b in zip(actual,expected))+abs(len(actual)-len(expected)),'native_body_sha256':hashlib.sha256(body.encode()).hexdigest(),'scope':'Full unfiltered fresh/retained-cache time lookup, seed/forward replay, interpolation, static scatter; ascending/descending/cross-block seeks; no filtered or runtime admission'}
(folder/'comparison.json').write_text(json.dumps(report,indent=2));print(report)
if actual!=expected:
 offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b);start=0
 for case,(raw,times,size,exp) in enumerate(cases):
  if start<=offset<start+len(exp):print('first mismatch case',case,'time',times[((offset-start)//size)%len(times)],'byte',(offset-start)%size,'actual',actual[offset:offset+8].hex(),'expected',expected[offset:offset+8].hex());break
  start+=len(exp)
assert actual==expected
