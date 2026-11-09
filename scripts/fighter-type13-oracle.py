"""Compare the type13 reader against locally generated original evaluator bodies.

Windows: load scripts/env.ps1, then run this script from the repository root.
Requires the user's generated recomp_0007.c and the unit fixtures. It writes
only ignored logs/fighter-type13-oracle output; no native bodies are tracked.
"""
from pathlib import Path
import importlib.util,struct,subprocess,sys,json,hashlib,random
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'setup'),str(ROOT/'tests/unit')]
from test_fighter_animation_timed_quaternions import timed_fixture
from fighter_animation_timed_quaternions import TimedQuaternionCurve
spec=importlib.util.spec_from_file_location('oracle',ROOT/'scripts/fighter-sod-oracle.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
folder=ROOT/'logs/fighter-type13-oracle';folder.mkdir(exist_ok=True)
source=(ROOT/'src/recomp/gen/recomp_0007.c').read_text()
functions=('000FC3F0','000EC8C0','000EA010','000ED300');body='\n'.join(o.extract(source,a) for a in functions)
extra=r'''
#include <math.h>
#define MEM16(a) (*(uint16_t*)address((uint32_t)(a),2))
#define MEMF(a) (*(float*)address((uint32_t)(a),4))
#define LO16(a) ((uint16_t)(a))
#define HI8(a) ((uint8_t)((a)>>8))
#define SET_LO16(a,b) ((a)=((a)&0xffff0000u)|(uint16_t)(b))
#define ZX16(v) ((uint16_t)(v))
#define ZX8(v) ((uint8_t)(v))
#define TEST_NZ(a,b) (((a)&(b))!=0)
#define XBOX_PTR(a) address((uint32_t)(a),1)
#define RECOMP_DF_STEP(n) (g_df?-(n):(n))
static uint32_t g_mxcsr,g_df,g_fp_top,g_fp_control_word;
static double g_fp_stack[8];
static double round24(double x) {int e;if(!x)return x;x=frexp(x,&e);return ldexp((double)(float)x,e);}
#define RECOMP_FP_PC(x) ((g_fp_control_word&0x300)?(double)(x):round24(x))
static uint32_t RECOMP_PARITY8(uint32_t x) {x^=x>>4;x^=x>>2;x^=x>>1;return !(x&1);}
static int32_t recomp_cvt_si32(double x,uint32_t mode,int truncating) {assert(truncating&&x>=0&&x<=65535);return (int32_t)x;}
static void sub_000ECBD0(void) {assert(!"filtered route outside oracle scope");}
typedef union {float f[4];} scalar_xmm;
static scalar_xmm xmm0,xmm1,xmm2,xmm3,xmm4,xmm5;
static scalar_xmm XMM_SCALAR(float f) {scalar_xmm v={{f,0,0,0}};return v;}
#define XMM_ZERO() XMM_SCALAR(0)
'''
main=r'''
int main(int argc,char**argv) {
 assert(argc==3);ram=calloc(1,64u*1024*1024);assert(ram);
 FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
 MEM32(0x289478)=0x3F800000;MEM32(0x28947C)=0;
 uint32_t cases;assert(fread(&cases,4,1,in)==1);
 for(uint32_t i=0;i<cases;i++) {
  uint32_t size,count,outsize;assert(fread(&size,4,1,in)==1);assert(size<=4096);
  assert(fread(ram+0x10000,size,1,in)==1);
  MEM32(0x10000+60)+=0x10000;MEM32(0x10000+64)+=0x10000;
  assert(fread(&count,4,1,in)==1);assert(fread(&outsize,4,1,in)==1&&outsize<=1024);
  uint32_t times[64];assert(count<=64&&fread(times,4,count,in)==count);
  for(uint32_t precision=0;precision<2;precision++) for(uint32_t j=0;j<count;j++) {
   memset(ram+0x1000,0,64);MEM32(0x100C)=0x10000+56;
   MEM32(0x1010)=0xFFFFFFFF;MEM32(0x1014)=0x200000;
   memset(ram+0x21FFF0,0xA5,outsize+32);memset(ram+0x200000,0,1024);
   ecx=0x1000;esp=0x3f00000;g_fp_control_word=precision?0x27F:0x7F;g_fp_top=0;
   PUSH32(esp,0);PUSH32(esp,0x220000);PUSH32(esp,times[j]);PUSH32(esp,0);
   sub_000ED300();assert(esp==0x3f00000&&g_fp_top==0);
   for(uint32_t k=0;k<16;k++)assert(ram[0x21FFF0+k]==0xA5&&ram[0x220000+outsize+k]==0xA5);
   assert(fwrite(ram+0x220000,outsize,1,out)==1);
  }
 }
 assert(fgetc(in)==EOF&&!ferror(in));fclose(in);fclose(out);free(ram);return 0;
}
'''
(folder/'oracle.c').write_text(o.PREAMBLE+extra+body+main,encoding='utf-8')
subprocess.run(['cl.exe','/nologo','/O2','/fp:strict','/W3',str(folder/'oracle.c'),'/Fe:'+str(folder/'oracle.exe'),'/Fo:'+str(folder/'oracle.obj')],cwd=folder,check=True)
rng=random.Random(1313);cases=[];times=[0,.001,.25,.5,1,1.999,2,2.001,2.25,3,4.999,5,5.25,65535]
for groups in (1,2,4,7):
 for bits in ((4,8,16) if groups==1 else (8,16)):
  for variant in range(80):
   def change(data,groups,bits):
    scalars=groups*4
    struct.pack_into('<'+'f'*(scalars*3),data,304,*[x for i in range(scalars) for x in (rng.uniform(-.1,.1),rng.uniform(-.0001,.0001),rng.uniform(-2,2))])
    packed=304+scalars*12;size=groups*bits
    data[packed:packed+size]=bytes(rng.randrange(256) for _ in range(size))
   layout=timed_fixture(groups,bits,change);decoder=TimedQuaternionCurve(layout,56);section=layout.model.sections[1]
   raw=layout.model.data[section[4]:section[4]+section[5]]
   size=(max(decoder.destinations)+4)*4;expected=bytearray()
   for precision in (24,53):
    for time in times:
     output=bytearray([0xA5]*size)
     for dest,values in zip(decoder.destinations,decoder.sample(time,precision_bits=precision)):struct.pack_into('<4f',output,dest*4,*values)
     expected.extend(output)
   cases.append((raw,size,bytes(expected)))
input=folder/'input.bin';input.write_bytes(struct.pack('<I',len(cases))+b''.join(struct.pack('<I',len(raw))+raw+struct.pack('<II',len(times),size)+struct.pack('<'+'f'*len(times),*times) for raw,size,_ in cases))
output=folder/'output.bin';subprocess.run([str(folder/'oracle.exe'),str(input),str(output)],check=True)
actual=output.read_bytes();expected=b''.join(v for _,_,v in cases)
report={'cases':len(cases),'sample_evaluations':len(cases)*len(times)*2,'compared_bytes':len(expected),'mismatched_bytes':sum(a!=b for a,b in zip(actual,expected))+abs(len(actual)-len(expected)),'native_body_sha256':hashlib.sha256(body.encode()).hexdigest(),'scope':'Full unfiltered ED300 fresh-cache evaluation; 1/2/4/7 quaternion groups; 8/16-bit, 4-bit single-group only, 24/53-bit x87 precision, exact endpoints and interpolation, output guards'}
(folder/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(report)
assert actual==expected
