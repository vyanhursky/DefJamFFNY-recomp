/* Closed position-only CAF sculpt adapter. Original rig, UVs, materials and
 * animation streams remain owned by the original per-participant head model. */
#include "fighter_caf_face.h"
#include "fighter_caf_layout.h"
#include "fighter_fatal.h"
#include "hooks/guest_call.h"
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
extern void sub_000296B0(void),sub_00026140(void),sub_0021BB10(void);
static uint32_t word(const uint8_t *p) {uint32_t v;memcpy(&v,p,4);return v;}
static float scalar(const uint8_t *p) {float v;memcpy(&v,p,4);return v;}
static void stop(const char *why) {defjam_fighter_fatal("face sculpt",why);}
static int span(uint32_t p,uint32_t n) {uint32_t a=p&0x7fffffffu;return a>=0x10000u&&a<0x4000000u&&n<=0x4000000u-a;}
/* Optional, bounded normal annex. No supplied render programs or pointers.
 * Construct both parts before publication. A mismatch rolls back only pointers
 * still owned by this lease and quarantines its arena for the process lifetime.
 * Draw rejection suppresses that one private upload; native parts resume later. */
#define NORMAL_MAX CAF_NORMAL_MAX
#define NORMAL_ARENA 65536u
static const uint8_t *s_normal_data;
static uint32_t s_normal_count;
static uint32_t s_normal_resources[4][2][16],s_normal_hash[4][2][16];
static uint32_t s_normal_params[4][2][16],s_normal_bytes[4][2][16];
static uint8_t s_normal_drawn[4][2][16];
static struct {uint32_t visual,arena,used,part[2],original[2],clone[2];uint8_t published[2],blocked;} s_normals[4];
static uint32_t hash_bytes(uint32_t p,uint32_t size);
static unsigned normal_error(const char *why) {
    fprintf(stderr,"[FIGHTERS] neck normals unavailable: %s\n",why);return 0;
}
static int normal_unit(uint32_t w,float n[3]) {
    static const unsigned bits[3]={11,11,10},shifts[3]={0,11,22};float len=0;
    for(unsigned i=0;i<3;++i){int v=(w>>shifts[i])&((1u<<bits[i])-1);if(v&(1u<<(bits[i]-1)))v-=1u<<bits[i];n[i]=fmaxf(-1.f,(float)v/((1u<<(bits[i]-1))-1));len+=n[i]*n[i];}
    if(len<.25f)return 0;len=sqrtf(len);for(unsigned i=0;i<3;++i)n[i]/=len;return 1;
}
static int normal_records_valid(const uint8_t *p) {
    unsigned n=word(p);if(!n||n>NORMAL_MAX)return 0;
    for(unsigned i=0;i<n;++i){const uint8_t *r=p+4+i*32;float a[3],b[3];
        if((word(r)!=3&&word(r)!=12)||word(r+4)>=16||word(r+8)>=1024)return 0;
        float x=scalar(r+12),y=scalar(r+16),z=scalar(r+20);
        if(!isfinite(x)||!isfinite(y)||!isfinite(z)||fabsf(x)>1.1f||y<17.5f||y>19.5f||fabsf(z)>1.1f)return 0;
        if(!normal_unit(word(r+24),a)||!normal_unit(word(r+28),b)||a[0]*b[0]+a[1]*b[1]+a[2]*b[2]<.819152f)return 0;
        for(unsigned j=0;j<i;++j)if(!memcmp(r,p+4+j*32,12))return 0;
    }
    for(unsigned i=4+n*32;i<4+NORMAL_MAX*32;++i)if(p[i])return 0;
    return 1;
}
static void normal_unbind(unsigned p,unsigned i) {
    for(unsigned v=0;v<16;++v)if(s_normal_resources[p][i][v]) {
        uint32_t resource=s_normal_resources[p][i][v];
        for(unsigned stream=0;stream<16;++stream) {
            if(MEM32(0x236c18+stream*12)==resource) {
                uint32_t args[]={stream,0,0};guest_call(sub_0021BB10,0,3,args);
            }
            if(MEM32(0x3a6e20+stream*4)==resource) {
                MEM32(0x3a6e20+stream*4)=0;MEM32(0x3a6e60+stream*4)=0;
            }
        }
        s_normal_resources[p][i][v]=s_normal_drawn[p][i][v]=s_normal_hash[p][i][v]=0;
        /* Retain parameter tombstones for a quarantined arena: an in-flight
         * RM dispatcher may still hold these addresses after model rollback. */
        if(!s_normals[p].blocked)s_normal_params[p][i][v]=s_normal_bytes[p][i][v]=0;
    }
}
static void normal_restore(unsigned p,unsigned i) {
    uint32_t part=s_normals[p].part[i];
    if(s_normals[p].published[i]) {
        if(span(part+0x12c,4)&&MEM32(part+0x12c)==s_normals[p].clone[i])MEM32(part+0x12c)=s_normals[p].original[i];
        else {s_normals[p].blocked=1;fprintf(stderr,"[FIGHTERS] neck normals ownership changed participant=%u slot=%u; arena quarantined\n",p,i?12:3);}
    }
    normal_unbind(p,i);s_normals[p].clone[i]=0;s_normals[p].published[i]=0;
}
static void normal_rollback(unsigned p,int quarantine) {
    if(quarantine)s_normals[p].blocked=1;
    for(unsigned i=0;i<2;++i)normal_restore(p,i);
}
void defjam_caf_normals_release(uint32_t visual,uint32_t slot) {
    for(unsigned p=0;p<4;++p)if(s_normals[p].visual==visual)for(unsigned i=0;i<2;++i)
        if(slot==(i?12u:3u)&&s_normals[p].clone[i]) {
            normal_restore(p,i);
            fprintf(stderr,"[FIGHTERS] neck normals restored participant=%u slot=%u\n",p,slot);
        }
}
/* Check the actual native SetVertexStream consumer, including its private
 * parameter address. A changed resource cannot escape the check by changing ID. */
int defjam_caf_normals_stream(uint32_t command,uint32_t parameter) {
    for(unsigned p=0;p<4;++p)for(unsigned i=0;i<2;++i)for(unsigned rm=0;rm<16;++rm)
        if(parameter&&s_normal_params[p][i][rm]==parameter) {
            if(s_normals[p].blocked)return 0;
            unsigned bytes=s_normal_bytes[p][i][rm];uint32_t data=span(parameter,8)?MEM32(parameter+4):0;
            int valid=span(command,16)&&MEM32(command+4)==0&&MEM32(command+8)==3&&MEM32(command+12)==4
                &&span(data-20,20)&&span(data,bytes)&&MEM32(parameter)==bytes/4u&&MEM32(data-16)==bytes&&MEM32(data-12)==4
                &&MEM32(data-20)==s_normal_resources[p][i][rm]&&span(MEM32(data-20),12)
                &&(MEM32(MEM32(data-20)+4)&0x7fffffffu)==(data&0x7fffffffu)&&hash_bytes(data,bytes)==s_normal_hash[p][i][rm];
            if(!valid) {normal_rollback(p,1);normal_error("private stream changed before draw; upload skipped and arena quarantined");return 0;}
            if(!s_normal_drawn[p][i][rm]) {
                s_normal_drawn[p][i][rm]=1;
                fprintf(stderr,"[FIGHTERS] neck normals drawn participant=%u slot=%u rm=%u packed-bytes=%u verified=yes\n",p,i?12:3,rm,bytes);
            }
            return 1;
        }
    return 1;
}
static uint32_t normal_alloc(unsigned p,unsigned bytes) {
    unsigned offset=(s_normals[p].used+15u)&~15u;
    if(offset>NORMAL_ARENA||bytes>NORMAL_ARENA-offset)return 0;
    uint32_t address=s_normals[p].arena+offset;s_normals[p].used=offset+bytes;return address;
}
/* Only observed typed stream commands; never execute supplied programs. */
static uint32_t normal_streams(uint32_t rm,uint32_t *position,uint32_t *normal,unsigned *count) {
    if(!span(rm,0x3c)||MEM32(rm+0x38)!=rm)return normal_error("normal RM wrapper");
    uint32_t at=MEM32(rm),end=MEM32(rm+8),pair=rm+0x3c;*position=*normal=*count=0;
    if(end<=at||end-at>65536||!span(at,end-at))return normal_error("normal RM program bounds");
    for(;at<end;) {
        unsigned token=MEM32(at),op=token>>16,width=token&65535,arity=0;
        if(!token){if(at+4!=end)return normal_error("normal RM trailing program");break;}
        switch(op){case 1:arity=1;break;case 2:case 3:case 4:case 14:case 16:case 31:arity=2;break;case 15:case 20:case 25:case 26:arity=3;break;case 5:case 6:case 9:case 35:arity=4;break;case 29:arity=6;break;default:return normal_error("normal RM unknown opcode");}
        if(width!=arity||width*4>=end-at)return normal_error("normal RM opcode bounds");
        if(op!=4&&op!=25&&op!=26){if(!span(pair,8))return normal_error("normal RM parameter bounds");
            if(op==9){unsigned instance_stride=MEM32(at+4),stream=MEM32(at+8),stride=MEM32(at+12),n=MEM32(pair);
                if(stream==0){if(*position||stride!=12||!n||n>1024||instance_stride>16384)return normal_error("normal position stream");*position=MEM32(pair+4);*count=n;}
                if(stream==3){if(*normal||stride!=4||!n||n>1024||instance_stride)return normal_error("normal packed stream");*normal=pair;}
            }pair+=8;
        }at+=width*4;
    }
    if(at>=end||!*position||!*normal||MEM32(*normal)!=*count||!span(*position,*count*12)||!span(MEM32(*normal+4),*count*4)) {
        fprintf(stderr,"[FIGHTERS] normal stream diagnostic rm=%08x at=%08x end=%08x xyz=%08x normal-param=%08x count=%u normal-count=%u normal-data=%08x\n",rm,at,end,*position,*normal,*count,*normal?MEM32(*normal):0,*normal?MEM32(*normal+4):0);
        for(uint32_t x=MEM32(rm);x<end&&x<MEM32(rm)+256;x+=4)fprintf(stderr,"[FIGHTERS] normal program +%u=%08x\n",x-MEM32(rm),MEM32(x));
        return normal_error("normal stream layout");
    }
    return pair-rm;
}
static void normals_apply(uint32_t visual,unsigned participant,const uint8_t *source) {
    const uint8_t *entry=NULL;const char *reason="normal construction failed";
    for(unsigned i=0;i<s_normal_count;++i){const uint8_t *r=s_normal_data+(size_t)i*CAF_NORMAL_STRIDE;if(!memcmp(r,source,8)){entry=r;break;}}
    if(!entry||s_normals[participant].blocked)return;
    const uint8_t *rows=entry+12;unsigned count=word(entry+8),changed=0;
    if(s_normals[participant].clone[0]||s_normals[participant].clone[1]){reason="normal clone still live at construction";goto reject;};
    if(!s_normals[participant].arena){uint32_t args[]={NORMAL_ARENA,0x298908,0x100};s_normals[participant].arena=guest_call(sub_000296B0,0,3,args);}
    if(!span(s_normals[participant].arena,NORMAL_ARENA)){reason="normal private allocation";goto reject;};
    s_normals[participant].used=0;s_normals[participant].visual=visual;
    /* Build both parts completely before publishing either model pointer. */
    for(unsigned part_index=0;part_index<2;++part_index){unsigned slot=part_index?12:3,needed=0;
        for(unsigned i=0;i<count;++i)needed+=word(rows+i*32)==slot;if(!needed)continue;
        uint32_t part=visual+0x140+slot*0x420;if(!span(part+0x12c,4)){reason="normal part bounds";goto reject;};
        uint32_t model=MEM32(part+0x12c);if(!span(model,0xd8)){reason="normal model bounds";goto reject;};
        unsigned groups=MEM32(model+0x9c);uint32_t table=MEM32(model+0xcc),end=table+4;
        if(!groups||groups>16||!span(table,4)||MEM32(table)){reason="normal material table";goto reject;};
        unsigned total=0;
        for(unsigned g=0;g<groups;++g){if(!span(end,4)){reason="normal group bounds";goto reject;};unsigned n=MEM32(end);if(!n||n>32-total||!span(end+4,n*4)){reason="normal group population";goto reject;};total+=n;end+=4+n*4;}
        uint32_t clone=normal_alloc(participant,0xd8),copy=normal_alloc(participant,end-table);
        if(!clone||!copy){reason="normal arena budget";goto reject;}
        memcpy((void *)XBOX_PTR(clone),(const void *)XBOX_PTR(model),0xd8);memcpy((void *)XBOX_PTR(copy),(const void *)XBOX_PTR(table),end-table);MEM32(clone+0xcc)=copy;
        unsigned rm_index=0;uint32_t cursor=table+4;
        for(unsigned g=0;g<groups;++g){unsigned population=MEM32(cursor);cursor+=4;
            for(unsigned j=0;j<population;++j,++rm_index){unsigned matches=0;
                for(unsigned i=0;i<count;++i)if(word(rows+i*32)==slot&&word(rows+i*32+4)==rm_index)++matches;
                if(!matches)continue;
                uint32_t wrapper=MEM32(cursor+j*4);if(!span(wrapper,4)){reason="normal wrapper bounds";goto reject;};uint32_t rm=MEM32(wrapper);
                if(wrapper!=rm+0x38){reason="normal wrapper identity";goto reject;};
                uint32_t xyz,param;unsigned vertices;uint32_t bytes=normal_streams(rm,&xyz,&param,&vertices);if(!bytes){reason="normal streams rejected";goto reject;}
                uint32_t data=MEM32(param+4),vb=data-20;
                if(!span(vb,20)||MEM32(vb+4)!=vertices*4||MEM32(vb+8)!=4){reason="normal VB layout";goto reject;};
                uint32_t resource=MEM32(vb);if(!span(resource,12)){reason="normal GPU resource bounds";goto reject;};
                /* Native D3D resource Data must address the original stream. */
                if((MEM32(resource+4)&0x7fffffffu)!=(data&0x7fffffffu)){
                    fprintf(stderr,"[FIGHTERS] normal resource data=%08x vb-data=%08x common=%08x\n",MEM32(resource+4),data,MEM32(resource));{reason="normal GPU source address differs";goto reject;};}
                for(unsigned i=0;i<count;++i){const uint8_t *r=rows+i*32;if(word(r)!=slot||word(r+4)!=rm_index)continue;unsigned v=word(r+8);
                    if(v>=vertices||MEM32(data+v*4)!=word(r+24)){reason="normal source word differs";goto reject;};
                    for(unsigned k=0;k<3;++k)if(!isfinite(MEMF(xyz+v*12+k*4))||fabsf(MEMF(xyz+v*12+k*4)-scalar(r+12+k*4))>.0002f){reason="normal source position differs";goto reject;};
                }
                uint32_t original_hash=hash_bytes(data,vertices*4),rmcopy=normal_alloc(participant,bytes),vbc=normal_alloc(participant,20+vertices*4),res=normal_alloc(participant,12);
                if(!rmcopy||!vbc||!res){reason="normal arena budget";goto reject;}
                memcpy((void *)XBOX_PTR(rmcopy),(const void *)XBOX_PTR(rm),bytes);MEM32(rmcopy+0x38)=rmcopy;
                memcpy((void *)XBOX_PTR(vbc),(const void *)XBOX_PTR(vb),20+vertices*4);memcpy((void *)XBOX_PTR(res),(const void *)XBOX_PTR(resource),12);
                MEM32(res)=(MEM32(resource)&~0x78ffffu)|1;MEM32(res+4)=(vbc+20)&0x7fffffffu;MEM32(res+8)=0;
                s_normal_resources[participant][part_index][rm_index]=res;
                s_normal_params[participant][part_index][rm_index]=rmcopy+(param-rm);
                s_normal_bytes[participant][part_index][rm_index]=vertices*4;
                MEM32(vbc)=res;MEM32(vbc+16)=vbc+20;MEM32(rmcopy+(param-rm)+4)=vbc+20;
                for(unsigned i=0;i<count;++i){const uint8_t *r=rows+i*32;if(word(r)==slot&&word(r+4)==rm_index){MEM32(vbc+20+word(r+8)*4)=word(r+28);++changed;}}
                s_normal_hash[participant][part_index][rm_index]=hash_bytes(vbc+20,vertices*4);
                if(hash_bytes(data,vertices*4)!=original_hash){reason="normal changed shared source";goto reject;};
                MEM32(copy+(cursor-table)+j*4)=rmcopy+0x38;
            }cursor+=population*4;
        }
        s_normals[participant].part[part_index]=part;s_normals[participant].original[part_index]=model;s_normals[participant].clone[part_index]=clone;
    }
    if(changed!=count){reason="normal descriptor has missing mesh";goto reject;};
    for(unsigned i=0;i<2;++i)if(s_normals[participant].clone[i]) {
        MEM32(s_normals[participant].part[i]+0x12c)=s_normals[participant].clone[i];s_normals[participant].published[i]=1;
    }
    fprintf(stderr,"[FIGHTERS] neck normals participant=%u vertices=%u private-bytes=%u shared-source=unchanged\n",participant,changed,s_normals[participant].used);
    return;
reject:
    normal_rollback(participant,1);
    fprintf(stderr,"[FIGHTERS] neck normals rejected participant=%u reason=%s; native parts retained\n",participant,reason);
}

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
int defjam_caf_normals_start(const uint8_t *rows,uint32_t count) {
    if(s_normal_data||!s_count||!count||count>s_count)return 0;
    for(unsigned i=0;i<count;++i) {
        const uint8_t *r=rows+(size_t)i*CAF_NORMAL_STRIDE;
        if(!find(word(r),word(r+4))||!normal_records_valid(r+8))return 0;
        for(unsigned j=0;j<i;++j)if(!memcmp(r,rows+(size_t)j*CAF_NORMAL_STRIDE,8))return 0;
    }
    s_normal_data=rows;s_normal_count=count;
    fprintf(stderr,"[FIGHTERS] validated %u CAF normal corrections\n",count);return 1;
}
void defjam_caf_faces_release(void) {s_data=NULL;s_count=0;s_normal_data=NULL;s_normal_count=0;}
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
    normals_apply(visual,participant,source);
    fprintf(stderr,"[FIGHTERS] face sculpt participant=%u logical=%u outfit=%u vertices=710 max-error=%.8g peer-buffers=unchanged\n",participant,selection,outfit,max_error);
}
