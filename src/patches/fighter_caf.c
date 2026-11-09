/* Retail CAF recipe adapter. Own-dump resources, original assembly and cleanup.
 * No profile import: compiler-owned records contain selections/training only. */
#include "fighter_caf.h"
#include "fighter_motion.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CAF_ROW 232u
#define CAF_MAX 16384u
static uint8_t *s_rows;
static uint32_t s_count;
static uint32_t s_profile_workspace;
static uint32_t s_contexts[4];
static uint32_t s_service;
static const uint8_t *s_recipes[4];
extern void sub_00063720(void), sub_00062850(void);
extern void sub_00062A00(void), sub_00063770(void);
extern void sub_00064170(void), sub_0001EE80(void), sub_000296B0(void), sub_0003E170_gen(void);
static uint32_t word(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void stop(const char *why) { fprintf(stderr,"[FIGHTERS] CAF stopped: %s\n",why);fflush(stderr);exit(1); }
int defjam_fighter_caf_start(void) {
    const char *path=getenv("RECOMP_FIGHTER_CAF"),*hash=getenv("RECOMP_FIGHTER_CAF_SHA256");
    if (!path || !*path) return !hash || !*hash;
    if (!mod_file_matches(path,hash) || s_rows) return 0;
    FILE *file;
#if defined(_WIN32)
    wchar_t wide[2048];if (!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,2048)) return 0;
    file=_wfopen(wide,L"rb");
#else
    file=fopen(path,"rb");
#endif
    if (!file) return 0;
    size_t maximum=16+CAF_MAX*CAF_ROW;
    uint8_t *data=(uint8_t *)malloc(maximum+1);
    if (!data) {fclose(file);return 0;}
    size_t size=fread(data,1,maximum+1,file);int valid=!ferror(file);fclose(file);
    uint32_t count=size>=16?word(data+8):0;
    valid=valid && size>=16 && !memcmp(data,"FCA1",4) && word(data+4)==1 && word(data+12)==CAF_ROW
        && count && count<=CAF_MAX && size==16+(size_t)count*CAF_ROW;
    for (uint32_t i=0;valid && i<count;++i) {
        const uint8_t *row=data+16+i*CAF_ROW;
        valid=word(row)>=100 && word(row+4)>=87 && word(row+4)<=141 && word(row+28)>=1 && word(row+28)<=3
            && word(row+32)<6 && word(row+36)<=36 && word(row+52)>=1 && word(row+52)<=8;
        for (unsigned j=0;j<5;++j) if (word(row+8+j*4)>50) valid=0;
        for (unsigned j=0;j<3;++j) if (row[222+j]!=(j<word(row+28)?row[222+j]:255) || (j<word(row+28)&&row[222+j]>4)) valid=0;
        for (uint32_t j=0;j<i;++j) if (word(data+16+j*CAF_ROW)==word(row)) valid=0;
        for (unsigned j=225;j<228;++j) if(row[j]) valid=0;
        if(word(row+228)<1 || word(row+228)>86) valid=0;
    }
    if (!valid) {free(data);return 0;}
    s_rows=data;s_count=count;fprintf(stderr,"[FIGHTERS] validated %u CAF recipes\n",count);return 1;
}
/* Called before each match/after it finishes: no stale context may be reused. */
void defjam_fighter_caf_clear(void) {
    s_service=0;
    for(unsigned i=0;i<4;++i) {s_contexts[i]=0;s_recipes[i]=NULL;}
}
static uint32_t prepare_profile(const uint8_t *row) {
    if(!s_profile_workspace) {
        uint32_t args[]={0x5c000,0x298908,0x100};
        s_profile_workspace=guest_call(sub_000296B0,0,3,args);
        if(!s_profile_workspace) stop("profile scratch allocation failed");
        memset((void *)XBOX_PTR(s_profile_workspace),0,0x5c000);
    }
    uint32_t profile=s_profile_workspace+0x177c,values=profile+0x5564,colors=profile+0x55fc;
    memset((void *)XBOX_PTR(profile),0,0x5920);
    memcpy((void *)XBOX_PTR(values),row+32,152);memcpy((void *)XBOX_PTR(colors),row+184,38);
    MEM32(profile+0x5910)=values;MEM32(profile+0x5914)=colors;
    for(unsigned j=0;j<5;++j) MEM32(profile+0xfc+j*4)=word(row+8+j*4);
    /* Original style bonuses, no Story accomplishment bonuses or currency. */
    static const uint8_t bonuses[5][6]={{2,0,0,1,0,0},{0,2,1,0,0,0},{0,1,0,0,2,0},{1,0,0,2,0,0},{0,0,2,0,1,0}};
    for(unsigned j=0;j<word(row+28);++j) for(unsigned k=0;k<6;++k) MEM32(profile+0x114+k*4)+=bonuses[row[222+j]][k];
    return profile;
}
void defjam_fighter_caf_participant(uint32_t service,uint32_t participant,uint32_t selection) {
    const uint8_t *row=NULL;
    for(uint32_t i=0;i<s_count;++i) if(word(s_rows+16+i*CAF_ROW)==selection) row=s_rows+16+i*CAF_ROW;
    if(!row) return;
    if(participant>=4 || !MEM32(service+0x1A9C)) stop("native CAF contexts are unavailable");
    /* Original service owns four 0x1c contexts and destroys each through63770.
     * Use that same lifetime; never borrow another player's profile object. */
    uint32_t contexts=MEM32(service+0x1A9C);
    if(MEM32(contexts-4)!=4 || (s_service && s_service!=service)) stop("native CAF context owner differs");
    s_service=service;
    uint32_t context=contexts+participant*0x1c;
    if(MEM8(context)) guest_call(sub_00063770,context,0,NULL);
    /* 62960 installs the single-preview 1.5 MiB arena. Match CAFs use
     * the existing normal game allocators, as 62A00 supports natively. */
    uint32_t resource_manager=guest_call(sub_00063720,0,0,NULL),load_args[]={0x400};
    guest_call(sub_00062850,resource_manager,1,load_args);
    guest_call(sub_00062A00,context,0,NULL);
    s_contexts[participant]=context;s_recipes[participant]=row;
    uint32_t args[]={prepare_profile(row)};
    guest_call(sub_00064170,context,1,args);
    if(!MEM8(context+1)||!MEM32(context+8)) stop("native CAF construction did not complete");
    uint32_t old_manager=MEM32(service+4),old_mode=MEM32(service+0x344);
    MEM32(service+4)=s_profile_workspace;MEM32(service+0x344)=0;MEM32(s_profile_workspace+0x5ac7c)=0;
    uint32_t stats_args[]={participant};guest_call(sub_0001EE80,service,1,stats_args);
    MEM32(service+4)=old_manager;MEM32(service+0x344)=old_mode;
    MEM8(service+0x1e8+participant)=(uint8_t)(participant+1);
    MEM32(service+0x168+participant*4)=word(row+4);
    fprintf(stderr,"[FIGHTERS] CAF prepared participant=%u logical=%u core=%u context=%08X visual=%08X build=%u face=%u\n",
        participant,selection,word(row+4),context,MEM32(context+8),word(row+32),word(row+52));
}

/* Original Battle lookup1E410 translates a participant through its signed-in
 * Story profile index. A standalone CPU has none: bind our exact live context
 * by participant, leaving native Story and retail lookups unchanged. */
int defjam_fighter_caf_context(uint32_t service,uint32_t participant,uint32_t *output) {
    if(service!=s_service || participant>=4 || !s_contexts[participant]) return 0;
    uint32_t context=s_contexts[participant];
    if(context!=MEM32(service+0x1a9c)+participant*0x1c || !MEM8(context) || !MEM8(context+1) || !MEM32(context+8))
        stop("CAF participant context is no longer valid");
    *output=context;return 1;
}

/* The original match loader initializes the same native visual again, then
 * reads assets/cp/cp_def<slot>.xml (debug preset). A standalone recipe replaces
 * only those two operations for its exact live context. Original Story CAFs
 * and every retail/owned visual retain their original implementations. */
int defjam_fighter_caf_visual(uint32_t visual, uint32_t participant, int apply) {
    for(unsigned i=0;i<4;++i) {
        uint32_t context=s_contexts[i];
        if(!context || !MEM8(context) || !s_recipes[i] || MEM32(context+8)+0x8b0!=visual) continue;
        if(apply) {
            if(participant!=i) stop("CAF participant/context differs");
            if(!MEM8(context+1)) stop("CAF visual was not assembled before match loading");
            fprintf(stderr,"[FIGHTERS] CAF assembled participant=%u logical=%u core=%u visual=%08X build=%u face=%u\n",
                i,word(s_recipes[i]),word(s_recipes[i]+4),visual,word(s_recipes[i]+32),word(s_recipes[i]+52));
        }
        return 1;
    }
    return 0;
}

void defjam_fighter_caf_decode_trace(uint32_t output,uint32_t source,uint32_t caller,int done) {
    static int checked,enabled;static unsigned count;
    if(!checked) {checked=1;enabled=getenv("RECOMP_FIGHTER_CAF_TRACE")!=NULL;}
    if(!enabled || !s_count) return;
    if(!done) ++count;
    if(count<=32 || !(count&(count-1))) {
        fprintf(stderr,"[CAF-TRACE] decode %s n=%u out=%08X source=%08X caller=%08X sp=%08X cursor=%u:%u\n",
            done?"end":"begin",count,output,source,caller,g_esp,MEM32(0x3BE108),MEM32(0x3BE104));
        uint32_t actor=0x3B92E0;
        fprintf(stderr,"[CAF-TRACE] actor core=%u state=%u mode=%u motion=%u ordinal=%u time=%g remaining=%g length=%g\n",
            MEM32(actor+0x2c),MEM32(actor+0x30),MEM32(actor+0x84),MEM32(actor+0x88),MEM32(actor+0x8c),
            MEMF(actor+0x9c),MEMF(actor+0xa0),MEMF(actor+0xa4));fflush(stderr);
    }
}

/* Native CAF motion rows do not supply standalone speech streams. Original
 * Story CAFs choose a voice from their profile instead. Bind our declared
 * retail voice donor on a nested audio-setup value; never rewrite actor cores. */
int defjam_fighter_caf_audio(uint32_t input) {
    if(MEM8(0x340540)) return 0; /* Native early-out may not supply a new setup. */
    int changed=0;
    for(unsigned i=0;i<4;++i) if(s_recipes[i]) {
        if(MEM32(input+0x20+i*0x18)!=word(s_recipes[i]+4)) stop("CAF audio core differs from participant");
        changed=1;
    }
    if(!changed) return 0;
    uint32_t stack=g_esp;
    if(stack<0x1090) stop("invalid CAF audio adapter stack");
    g_esp-=0x90;uint32_t copy=g_esp;
    memcpy((void *)XBOX_PTR(copy),(const void *)XBOX_PTR(input),0x84);
    for(unsigned i=0;i<4;++i) if(s_recipes[i]) MEM32(copy+0x20+i*0x18)=word(s_recipes[i]+228);
    /* A mixed match also needs owned motion cores translated on this copy.
     * Both adapters are synchronous; native setup runs once and the wrapper
     * restores owned voice IDs using the untouched original participant rows. */
    if(!defjam_fighter_motion_audio(copy)) g_eax=guest_call(sub_0003E170_gen,g_ecx,1,&copy);
    g_esp=stack+4;
    fprintf(stderr,"[FIGHTERS] CAF inherited audio templates %u/%u/%u/%u\n",
        MEM32(copy+0x20),MEM32(copy+0x38),MEM32(copy+0x50),MEM32(copy+0x68));
    return 1;
}
