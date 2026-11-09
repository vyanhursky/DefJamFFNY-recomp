"""Check original voice lookup/alternative bodies with invented cache data.

Run from scripts/env.ps1 with the game closed. Six unchanged generated bodies
execute in a CPU-only harness beneath ignored logs. Event eligibility, random,
sample selection and device playback are counted stand-ins. This proves bank
omission semantics, not an in-game audio or whole-pack acceptance test.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('oracle', ROOT / 'scripts/fighter-sod-oracle.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
FUNCTIONS = ('00135C50', '00135CB0', '00135D40', '00137780', '00138070', '00138CA0')
EXTRA = r'''
#define MEM16(a) (*(uint16_t*)address((uint32_t)(a),2))
#define SMEM16(a) (*(int16_t*)address((uint32_t)(a),2))
#define ZX8(a) ((uint8_t)(a))
#define ZX16(a) ((uint16_t)(a))
#define SX16(a) ((uint32_t)(int32_t)(int16_t)(a))
#define LO16(a) ((uint16_t)(a))
#define SET_LO16(a,b) ((a)=((a)&0xffff0000u)|(uint16_t)(b))
#define TEST_NZ(a,b) (((a)&(b))!=0)
static unsigned attempts,samples,played,cases;
static void sub_00137E30(void) {esp+=4;}
static void sub_00137E80(void) {attempts++;eax=1;esp+=4;}
static void sub_00137A30(void) {
 uint32_t out=MEM32(esp+12);assert(MEM32(out)>=100&&MEM32(out)<=102);
 samples++;eax=1;esp+=4;
}
static void sub_00136870(void) {eax=0x4000;esp+=4;}
static void sub_001368D0(void) {MEM32(MEM32(esp+8))=0;eax=1;esp+=4;}
static void sub_001395E0(void) {eax=0;esp+=4;}
static void sub_00137CD0(void) {uint32_t out=MEM32(esp+8);MEM8(out)=0;MEM8(out+1)=1;MEM8(out+2)=2;esp+=4;}
static void sub_00139110(void) {eax=0;esp+=4;}
static void sub_00138BD0(void) {eax=1;esp+=4;}
static void sub_001397B0(void) {eax=1;esp+=4;}
static void sub_00138410(void) {eax=1;esp+=4;}
static void sub_00138930(void) {played++;esp+=4;}
static void sub_00136A00(void) {assert(!"unexpected native mode");}
static void sub_00138B30(void) {assert(!"unexpected native mode");}
static void sub_00137510(void) {assert(!"unexpected native mode");}
'''
MAIN = r'''
static void call(void(*fn)(void),unsigned n,const uint32_t *args) {
 esp=0x3F00000;for(unsigned i=n;i;i--)PUSH32(esp,args[i-1]);
 PUSH32(esp,0);fn();assert(esp==0x3F00000-4*n);esp+=4*n;
}
static void setup(void) {
 memset(ram,0,64u*1024*1024);MEM32(0x3ADB6C)=0x5000;MEM32(0x3ADB78)=3;
 const uint16_t families[]={1,16626,40963};
 for(unsigned i=0;i<3;i++) {
  MEM32(0x5000+8*i)=100+i;MEM32(0x5004+8*i)=0x6000+32*i;
  MEM16(0x6000+32*i)=families[i];MEM16(0x6002+32*i)=601;MEM16(0x600A+32*i)=5;
 }
}
static void descriptor(uint32_t at,uint16_t family,unsigned mode) {
 MEM16(at)=family;MEM8(at+2)=0;MEM8(at+3)=(uint8_t)mode;
}
static void lookup(uint16_t family,uint32_t voice,int hit) {
 uint32_t args[]={0xABCD0000u|family,voice,0x7000};MEM32(0x7000)=0xAABBCCDD;
 call(sub_00135CB0,3,args);assert((LO16(eax)!=65535)==hit);
 assert(MEM32(0x7000)==(hit?100u+LO16(eax):0xAABBCCDD));cases++;
}
static void resolve(uint16_t family,unsigned mode,uint32_t dynamic,int hit) {
 descriptor(0x7100,family,mode);MEM32(0x7200)=dynamic;memset(ram+0x7300,0xA5,12);
 eax=0x7100;ebx=0x7200;esi=0x7300;call(sub_00137780,0,NULL);
 assert(eax==(uint32_t)hit);assert((MEM32(0x7300)!=UINT32_MAX)==hit);
 if(hit&&mode==2)assert(MEM16(0x7306)==dynamic);cases++;
}
static void alternatives(unsigned scenario) {
 memset(ram+0x4000,0,0x100);MEM16(0x4000)=123;MEM8(0x4006)=3;
 MEM32(0x7400)=123;MEM32(0x7404)=601;MEM16(0x3AD980)=999;
 for(unsigned i=0;i<3;i++) {
  MEM16(0x400C+2*i)=(uint16_t)(16+16*i);
  uint32_t group=0x4040+64*i;MEM8(group+1)=100;MEM8(group+2)=4;MEM8(group+8)=4;
  descriptor(group+16,0,1);
 }
 // First candidate misses exactly; scenario3 instead succeeds immediately.
 descriptor(0x4050,scenario==3?1:0,1);
 descriptor(0x4090,scenario==1?0:16626,scenario==2?0:1);
 for(unsigned i=0;i<3;i++)MEM8(0x4052+64*i)=1;
 attempts=samples=played=0;uint32_t args[]={0x7400,0x7500};call(sub_00138CA0,2,args);
 assert(attempts==(scenario==1?3u:scenario==3?1u:2u));
 assert(eax==(scenario==1?0u:1u)&&samples==(scenario==1?0u:1u)&&played==samples);cases++;
}
int main(void) {
 ram=calloc(1,64u*1024*1024);assert(ram);setup();
 const uint16_t families[]={1,16626,40963};
 for(unsigned i=0;i<3;i++) {
  lookup(families[i],0xABCD0259,1);lookup(families[i],600,0);
  resolve(families[i],1,600,0);resolve(families[i],1,601,1);
  resolve(families[i],0,600,1);resolve(families[i],2,0,1);
  resolve(families[i],2,4,1);resolve(families[i],2,5,0);
 }
 resolve(0,0,600,0);resolve(0,1,600,0);resolve(0,2,0,0);
 MEM16(0x600A)=65535;resolve(1,2,0,0);MEM16(0x600A)=5;
 for(unsigned scenario=0;scenario<4;scenario++)alternatives(scenario);
 // Empty registered cache must retain the missing sentinel, too.
 MEM32(0x3ADB78)=0;lookup(1,601,0);resolve(1,0,601,0);
 printf("%u voice absence cases passed\n",cases);free(ram);return 0;
}
'''


def main():
    folder = ROOT / 'logs/fighter-voice-absence-oracle'
    folder.mkdir(exist_ok=True)
    source = (ROOT / 'src/recomp/gen/recomp_0009.c').read_text()
    body = '\n'.join(oracle.extract(source, address) for address in FUNCTIONS)
    prototypes = '\n'.join('void sub_' + address + '(void);' for address in FUNCTIONS)
    (folder / 'oracle.c').write_text(oracle.PREAMBLE + EXTRA + prototypes + body + MAIN, encoding='utf-8')
    subprocess.run(['cl.exe', '/nologo', '/O2', '/W3', '/wd4102', str(folder / 'oracle.c'),
                    '/Fe:' + str(folder / 'oracle.exe'), '/Fo:' + str(folder / 'oracle.obj')],
                   cwd=folder, check=True)
    result = subprocess.run([str(folder / 'oracle.exe')], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == '34 voice absence cases passed', result.stdout
    report = {'cases': 34, 'functions': FUNCTIONS, 'native_body_sha256': hashlib.sha256(body.encode()).hexdigest(),
              'scope': 'exact/family-only/matrix lookup, missing sample early-out, event alternatives and exhaustion; counted playback stand-in',
              'native_playtest': False, 'output': result.stdout.strip()}
    (folder / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
