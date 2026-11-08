/* FBP3 admits only a compiler-sealed five-role graph. FBP1/2 keep their legacy
 * type11 guard. Prove every relocated byte before native evaluation, then join
 * actual body/face/hand resources at each subject/counterpart activation. */
#include "fighter_graph_proof.h"
#include "fighter_cpu_pool.h"
#include "fighter_palette_context.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>

#define GRAPH_LIMIT 8192u
#define GRAPH_FIRST 873u
#define GRAPH_BYTES (32u*1024u*1024u)
typedef struct GraphProof { const uint8_t *record; uint32_t bank; char name[8]; } GraphProof;
static GraphProof s_graphs[GRAPH_LIMIT];
static uint8_t *s_data;
static unsigned s_context_logs,s_seal_logs;
extern void sub_000441C0(void);
static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
int defjam_fighter_graph_start(const uint8_t *data,size_t bytes,uint32_t motion_count) {
    if (s_data || bytes<12 || bytes>(64u<<20) || memcmp(data,"FGP1",4) || word(data+4)!=1) return 0;
    uint32_t count=word(data+8), previous=872;
    if (!count || count>GRAPH_LIMIT) return 0;
    size_t at=12;
    for (uint32_t i=0;i<count;++i) {
        if (bytes-at<92) return 0;
        const uint8_t *p=data+at;
        uint32_t ordinal=word(p), size=word(p+4), root=word(p+8), relocs=word(p+12);
        uint32_t bones=word(p+52), rigs=word(p+56);
        if (ordinal<=previous || ordinal>=709+motion_count || ordinal<GRAPH_FIRST
            || ordinal-GRAPH_FIRST>=GRAPH_LIMIT || size<24 || size>GRAPH_BYTES || root>size-24
            || !relocs || relocs>65536 || bones>4096 || rigs>512 || (!bones!=!rigs)) return 0;
        size_t record_bytes=92u+8u*relocs+32u*rigs;
        if (record_bytes>bytes-at) return 0;
        for (unsigned role=0;role<5;++role)
            if (word(p+16+4*role)>size-12 || (!bones && role>=2 && word(p+16+4*role))) return 0;
        for (unsigned selector=0;selector<4;++selector)
            if (bones ? (!word(p+36+4*selector) || word(p+36+4*selector)>256) : word(p+36+4*selector)!=0) return 0;
        uint32_t end=0;
        for (uint32_t j=0;j<relocs;++j) {
            uint32_t field=word(p+92+8*j),target=word(p+96+8*j);
            if (field<end || (field&3) || field>size-4 || target>=size) return 0;
            end=field+4;
        }
        for (uint32_t j=1;j<rigs;++j)
            if (memcmp(p+92+8*relocs+32*(j-1),p+92+8*relocs+32*j,32)>=0) return 0;
        previous=ordinal; at+=record_bytes;
    }
    if (at!=bytes) return 0;
    s_data=(uint8_t *)malloc(bytes);
    if (!s_data) return 0;
    memcpy(s_data,data,bytes);at=12;
    for (uint32_t i=0;i<count;++i) {
        const uint8_t *p=s_data+at;
        s_graphs[word(p)-GRAPH_FIRST].record=p;
        at+=92u+8u*word(p+12)+32u*word(p+56);
    }
    return 1;
}
int defjam_fighter_graph_has(uint32_t ordinal) {
    return ordinal>=GRAPH_FIRST && ordinal-GRAPH_FIRST<GRAPH_LIMIT && s_graphs[ordinal-GRAPH_FIRST].record
        && word(s_graphs[ordinal-GRAPH_FIRST].record+52)!=0;
}
int defjam_fighter_graph_known(uint32_t ordinal,const char *name) {
    if (ordinal<GRAPH_FIRST || ordinal-GRAPH_FIRST>=GRAPH_LIMIT || !name || !*name || strlen(name)>7
        || !s_graphs[ordinal-GRAPH_FIRST].record) return 0;
    memcpy(s_graphs[ordinal-GRAPH_FIRST].name,name,strlen(name)+1);return 1;
}
int defjam_fighter_graph_complete(void) {
    for (unsigned i=0;i<GRAPH_LIMIT;++i) if (s_graphs[i].record && !s_graphs[i].name[0]) return 0;
    return 1;
}
static int seal(GraphProof *proof,uint32_t bank) {
    const uint8_t *p=proof->record;
    uint32_t size=word(p+4),root=word(p+8),relocs=word(p+12);
    if (bank<root) return 0;
    uint32_t base=bank-root;
    if (!defjam_fighter_cpu_range(base,size)) return 0;
    Sha sha;sha_init(&sha);uint32_t end=0;
    for (uint32_t j=0;j<relocs;++j) {
        uint32_t field=word(p+92+8*j),target=word(p+96+8*j);
        if (MEM32(base+field)!=base+target) return 0;
        sha_update(&sha,(const void *)XBOX_PTR(base+end),field-end);
        sha_update(&sha,p+96+8*j,4);end=field+4;
    }
    sha_update(&sha,(const void *)XBOX_PTR(base+end),size-end);
    uint8_t digest[32];sha_final(&sha,digest);
    if (memcmp(digest,p+60,32)) return 0;
    proof->bank=bank;
    if (++s_seal_logs<=128) fprintf(stderr,"[FIGHTERS] graph sealed before constructor name=%s bank=%08X bytes=%u relocations=%u\n",
                                   proof->name,bank,size,relocs);
    return 1;
}
int defjam_fighter_graph_preconstruct(uint32_t bank) {
    if (!s_data || !defjam_fighter_cpu_range(bank,24)) return 1;
    uint32_t count=MEM32(bank+4),names=MEM32(bank+20);
    if (!count || count>65535 || !defjam_fighter_cpu_range(names,4*count)) return 0;
    uint32_t name=MEM32(names);
    if (!defjam_fighter_cpu_range(name,10)) return 0;
    for (unsigned i=0;i<GRAPH_LIMIT;++i) if (s_graphs[i].name[0]) {
        size_t length=strlen(s_graphs[i].name);
        if (!memcmp((const void *)XBOX_PTR(name),s_graphs[i].name,length) && MEM8(name+(uint32_t)length)=='_')
            return seal(&s_graphs[i],bank);
    }
    return 0;
}
int defjam_fighter_graph_bound(uint32_t ordinal,uint32_t bank) {
    if (!s_data) return 1;
    return ordinal>=GRAPH_FIRST && ordinal-GRAPH_FIRST<GRAPH_LIMIT
        && s_graphs[ordinal-GRAPH_FIRST].record && s_graphs[ordinal-GRAPH_FIRST].bank==bank;
}
int defjam_fighter_graph_bank(uint32_t ordinal,uint32_t bank,uint32_t body_index,uint32_t root_index) {
    if (!defjam_fighter_graph_has(ordinal)) return 0;
    GraphProof *proof=&s_graphs[ordinal-GRAPH_FIRST];const uint8_t *p=proof->record;
    if (proof->bank!=bank || bank<word(p+8)) return 0;
    uint32_t base=bank-word(p+8),size=word(p+4);
    uint32_t count=MEM32(bank+4),table=MEM32(bank+16);
    if (body_index>=count || root_index>=count || count>65535 || table<base
        || table-base>size || count*4>size-(table-base)
        || MEM32(table+body_index*4)!=base+word(p+16)
        || MEM32(table+root_index*4)!=base+word(p+20)) return 0;
    for (unsigned role=0;role<5;++role) if ((MEM32(base+word(p+16+4*role))&65535)!=15) return 0;
    return 1;
}
int defjam_fighter_graph_actor(uint32_t ordinal,uint32_t actor) {
    if (!defjam_fighter_graph_has(ordinal)) return 0;
    const GraphProof *proof=&s_graphs[ordinal-GRAPH_FIRST];const uint8_t *p=proof->record;
    if (!proof->bank || actor<0x3B92E0 || actor-0x3B92E0>=4*0x12E8 || (actor-0x3B92E0)%0x12E8) return 0;
    uint32_t slot=(actor-0x3B92E0)/0x12E8;
    uint32_t visual=guest_call(sub_000441C0,0,1,&slot);
    if (!visual) return 0;
    int created=(MEM8(visual+0xABB4)&1)!=0;
    uint32_t model=created?MEM32(visual+0x9D0):visual+0x30;
    if (!model || !(MEM8(model+0x138)&1) || MEM8(model+0x158)!=1) return 0;
    uint32_t skeleton=MEM32(model+0x144),bones=word(p+52),rigs=word(p+56),relocs=word(p+12);
    if (!skeleton || skeleton>UINT32_MAX-(16+112*bones) || MEM32(skeleton)!=0x03AC3F23
        || MEM32(skeleton+4) || MEM32(skeleton+8)!=bones || MEM32(skeleton+12)
        || MEM32(model+0x15C)!=bones || MEM32(model+0x16C)!=skeleton
        || !MEM32(model+0x14C) || !MEM32(model+0x150) || !MEM32(model+0x154)) return 0;
    Sha sha;sha_init(&sha);sha_update(&sha,(const void *)XBOX_PTR(skeleton),16+112*bones);
    uint8_t digest[32];sha_final(&sha,digest);int found=0;
    for (uint32_t i=0;i<rigs;++i) if (!memcmp(digest,p+92+8*relocs+32*i,32)) { found=1;break; }
    uint32_t face=visual+(created?0xA6B0:0x450),hands=MEM32(visual+0xABB8);
    uint32_t face_need[2]={word(p+36),word(p+40)},hand_need[2]={word(p+44),word(p+48)};
    if (!found || !defjam_fighter_palette_check(face,MEM32(face),bones,face_need)
        || !hands || !defjam_fighter_palette_check(hands,MEM32(hands),bones,hand_need)) return 0;
    if (++s_context_logs<=128) fprintf(stderr,"[FIGHTERS] graph context verified ordinal=%u actor=%u created=%d bones=%u face=%08X hands=%08X\n",
                                      ordinal,slot,created,bones,MEM32(face),MEM32(hands));
    return 1;
}
void defjam_fighter_graph_release(void) {
    for (unsigned i=0;i<GRAPH_LIMIT;++i) s_graphs[i].bank=0;
    s_context_logs=s_seal_logs=0;
}
