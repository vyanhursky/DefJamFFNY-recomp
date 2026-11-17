/* Optional, reference-bound packed 11:11:10 neck normals. Original source
 * draw tables/buffers stay immutable. Each live participant gets private
 * copies, detached before its native CAF context is destroyed. */
#include "fighter_caf_normals.h"
#include "fighter_caf_layout.h"
#include "fighter_config.h"
#include "hooks/guest_call.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#define NORMAL_CHUNK 131072u
#define NORMAL_ARENA (4u*NORMAL_CHUNK)
static const uint8_t *n_rows;
static uint32_t n_count,n_arena,n_models[4][2],n_tables[4][2],n_original[4][2],n_peers[4][2];
extern void sub_000296B0(void);
static uint32_t nw(const uint8_t *p) {uint32_t v;memcpy(&v,p,4);return v;}
static float nf(const uint8_t *p) {float v;memcpy(&v,p,4);return v;}
static int ns(uint32_t p,uint32_t n) {uint32_t a=p&0x7fffffffu;return a>=0x10000u&&a<0x4000000u&&n<=0x4000000u-a;}
static int packed(uint32_t word) {
    float length=0;
    for(unsigned k=0;k<3;++k) {unsigned bits=k==2?10:11,shift=k==2?22:k*11;int sign=1<<(bits-1),v=(int)(word>>shift);
        float x=(float)((v&(sign-1))-(v&sign))/(float)(sign-1);if(x< -1.f)x=-1.f;length+=x*x;}
    return length>=.01f;
}
int defjam_caf_normals_start(const uint8_t *(*recipe)(uint32_t,uint32_t),const uint8_t *rows,uint32_t count) {
    if(n_rows||!count||count>CAF_NORMAL_MAX)return 0;
    for(uint32_t i=0;i<count;++i) {
        const uint8_t *r=rows+(size_t)i*CAF_NORMAL_STRIDE;uint32_t slot=nw(r+CAF_NORMAL_SLOT);
        if(!recipe(nw(r),nw(r+4))||nw(r+4)>2||(slot!=3&&slot!=12)||nw(r+CAF_NORMAL_RM)>=16||nw(r+CAF_NORMAL_VERTEX)>=65535
            ||!packed(nw(r+CAF_NORMAL_ORIGINAL))||!packed(nw(r+CAF_NORMAL_REPLACEMENT)))return 0;
        for(unsigned k=0;k<3;++k) {float p=nf(r+CAF_NORMAL_POSITION+k*4);if(!isfinite(p)||fabsf(p)>100.f||(k==1&&(p<=10.f||p>=30.f)))return 0;}
        unsigned per_outfit=0;
        for(uint32_t j=0;j<count;++j) {
            const uint8_t *other=rows+(size_t)j*CAF_NORMAL_STRIDE;
            if(!memcmp(r,other,8))++per_outfit;
            if(j<i&&!memcmp(r,other,20))return 0;
        }
        if(per_outfit>128)return 0;
    }
    n_rows=rows;n_count=count;return 1;
}
void defjam_caf_normals_release(void) {n_rows=NULL;n_count=0;}
void defjam_caf_normals_clear(void) {memset(n_peers,0,sizeof n_peers);}
void defjam_caf_normals_detach(uint32_t visual,uint32_t participant) {
    if(participant>=4)return;
    for(unsigned s=0;s<2;++s) {
        uint32_t slot=s?12:3,part=visual+0x140+slot*0x420,model=n_models[participant][s];
        if(model&&ns(part,0x130)&&MEM32(part+0x12c)==model&&ns(model,0xd8)&&MEM32(model+0xcc)==n_tables[participant][s])
            MEM32(model+0xcc)=n_original[participant][s];
        n_models[participant][s]=n_tables[participant][s]=n_original[participant][s]=0;
    }
}
/* Render groups reference RM wrappers, whose immutable programs consume paired
 * parameters at wrapper+4. Opcode9 binds vertex streams. Copy the wrapper and
 * normal stream together so the renderer, not just the morph table, sees it. */
static unsigned arity(unsigned op) {
    static const uint8_t widths[36]={0,1,2,2,2,4,4,0,0,4,0,0,0,0,2,3,2,0,0,0,3,0,0,0,0,3,3,0,0,6,0,2,0,0,0,4};
    return op<36?widths[op]:0;
}
static const char *streams(uint32_t rm,uint32_t *bytes,uint32_t *positions,uint32_t *normals,uint32_t *count) {
    if(!ns(rm,0x3c)||MEM32(rm+0x38)!=rm)return "neck render wrapper differs";
    uint32_t at=MEM32(rm),end=MEM32(rm+8),parameter=rm+0x3c,vertices=0;
    *positions=*normals=*count=0;
    if(end<=at||end-at>65536||!ns(at,end-at))return "neck render program bounds";
    while(at<end) {
        uint32_t word=MEM32(at);if(!word){if(at+4!=end)return "neck render terminator differs";break;}
        unsigned op=word>>16,width=word&65535;
        if(!arity(op)||width!=arity(op)||width*4>=end-at)return "unsupported neck render command";
        if(op!=4&&op!=25&&op!=26) {
            if(parameter-rm>4096||!ns(parameter,8))return "neck render parameter bounds";
            if(op==9) {
                uint32_t slot=MEM32(at+8),stride=MEM32(at+12),n=MEM32(parameter);
                if(slot==0){if(*positions||stride!=12||!n||n>65535)return "neck position stream differs";*positions=MEM32(parameter+4);vertices=n;}
                if(slot==3){if(*normals||stride!=4||!n||n>65535)return "neck normal stream differs";*normals=parameter+4;*count=n;}
            }
            parameter+=8;
        }
        at+=width*4;
    }
    if(at>=end||!*positions||!*normals||vertices!=*count||!ns(*positions,vertices*12)||!ns(MEM32(*normals),vertices*4))return "neck vertex streams differ";
    *bytes=parameter-rm;return NULL;
}
static const char *render_rows(uint32_t model,uint32_t *size,uint32_t *fields,unsigned *population) {
    if(!ns(model,0xd8)||MEM32(model+0xc0))return "unsupported neck model";
    uint32_t groups=MEM32(model+0x9c),base=MEM32(model+0xcc),at=base+4;*population=0;
    if(!groups||groups>16||!ns(base,4)||MEM32(base))return "neck render group bounds";
    for(uint32_t g=0;g<groups;++g) {
        if(!ns(at,4))return "neck render group bounds";
        uint32_t n=MEM32(at);at+=4;
        if(!n||n>16-*population||!ns(at,n*4))return "neck render population differs";
        for(uint32_t i=0;i<n;++i)fields[(*population)++]=at+i*4;
        at+=n*4;
    }
    *size=at-base;return NULL;
}
static const char *apply(uint32_t visual,uint32_t participant,uint32_t selection,uint32_t outfit) {
    if(participant>=4)return "neck participant outside supported range";
    uint32_t models[2],bases[2]={0},sizes[2]={0},fields[2][16],copies[2]={0};unsigned population[2]={0};
    uint32_t rms[2][16]={{0}},rm_bytes[2][16]={{0}},normal_fields[2][16]={{0}},counts[2][16]={{0}};
    unsigned count=0;uint32_t budget=0;
    for(unsigned s=0;s<2;++s) {
        uint32_t part=visual+0x140+(s?12u:3u)*0x420;
        models[s]=ns(part,0x130)?MEM32(part+0x12c):0;n_peers[participant][s]=models[s];
        for(unsigned peer=0;peer<4;++peer)if(peer!=participant)for(unsigned k=0;k<2;++k)
            if(models[s]&&models[s]==n_models[peer][k]) {
                if(ns(models[s],0xd8)&&MEM32(models[s]+0xcc)==n_tables[peer][k])MEM32(models[s]+0xcc)=n_original[peer][k];
                return "neck model aliases another participant";
            }
    }
    for(uint32_t i=0;i<n_count;++i) {
        const uint8_t *r=n_rows+(size_t)i*CAF_NORMAL_STRIDE;if(nw(r)!=selection||nw(r+4)!=outfit)continue;
        unsigned s=nw(r+CAF_NORMAL_SLOT)==12;uint32_t model=models[s],rm=nw(r+CAF_NORMAL_RM),v=nw(r+CAF_NORMAL_VERTEX);
        for(unsigned peer=0;peer<4;++peer)if(peer!=participant)for(unsigned k=0;k<2;++k)
            if(model&&model==n_peers[peer][k])return "neck model aliases another participant";
        if(!sizes[s]) {
            const char *why=render_rows(model,&sizes[s],fields[s],&population[s]);if(why)return why;
            bases[s]=MEM32(model+0xcc);budget+=(sizes[s]+15)&~15u;
        }
        if(rm>=population[s])return "neck render mesh differs";
        uint32_t wrapper=MEM32(fields[s][rm]);if(!ns(wrapper,4))return "neck render wrapper bounds";
        uint32_t resource=MEM32(wrapper),positions=0,normal=0,n=0,bytes=0;
        if(wrapper!=resource+0x38)return "neck render wrapper differs";
        const char *why=streams(resource,&bytes,&positions,&normal,&n);if(why)return why;
        if(v>=n)return "neck normal topology differs";
        for(unsigned k=0;k<3;++k) {float p=MEMF(positions+v*12+k*4);if(!isfinite(p)||fabsf(p-nf(r+CAF_NORMAL_POSITION+k*4))>.0002f)return "neck normal position differs";}
        if(MEM32(MEM32(normal)+v*4)!=nw(r+CAF_NORMAL_ORIGINAL))return "neck normal source differs";
        if(!rms[s][rm]) {rms[s][rm]=resource;rm_bytes[s][rm]=bytes;normal_fields[s][rm]=normal;counts[s][rm]=n;budget+=((bytes+15)&~15u)+((n*4+15)&~15u);}
        ++count;
    }
    if(!count)return NULL;
    if(models[0]&&models[0]==models[1])return "neck slots alias the same model";
    if(budget>NORMAL_CHUNK)return "neck normal private buffer budget exceeded";
    if(!n_arena){uint32_t args[]={NORMAL_ARENA,0x298908,0x100};n_arena=guest_call(sub_000296B0,0,3,args);}
    if(!ns(n_arena,NORMAL_ARENA))return "neck normal arena unavailable";
    uint32_t cursor=n_arena+participant*NORMAL_CHUNK,private_normal[2][16]={{0}};
    for(unsigned s=0;s<2;++s)if(sizes[s]) {
        copies[s]=cursor;memcpy((void *)XBOX_PTR(cursor),(const void *)XBOX_PTR(bases[s]),sizes[s]);cursor+=(sizes[s]+15)&~15u;
        for(unsigned rm=0;rm<16;++rm)if(rms[s][rm]) {
            cursor=(cursor+15)&~15u;uint32_t resource=cursor;cursor+=(rm_bytes[s][rm]+15)&~15u;
            memcpy((void *)XBOX_PTR(resource),(const void *)XBOX_PTR(rms[s][rm]),rm_bytes[s][rm]);
            MEM32(resource+0x38)=resource;
            private_normal[s][rm]=cursor;
            memcpy((void *)XBOX_PTR(cursor),(const void *)XBOX_PTR(MEM32(normal_fields[s][rm])),counts[s][rm]*4u);cursor+=(counts[s][rm]*4+15)&~15u;
            MEM32(resource+normal_fields[s][rm]-rms[s][rm])=private_normal[s][rm];
            MEM32(copies[s]+fields[s][rm]-bases[s])=resource+0x38;
            if(defjam_fighter_env("RECOMP_FIGHTER_FACE_TRACE"))fprintf(stderr,"[CAF-NORMAL] slot=%u rm=%u original-rm=%08X private-rm=%08X original-normal=%08X private-normal=%08X vertices=%u\n",s?12:3,rm,rms[s][rm],resource,MEM32(normal_fields[s][rm]),private_normal[s][rm],counts[s][rm]);
        }
    }
    for(uint32_t i=0;i<n_count;++i) {
        const uint8_t *r=n_rows+(size_t)i*CAF_NORMAL_STRIDE;if(nw(r)!=selection||nw(r+4)!=outfit)continue;
        unsigned s=nw(r+CAF_NORMAL_SLOT)==12;
        MEM32(private_normal[s][nw(r+CAF_NORMAL_RM)]+nw(r+CAF_NORMAL_VERTEX)*4)=nw(r+CAF_NORMAL_REPLACEMENT);
    }
    for(unsigned s=0;s<2;++s)if(sizes[s]) {
        n_models[participant][s]=models[s];n_tables[participant][s]=copies[s];n_original[participant][s]=bases[s];MEM32(models[s]+0xcc)=copies[s];
    }
    fprintf(stderr,"[FIGHTERS] CAF neck normals participant=%u logical=%u outfit=%u corrections=%u source-buffers=unchanged private-bytes=%u\n",participant,selection,outfit,count,budget);
    return NULL;
}
void defjam_caf_normals_apply(uint32_t visual,uint32_t participant,uint32_t selection,uint32_t outfit) {
    if(!n_count)return;
    const char *why=apply(visual,participant,selection,outfit);
    if(why)fprintf(stderr,"[FIGHTERS] CAF neck normals not applied participant=%u logical=%u outfit=%u: %s; original normals retained\n",participant,selection,outfit,why);
}
