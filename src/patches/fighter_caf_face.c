/* Closed position-only CAF sculpt adapter. Original rig, UVs, materials and
 * animation streams remain owned by the original per-participant head model. */
#include "fighter_caf_face.h"
#include "fighter_caf_layout.h"
#include "fighter_fatal.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define FACE_MAX (8u*1024u*1024u)
static const uint8_t *s_data; /* rows inside the loaded container, which stays resident */
static uint32_t s_count,s_arena,s_live[4][10],s_sizes[4][10];
static uint8_t s_unknown[4]; /* A CAF participant without a sculpt whose head layout is not the supported one. */
static const uint32_t s_rms[9]={0,1,2,3,4,5,6,7,9};
static const uint32_t s_counts[9]={54,218,70,92,73,51,51,81,20};
extern void sub_000296B0(void),sub_00026140(void);
static uint32_t word(const uint8_t *p) {uint32_t v;memcpy(&v,p,4);return v;}
static float scalar(const uint8_t *p) {float v;memcpy(&v,p,4);return v;}
static void stop(const char *why) {defjam_fighter_fatal("face sculpt",why);}
static int span(uint32_t p,uint32_t n) {uint32_t a=p&0x7fffffffu;return a>=0x10000u&&a<0x4000000u&&n<=0x4000000u-a;}
static const uint8_t *find(uint32_t selection,uint32_t outfit) {
    for(uint32_t i=0;i<s_count;++i) {const uint8_t *r=s_data+(size_t)i*CAF_FACE_STRIDE;if(word(r+CAF_FACE_SELECTION)==selection&&word(r+CAF_FACE_OUTFIT)==outfit)return r;}
    return NULL;
}
/* Validates the container's sculpt rows. They stay where they are; nothing is copied, and a failure keeps nothing. */
int defjam_caf_faces_start(const uint8_t *(*recipe)(uint32_t,uint32_t),const uint8_t *rows,uint32_t count) {
    if(s_data||!count||count>FACE_MAX/CAF_FACE_STRIDE)return 0;
    int valid=1;
    for(uint32_t i=0;valid&&i<count;++i) {
        const uint8_t *r=rows+(size_t)i*CAF_FACE_STRIDE;
        if(word(r+CAF_FACE_OUTFIT)>2)valid=0;
        const uint8_t *base=recipe(word(r+CAF_FACE_SELECTION),word(r+CAF_FACE_OUTFIT));
        static const unsigned slots[CAF_FACE_BASIS_COUNT]={0,5,6,9,10,11};
        if(!base)valid=0;
        else for(unsigned k=0;k<CAF_FACE_BASIS_COUNT;++k)if(word(r+CAF_FACE_BASIS_AT(k))!=word(base+CAF_ROW_VALUE_AT(slots[k])))valid=0;
        for(uint32_t j=0;j<i;++j)if(!memcmp(r+CAF_FACE_SELECTION,rows+(size_t)j*CAF_FACE_STRIDE+CAF_FACE_SELECTION,8))valid=0;
        for(unsigned v=0;v<CAF_FACE_VERTEX_COUNT;++v)for(unsigned k=0;k<6;++k) {
            float x=scalar(r+CAF_FACE_VERTEX_AT(v)+k*4);if(!isfinite(x)||fabsf(x)>(k<3?100.f:.6f))valid=0;
        }
    }
    if(!valid)return 0;
    s_data=rows;s_count=count;fprintf(stderr,"[FIGHTERS] validated %u CAF face sculpts\n",count);return 1;
}
void defjam_caf_faces_clear(void) {memset(s_live,0,sizeof(s_live));memset(s_sizes,0,sizeof(s_sizes));memset(s_unknown,0,sizeof(s_unknown));}
static uint32_t hash_bytes(uint32_t p,uint32_t size) {
    uint32_t hash=2166136261u;const uint8_t *bytes=(const uint8_t *)XBOX_PTR(p);
    for(uint32_t i=0;i<size;++i)hash=(hash^bytes[i])*16777619u;
    return hash;
}
/* Walks the original head model's channel table. Returns NULL and the address of its ten Coordinates
 * buffers when the layout is exactly the one the sculpt adapter was built for, else the reason it is not. */
static const char *head_layout(uint32_t model,uint32_t *rows_out) {
    if(!span(model,0xd8))return "head model unavailable";
    uint32_t group=MEM32(model+0xb8)+4,rows=0,count=0;
    for(unsigned i=0;i<16;++i) {
        if(!span(group,8))return "channel bounds";
        uint32_t name=MEM32(group),n=MEM32(group+4);
        if(!name)break;
        if(n>16||!span(name,16)||!span(group+8,n*16))return "channel layout";
        if(!memcmp((const void *)XBOX_PTR(name),"Coordinates\0",12)){rows=group+8;count=n;break;}
        group+=8+n*16;
    }
    if(!rows||count!=10||MEM32(model+0xc0)!=0)return "unsupported original Coordinates layout";
    for(unsigned i=0;i<10;++i) {
        uint32_t row=rows+i*16,n=MEM16(row+4),p=MEM32(row+12);
        if(MEM32(row)!=i||MEM16(row+6)!=24||!n||n>1024||!span(p,n*12))return "unsupported original float3 buffer";
    }
    *rows_out=rows;return NULL;
}
void defjam_caf_faces_apply(uint32_t visual,uint32_t participant,uint32_t selection,uint32_t outfit,const uint8_t *recipe) {
    if(!s_count)return;
    if(participant>=4)stop("participant outside supported range");
    /* Only a fighter that has a sculpt is held to the sculpt layout. Every other CAF participant keeps its
     * original head untouched, so an unfamiliar head layout must not stop the game; its buffers are only
     * remembered so that a sculpted peer can prove it never writes into them. */
    const uint8_t *source=find(selection,outfit);
    uint32_t part=visual+0x140+2u*0x420,model=MEM32(part+0x12c),rows=0;
    const char *why=head_layout(model,&rows);
    s_unknown[participant]=0;
    if(!source) {
        memset(s_live[participant],0,sizeof s_live[participant]);memset(s_sizes[participant],0,sizeof s_sizes[participant]);
        if(why)s_unknown[participant]=1;
        else for(unsigned i=0;i<10;++i){uint32_t row=rows+i*16;s_live[participant][i]=MEM32(row+12);s_sizes[participant][i]=MEM16(row+4)*12u;}
        return;
    }
    if(why)stop(why);
    for(unsigned peer=0;peer<4;++peer)if(peer!=participant&&s_unknown[peer])stop("another participant's head layout cannot be isolated from the sculpt");
    uint32_t peers[4][10]={{0}};
    for(unsigned i=0;i<10;++i) {
        uint32_t row=rows+i*16,n=MEM16(row+4),p=MEM32(row+12);
        for(unsigned peer=0;peer<4;++peer)if(peer!=participant)for(unsigned j=0;j<10;++j)if(s_live[peer][j]) {
            uint32_t a=p&0x7fffffffu,b=s_live[peer][j]&0x7fffffffu;
            if(a<b+s_sizes[peer][j]&&b<a+n*12)stop("head coordinates alias another participant");
            peers[peer][j]=hash_bytes(s_live[peer][j],s_sizes[peer][j]);
        }
        s_live[participant][i]=p;s_sizes[participant][i]=n*12;
    }
    static const unsigned slots[6]={0,5,6,9,10,11};
    for(unsigned i=0;i<CAF_FACE_BASIS_COUNT;++i)if(word(source+CAF_FACE_BASIS_AT(i))!=word(recipe+CAF_ROW_VALUE_AT(slots[i])))stop("sculpt preset basis differs");
    /* Preflight every reference before invoking the native evaluator. This is
     * the binding proof: hashes supplied by a pack cannot replace live XYZ. */
    float low=100.f,high=-100.f;uint32_t vertex=0;
    for(unsigned m=0;m<9;++m) {
        uint32_t row=rows+s_rms[m]*16,n=MEM16(row+4),p=MEM32(row+12);
        if(n!=s_counts[m])stop("head topology differs");
        for(uint32_t v=0;v<n;++v,++vertex)for(unsigned k=0;k<3;++k) {
            float native=MEMF(p+v*12+k*4),expected=scalar(source+CAF_FACE_VERTEX_AT(vertex)+k*4);
            if(!isfinite(native)||fabsf(native-expected)>.0002f)stop("sculpt template differs from assembled original head");
            if(k==1){low=fminf(low,native);high=fmaxf(high,native);}
        }
    }
    for(unsigned v=0;v<CAF_FACE_VERTEX_COUNT;++v)if(scalar(source+CAF_FACE_VERTEX_AT(v)+4)<=low+(high-low)*.12f)
        for(unsigned k=0;k<3;++k)if(fabsf(scalar(source+CAF_FACE_VERTEX_AT(v)+CAF_FACE_VERTEX_DELTA+k*4))>1e-6f)stop("protected neck seam moved");
    if(!s_arena){uint32_t args[]={0x4000,0x298908,0x100};s_arena=guest_call(sub_000296B0,0,3,args);}
    if(!span(s_arena,0x4000))stop("sculpt arena unavailable");
    memset((void *)XBOX_PTR(s_arena),0,0x4000);
    uint32_t root=s_arena+32,label=s_arena+0x3f00;
    memcpy((void *)XBOX_PTR(label),"Coordinates",12);
    MEM32(s_arena)=root;MEM32(root)=1;MEM32(root+8)=s_arena+16;MEM32(root+16)=1;
    MEM32(root+20)=label;MEM32(root+24)=1;MEM32(root+28)=0;MEM32(root+32)=9;
    uint32_t at=root+36;vertex=0;
    for(unsigned m=0;m<9;++m) {
        uint32_t n=s_counts[m];MEM32(at)=0xc0000000u+n*12;MEM32(at+4)=n;MEM32(at+8)=0;MEM32(at+12)=s_rms[m];at+=16;
        for(uint32_t v=0;v<n;++v,++vertex) {memcpy((void *)XBOX_PTR(at),source+CAF_FACE_VERTEX_AT(vertex)+CAF_FACE_VERTEX_DELTA,12);at+=12;}
    }
    uint32_t original=MEM32(model+0xd4),args[]={s_arena,0x3f7fffff};
    guest_call(sub_00026140,part,2,args);MEM32(model+0xd4)=original;
    vertex=0;float max_error=0;
    for(unsigned m=0;m<9;++m)for(unsigned v=0;v<s_counts[m];++v,++vertex)for(unsigned k=0;k<3;++k) {
        float expected=scalar(source+CAF_FACE_VERTEX_AT(vertex)+k*4)+scalar(source+CAF_FACE_VERTEX_AT(vertex)+CAF_FACE_VERTEX_DELTA+k*4);
        float error=fabsf(MEMF(s_live[participant][s_rms[m]]+v*12+k*4)-expected);max_error=fmaxf(max_error,error);
        if(!isfinite(error)||error>.0002f)stop("native sculpt result differs from requested coordinates");
    }
    for(unsigned peer=0;peer<4;++peer)if(peer!=participant)for(unsigned j=0;j<10;++j)
        if(s_live[peer][j]&&peers[peer][j]!=hash_bytes(s_live[peer][j],s_sizes[peer][j]))stop("sculpt changed another participant");
    fprintf(stderr,"[FIGHTERS] face sculpt participant=%u logical=%u outfit=%u vertices=710 max-error=%.8g peer-buffers=unchanged\n",participant,selection,outfit,max_error);
}
