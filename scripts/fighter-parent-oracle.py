"""Exercise original type15 parent scale/dispatch/cache code with invented data.

Run from scripts/env.ps1 with the game closed. Native bodies are extracted from
local generated code into ignored logs/fighter-parent-oracle only. Fake leaves
record arguments; only allocator/factory/free and leaf evaluation are stubs.
This proves parent mechanics, not full leaf graphs or runtime pack admission.
"""
from pathlib import Path
import importlib.util,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('oracle',ROOT/'scripts/fighter-sod-oracle.py')
o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
folder=ROOT/'logs/fighter-parent-oracle';folder.mkdir(exist_ok=True)
source=(ROOT/'src/recomp/gen/recomp_0007.c').read_text()
functions=('000EB7F0','000E5C80','000FD920','000FD960','000EE3F0','000EE2D0',
           '000EE320','000E5CD0','000EDEC0','000EE400','000EDF90','000EE190')
body='\n'.join(o.extract(source,a) for a in functions)
extra=r'''
#define MEM16(a) (*(uint16_t*)address((uint32_t)(a),2))
#define MEMF(a) (*(float*)address((uint32_t)(a),4))
#define ZX8(a) ((uint8_t)(a))
#define ZX16(a) ((uint16_t)(a))
#define LO16(a) ((uint16_t)(a))
#define SET_LO16(a,b) ((a)=((a)&0xffff0000u)|(uint16_t)(b))
#define g_esp esp
#define RECOMP_ICALL_SAFE_AT(a,b,c) dispatch(a)
#define RECOMP_ICALL_SAFE_AT_CC(a,b,c) dispatch(a)
typedef union {float f[4];} scalar_xmm;
static scalar_xmm xmm0,xmm1;
static scalar_xmm XMM_SCALAR(float f) {scalar_xmm v={{f,0,0,0}};return v;}
static void dispatch(uint32_t target);
'''
main=r'''
static unsigned allocated,freed,created,destroyed,evaluated,queried;
static uint32_t observed[16],query_record;
static float expected_time;
static uint32_t bits(float value) {uint32_t out;memcpy(&out,&value,4);return out;}
static void dispatch(uint32_t target) {
 if(target==0xEE3F0){sub_000EE3F0();return;}
 uint32_t arg=MEM32(esp+4);
 if(target==1){assert(ecx==0x3000&&arg<=16);allocated++;eax=0x6000;esp+=8;return;}
 if(target==2){assert(ecx==0x3000&&arg==0x6000);freed++;esp+=8;return;}
 if(target==3){
  assert(ecx==0x3000);eax=0x7000+32*created++;assert(created<=16);
  MEM32(eax)=0x3200;MEM32(eax+12)=arg;esp+=8;return;
 }
 if(target==4){assert(ecx==0x3000&&arg>=0x7000&&arg<0x7200);destroyed++;esp+=8;return;}
 if(target==5){
  assert(MEMF(esp+4)==expected_time&&MEM32(esp+8)==0x3456&&MEM32(esp+12)==0x4567);
  assert(evaluated<16);observed[evaluated++]=MEM32(ecx+12);eax=1;esp+=16;return;
 }
 if(target==6){
  assert(arg==0x5678&&MEMF(esp+8)==expected_time&&MEM32(esp+12)==0x8000);
  queried++;query_record=MEM32(ecx+12);MEMF(0x8000)=180.;eax=1;esp+=16;return;
 }
 assert(!"unexpected native indirect target");
}
static void call(void(*fn)(void),uint32_t obj,unsigned count,const uint32_t *args) {
 esp=0x3F00000;ecx=obj;
 for(unsigned i=count;i;i--)PUSH32(esp,args[i-1]);
 PUSH32(esp,0);fn();assert(esp==0x3F00000);
}
static void parent(uint32_t duration,uint32_t scale,unsigned count) {
 memset(ram,0,64u*1024*1024);
 allocated=freed=created=destroyed=evaluated=queried=0;
 MEM32(0x3A4FE4)=0x3000;MEM32(0x3000)=0x3100;
 MEM32(0x3114)=1;MEM32(0x3118)=2;MEM32(0x3124)=3;MEM32(0x312C)=4;
 MEM32(0x3218)=5;MEM32(0x3234)=6;MEM32(0x2B5850+0x3C)=0xEE3F0;
 MEM16(0x4000)=15;MEM32(0x4004)=0x2000;MEM16(0x4008)=(uint16_t)count;MEM16(0x400A)=(uint16_t)duration;
 MEM32(0x2000)=1;MEM16(0x2004)=1;MEM16(0x2006)=1;MEM32(0x2008)=scale;
 for(unsigned i=0;i<count;i++)MEM32(0x400C+4*i)=0x5000+16*i;
 call(sub_000E5C80,0x1000,0,NULL);assert(MEM32(0x1000)==0x2B5850&&!MEM32(0x1010)&&!MEM16(0x1014));
 uint32_t record=0x4000;call(sub_000EDEC0,0x1000,1,&record);
}
int main(void) {
 ram=calloc(1,64u*1024*1024);assert(ram);unsigned cases=0;
 const uint32_t scales[]={1,2,60,255},durations[]={0,93,65535};
 for(unsigned c=1;c<=2;c++)for(unsigned s=0;s<4;s++)for(unsigned d=0;d<3;d++)for(uint32_t enabled=0;enabled<2;enabled++){
  parent(durations[d],scales[s],c);
  call(sub_000EE2D0,0x1000,1,&enabled);assert(MEM8(0x1014)==enabled);
  call(sub_000EE320,0x1000,0,NULL);assert(LO8(eax)==scales[s]);
  uint32_t output=0x8000;call(sub_000E5CD0,0x1000,1,&output);
  float want=(float)durations[d];if(enabled)want/=(float)scales[s];assert(MEM32(output)==bits(want));
  uint32_t args[]={bits(1.5f),0x3456,0x4567};expected_time=enabled?1.5f*scales[s]:1.5f;
  call(sub_000EDF90,0x1000,3,args);assert(LO8(eax)&&allocated==1&&created==c&&evaluated==c);
  for(unsigned i=0;i<c;i++)assert(observed[i]==0x5000+16*(c-1-i));
  call(sub_000EDF90,0x1000,3,args);assert(allocated==1&&created==c&&evaluated==2*c);
  uint32_t query[]={0x5678,bits(1.5f),output};call(sub_000EE190,0x1000,3,query);
  want=enabled?180.f/scales[s]:180.f;assert(LO8(eax)&&queried==1&&query_record==0x5000+16*(c-1)&&MEM32(output)==bits(want));
  uint32_t off=0;call(sub_000EE2D0,0x1000,1,&off);expected_time=1.5f;
  call(sub_000EDF90,0x1000,3,args);assert(allocated==1&&created==c);
  /* Native reattach uses the NEW count for OLD cache destruction: same-count only. */
  memcpy(ram+0x4100,ram+0x4000,12+4*c);
  for(unsigned i=0;i<c;i++)MEM32(0x410C+4*i)=0x5100+16*i;
  uint32_t replacement=0x4100;call(sub_000EDEC0,0x1000,1,&replacement);
  assert(destroyed==c&&freed==1&&!MEM32(0x1010));evaluated=0;
  call(sub_000EDF90,0x1000,3,args);assert(allocated==2&&created==2*c&&evaluated==c);
  for(unsigned i=0;i<c;i++)assert(observed[i]==0x5100+16*(c-1-i));
  cases++;
 }
 printf("%u parent cases passed\n",cases);free(ram);return 0;
}
'''
prototypes='\n'.join('void sub_'+a+'(void);' for a in functions)
(folder/'oracle.c').write_text(o.PREAMBLE+extra+prototypes+body+main,encoding='utf-8')
subprocess.run(['cl.exe','/nologo','/O2','/fp:strict','/W3',str(folder/'oracle.c'),'/Fe:'+str(folder/'oracle.exe'),'/Fo:'+str(folder/'oracle.obj')],cwd=folder,check=True)
result=subprocess.run([str(folder/'oracle.exe')],capture_output=True,text=True,check=True)
report={'cases':48,'native_body_sha256':hashlib.sha256(body.encode()).hexdigest(),
        'functions':list(functions),'scope':'parent scale/duration, reverse child dispatch, retained cache, same-count reattachment; fake leaves and allocator; no full-graph admission',
        'output':result.stdout.strip()}
assert result.stdout.strip()=='48 parent cases passed'
(folder/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
