/* Retail CAF recipe adapter. Own-dump resources, original assembly and cleanup.
 * No profile import: compiler-owned records contain selections/training only. */
#include "fighter_caf.h"
#include "fighter_motion.h"
#include "fighter_caf_face.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CAF_ROW 232u
#define CAF_MAX 16384u
#define EXTRA_ROW 48u
#define ATLAS_BYTES (256u*256u*4u)
#define EXTRA_MAX (16u*1024u*1024u)
static uint32_t s_row_stride=CAF_ROW,s_extra_stride=EXTRA_ROW;
static uint32_t s_menu_selection[4],s_menu_outfit[4];
static uint8_t *s_extras;
static uint32_t s_extra_count;
static uint8_t *s_rows;
static uint32_t s_count;
static uint32_t s_profile_workspace;
static uint32_t s_contexts[4];
static uint32_t s_service;
static const uint8_t *s_recipes[4];
static uint8_t s_story_rows[4][240];
static uint32_t s_story_profiles[4];
static uint32_t s_finisher_before[4][4],s_finisher_applied[4][4];
static uint8_t s_finisher_live[4];
extern void sub_00063720(void), sub_00062850(void);
extern void sub_00062A00(void), sub_00063770(void);
extern void sub_00064170(void), sub_0001EE80(void), sub_000296B0(void), sub_0003E170_gen(void);
extern void sub_00092BE0(void), sub_001DE887(void), sub_00098270(void);
extern void sub_0001E8F0(void);
extern void sub_0001E410_gen(void);
static uint32_t word(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void stop(const char *why) { fprintf(stderr,"[FIGHTERS] CAF stopped: %s\n",why);fflush(stderr);exit(1); }
static uint32_t row_outfit(const uint8_t *row) { return s_row_stride==240u?word(row+232):0; }
static const uint8_t *recipe_row(uint32_t selection,uint32_t outfit) {
    for(uint32_t i=0;i<s_count;++i) {
        const uint8_t *row=s_rows+16+i*s_row_stride;
        if(word(row)==selection && row_outfit(row)==outfit) return row;
    }
    return NULL;
}
void defjam_fighter_caf_menu_clear(uint32_t participant) {
    for(unsigned i=0;i<4;++i) if(participant==UINT32_MAX || participant==i) {s_menu_selection[i]=0;s_menu_outfit[i]=0;}
}
int defjam_fighter_caf_outfit(uint32_t participant,uint32_t selection,uint32_t outfit) {
    if(participant>=4 || !recipe_row(selection,outfit)) return 0;
    s_menu_selection[participant]=selection;s_menu_outfit[participant]=outfit;
    fprintf(stderr,"[FIGHTERS] outfit participant=%u logical=%u index=%u\n",participant,selection,outfit);
    return 1;
}
uint32_t defjam_fighter_caf_presentation(uint32_t participant,uint32_t selection) {
    uint32_t index=participant<4 && s_menu_selection[participant]==selection?s_menu_outfit[participant]:0;
    const uint8_t *row=recipe_row(selection,index);
    return row && s_row_stride==240u?word(row+236):selection;
}
static int extras_valid(const uint8_t *data,size_t size) {
    uint32_t count=size>=16?word(data+8):0;
    uint32_t stride=size>=16?word(data+12):0;
    int extended=size>=16 && !memcmp(data,"FCX2",4) && word(data+4)==2 && stride==52;
    if(size<16 || size>EXTRA_MAX || (!extended && (memcmp(data,"FCX1",4) || word(data+4)!=1 || stride!=EXTRA_ROW))
        || !count || count>(extended?CAF_MAX*3:CAF_MAX)) return 0;
    size_t base=16+(size_t)count*stride;
    if(base>size || (size-base)%ATLAS_BYTES) return 0;
    size_t blocks=(size-base)/ATLAS_BYTES;
    if(blocks>64) return 0;
    uint8_t used[64]={0};
    for(uint32_t i=0;i<count;++i) {
        const uint8_t *row=data+16+i*stride;
        uint32_t index=extended?word(row+48):0;
        if(!recipe_row(word(row),index) || word(row+4)>1) return 0;
        for(uint32_t j=0;j<i;++j) {
            const uint8_t *before=data+16+j*stride;
            if(word(before)==word(row) && (!extended || word(before+48)==index)) return 0;
            if(word(before)==word(row) && memcmp(before+4,row+4,20)) return 0;
        }
        for(unsigned j=0;j<4;++j) if(word(row+8+j*4)>81 || (!word(row+4)&&word(row+8+j*4))) return 0;
        for(unsigned j=0;j<6;++j) {
            uint32_t offset=word(row+24+j*4);
            if(!offset) continue;
            if(offset<base || (offset-base)%ATLAS_BYTES || offset>size || ATLAS_BYTES>size-offset) return 0;
            size_t block=(offset-base)/ATLAS_BYTES;
            if(block>=blocks) return 0;
            used[block]=1;
        }
    }
    for(size_t i=0;i<blocks;++i) if(!used[i]) return 0;
    return 1;
}
static int extras_start(void) {
    const char *path=getenv("RECOMP_FIGHTER_CAF_EXTRAS"),*hash=getenv("RECOMP_FIGHTER_CAF_EXTRAS_SHA256");
    if(!path || !*path) return !hash || !*hash;
    if(!mod_file_matches(path,hash) || s_extras) return 0;
    FILE *file;
#if defined(_WIN32)
    wchar_t wide[2048];if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,2048)) return 0;
    file=_wfopen(wide,L"rb");
#else
    file=fopen(path,"rb");
#endif
    if(!file) return 0;
    uint8_t *data=(uint8_t *)malloc(EXTRA_MAX+1);
    if(!data) {fclose(file);return 0;}
    size_t size=fread(data,1,EXTRA_MAX+1,file);int valid=!ferror(file);fclose(file);
    if(!valid || !extras_valid(data,size)) {free(data);return 0;}
    s_extras=data;s_extra_count=word(data+8);s_extra_stride=word(data+12);
    fprintf(stderr,"[FIGHTERS] validated %u CAF extras (%zu bytes)\n",s_extra_count,size);return 1;
}
static const uint8_t *extra_row(uint32_t selection,uint32_t outfit) {
    for(uint32_t i=0;i<s_extra_count;++i) {
        const uint8_t *row=s_extras+16+i*s_extra_stride;
        if(word(row)==selection && (s_extra_stride==52?word(row+48):0)==outfit) return row;
    }
    return NULL;
}
static int guest_span(uint32_t pointer,uint32_t bytes) {
    uint32_t offset=pointer>=0x80000000u?pointer-0x80000000u:pointer;
    return offset>=0x10000u && offset<0x4000000u && bytes<=0x4000000u-offset;
}
static uint32_t swizzle8(uint32_t value) {
    value=(value|(value<<4))&0x0F0Fu;
    value=(value|(value<<2))&0x3333u;
    return (value|(value<<1))&0x5555u;
}
static void apply_atlases(uint32_t visual,const uint8_t *extra) {
    if(!extra) return;
    uint32_t originals[6]={0},changed=0;
    for(unsigned atlas=0;atlas<6;++atlas) {
        uint32_t offset=word(extra+24+atlas*4);
        if(!offset) continue;
        uint32_t original=MEM32(visual+0xA234+atlas*4);
        if(!guest_span(original,16) || MEM16(original+4)!=256 || MEM16(original+6)!=256)
            stop("declared atlas has no original 256x256 native bitmap");
        /* 92BE0 makes the same owned 32-bit bitmap used by the retail
         * compositor. Borrowed base resources at A24C remain immutable. */
        uint32_t args[]={original,0x7D},bitmap=guest_call(sub_00092BE0,0,2,args);
        if(!guest_span(bitmap,16) || bitmap==original || MEM8(bitmap)!=0x7D
            || MEM16(bitmap+4)!=256 || MEM16(bitmap+6)!=256) stop("native RGBA atlas conversion failed");
        uint32_t pixels=bitmap+16;
        if(MEM32(bitmap+12)&0x1000u) pixels=bitmap+MEM32(bitmap+16);
        if(!guest_span(pixels,ATLAS_BYTES)) stop("native atlas pixels exceed guest memory");
        uint8_t *target=(uint8_t *)XBOX_PTR(pixels);
        const uint8_t *source=s_extras+offset;
        for(uint32_t pixel=0;pixel<256u*256u;++pixel) {
            /* Native conversion retains the FSH 0x2000 Morton layout flag.
             * PNG rows are linear. Keep alpha at its original native address. */
            uint32_t destination=(MEM32(bitmap+12)&0x2000u)
                ? swizzle8(pixel&255u)|(swizzle8(pixel>>8)<<1) : pixel;
            memcpy(target+destination*4,source+pixel*4,3);
        }
        originals[atlas]=original;MEM32(visual+0xA234+atlas*4)=bitmap;++changed;
        fprintf(stderr,"[FIGHTERS] CAF RGB atlas logical=%u slot=%u bitmap=%08X original-alpha=held\n",word(extra),atlas,bitmap);
    }
    if(!changed) return;
    /* Rebind cp_a..cp_d after replacing this visual's bitmap pointers, before
     * any frame uses it. This is context-local, never a global hash override. */
    guest_call(sub_00098270,visual,0,NULL);
    for(unsigned atlas=0;atlas<6;++atlas) if(originals[atlas] && originals[atlas]!=MEM32(visual+0xA24C+atlas*4)) {
        uint32_t args[]={originals[atlas]};guest_call(sub_001DE887,0,1,args);
    }
}
/* Restore only our last write. A native profile initializer may already own
 * this matrix again; never overwrite values it has installed since then. */
static void restore_finishers(void) {
    for(unsigned slot=0;slot<4;++slot) if(s_finisher_live[slot]) {
        int owned=1;
        for(unsigned i=0;i<4;++i) if(MEM32(0x3B9288u+slot*16+i*4)!=s_finisher_applied[slot][i]) owned=0;
        if(owned) for(unsigned i=0;i<4;++i) MEM32(0x3B9288u+slot*16+i*4)=s_finisher_before[slot][i];
        s_finisher_live[slot]=0;
    }
}
void defjam_fighter_caf_finishers(void) {
    for(unsigned slot=0;slot<4;++slot) {
        if(!s_recipes[slot] || !s_contexts[slot]) continue;
        const uint8_t *extra=extra_row(word(s_recipes[slot]),row_outfit(s_recipes[slot]));
        int story=s_story_profiles[slot]!=0;
        if(!story && (!extra || !word(extra+4))) continue;
        uint32_t context;
        if(story) {
            context=s_contexts[slot];
            if(!MEM8(context) || !MEM8(context+1) || !MEM32(context+8))stop("Story CAF context was not assembled by its native loader");
        } else if(!s_service || !defjam_fighter_caf_context(s_service,slot,&context))
            stop("finisher CAF context is no longer active");
        uint32_t actor=0x3B92E0u+slot*0x12E8u;
        if(MEM32(actor+0x28)==UINT32_MAX || MEM32(actor+0x2C)+1!=word(s_recipes[slot]+4))
            stop("finisher actor differs from its CAF participant");
        int owned=s_finisher_live[slot];uint32_t choices[4];
        for(unsigned i=0;i<4;++i) if(MEM32(0x3B9288u+slot*16+i*4)!=s_finisher_applied[slot][i]) owned=0;
        for(unsigned choice=0;choice<4;++choice) {
            uint32_t address=0x3B9288u+slot*16+choice*4;
            uint32_t value=story?MEM32(address):word(extra+8+choice*4);
            if(value>=82)stop("CAF finisher choice exceeds the original move pool");
            choices[choice]=value;
            if(!story) {
                if(!owned) s_finisher_before[slot][choice]=MEM32(address);
                s_finisher_applied[slot][choice]=value;
                MEM32(address)=value;
            }
            /* Original 1A8180 copies the profile matrix only for CAF cores.
             * Retail motion cores still need the CAF's four chosen moves. */
            MEM32(actor+0xbb8+choice*4)=value;
        }
        if(!story)s_finisher_live[slot]=1;
        fprintf(stderr,"[FIGHTERS] CAF finisher choices slot=%u: %u,%u,%u,%u\n",slot,
            choices[0],choices[1],choices[2],choices[3]);
        if(story) {
            /* Actor/WPAR initialization has consumed the requested retail core.
             * Subsequent model/intro/presentation gates still identify this as
             * the player's CAF. Keep that config identity independent of the
             * live actor's motion core and the saved Battle moveset byte. */
            MEM32(s_service+0x168+slot*4)=word(s_recipes[slot]+228);
            fprintf(stderr,"[FIGHTERS] Story CAF presentation participant=%u career=%u motion=%u\n",slot,word(s_recipes[slot]+228),MEM32(actor+0x2c)+1);
        }
    }
}
static int recipes_valid(const uint8_t *data,size_t size) {
    uint32_t count=size>=16?word(data+8):0;
    uint32_t stride=size>=16?word(data+12):0;
    int retail=size>=16 && !memcmp(data,"FCA3",4) && word(data+4)==3 && stride==240;
    int extended=retail || (size>=16 && !memcmp(data,"FCA2",4) && word(data+4)==2 && stride==240);
    int valid=size>=16 && (extended || (!memcmp(data,"FCA1",4) && word(data+4)==1 && stride==CAF_ROW))
        && count && count<=(extended?CAF_MAX*3:CAF_MAX) && size==16+(size_t)count*stride;
    for (uint32_t i=0;valid && i<count;++i) {
        const uint8_t *row=data+16+i*stride;
        valid=word(row)>=100 && (retail&&row[225]==1?(word(row+4)>=1&&word(row+4)<=86):(word(row+4)>=87&&word(row+4)<=141)) && word(row+28)>=1 && word(row+28)<=3
            && word(row+32)<6 && word(row+36)<=36 && word(row+52)>=1 && word(row+52)<=8;
        for (unsigned j=0;j<5;++j) if (word(row+8+j*4)>50) valid=0;
        for (unsigned j=0;j<3;++j) if (row[222+j]!=(j<word(row+28)?row[222+j]:255) || (j<word(row+28)&&row[222+j]>4)) valid=0;
        uint32_t index=extended?word(row+232):0,previous=UINT32_MAX;
        if(index>2 || (extended && (word(row+236)<100 || word(row+236)>0x7FFFFFFEu || (!index && word(row+236)!=word(row))))) valid=0;
        for (uint32_t j=0;j<i;++j) {
            const uint8_t *before=data+16+j*stride;
            if(extended && word(before+236)==word(row+236)) valid=0;
            if(word(before)==word(row)) {
                uint32_t old_index=extended?word(before+232):0;
                if(!extended || old_index>=index || memcmp(before+4,row+4,28) || memcmp(before+222,row+222,10)) valid=0;
                previous=old_index;
            }
        }
        if(index && previous!=index-1) valid=0;
        if(row[225]>(retail?1:0) || row[226] || row[227]) valid=0;
        if(word(row+228)<1 || word(row+228)>86) valid=0;
    }
    return valid;
}
int defjam_fighter_caf_start(void) {
    const char *path=getenv("RECOMP_FIGHTER_CAF"),*hash=getenv("RECOMP_FIGHTER_CAF_SHA256");
    if (!path || !*path) return (!hash || !*hash) && !getenv("RECOMP_FIGHTER_CAF_EXTRAS") && !getenv("RECOMP_FIGHTER_CAF_EXTRAS_SHA256") && !getenv("RECOMP_FIGHTER_CAF_FACES") && !getenv("RECOMP_FIGHTER_CAF_FACES_SHA256");
    if (!mod_file_matches(path,hash) || s_rows) return 0;
    FILE *file;
#if defined(_WIN32)
    wchar_t wide[2048];if (!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,2048)) return 0;
    file=_wfopen(wide,L"rb");
#else
    file=fopen(path,"rb");
#endif
    if (!file) return 0;
    size_t maximum=16+CAF_MAX*3u*240u;
    uint8_t *data=(uint8_t *)malloc(maximum+1);
    if (!data) {fclose(file);return 0;}
    size_t size=fread(data,1,maximum+1,file);int valid=!ferror(file);fclose(file);
    valid=valid && recipes_valid(data,size);
    uint32_t count=valid?word(data+8):0,stride=valid?word(data+12):0;
    if (!valid) {free(data);return 0;}
    s_rows=data;s_count=count;s_row_stride=stride;
    if(!extras_start()) {free(s_rows);s_rows=NULL;s_count=0;return 0;}
    if(!defjam_caf_faces_start(recipe_row)) return 0;
    fprintf(stderr,"[FIGHTERS] validated %u CAF recipes\n",count);return 1;
}
/* Called before each match/after it finishes: no stale context may be reused. */
void defjam_fighter_caf_clear(void) {
    defjam_caf_faces_clear();
    restore_finishers();
    for(unsigned i=0;i<4;++i) if(s_story_profiles[i] && s_service && s_recipes[i]
        && MEM32(s_service+0x168+i*4)==word(s_recipes[i]+228))
        MEM32(s_service+0x168+i*4)=word(s_recipes[i]+4);
    s_service=0;
    for(unsigned i=0;i<4;++i) {s_contexts[i]=0;s_recipes[i]=NULL;}
    memset(s_story_profiles,0,sizeof(s_story_profiles));
}
void defjam_fighter_caf_begin_match(void) {
    /* Original setup already published its new config. Do not restore an old
     * Story journal over an equal career core now owned by a new participant. */
    memset(s_story_profiles,0,sizeof(s_story_profiles));
    defjam_fighter_caf_clear();
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
/* Read-only diagnostics for the original per-CAF deform buffers. Never edits
 * archive geometry; used to qualify the custom-face ownership boundary. */
static void face_trace(uint32_t visual,uint32_t participant) {
    if(!getenv("RECOMP_FIGHTER_FACE_TRACE")) return;
    uint32_t part=visual+0x140+2u*0x420,model=MEM32(part+0x12c);
    if(model<0x10000 || model>0xfffe0000u) {fprintf(stderr,"[CAF-FACE] missing head model\n");return;}
    uint32_t group=MEM32(model+0xb8)+4;
    fprintf(stderr,"[CAF-FACE] participant=%u part=%08X model=%08X groups=%08X frame=%u morph=%08X\n",participant,part,model,group,MEM32(model+0xc0),MEM32(model+0xd4));
    for(unsigned channel=0;channel<16 && group>=0x10000 && group<0xfffe0000u;++channel) {
        uint32_t name=MEM32(group),count=MEM32(group+4);
        if(!name) break;
        if(name<0x10000 || name>0xfffe0000u || count>64) break;
        fprintf(stderr,"[CAF-FACE] channel=%u name=%.32s rows=%u\n",channel,(const char *)XBOX_PTR(name),count);
        for(uint32_t i=0;i<count;++i) {
            uint32_t at=group+8+16*i;
            fprintf(stderr,"[CAF-FACE] buffer=%u rm=%u vertices=%u encoding=%u stride=%u data=%08X\n",i,MEM32(at),MEM16(at+4),MEM16(at+6),MEM32(at+8),MEM32(at+12));
        }
        group+=8+16*count;
    }
}
static uint32_t construct_caf(uint32_t service,uint32_t participant,const uint8_t *row,uint32_t profile) {
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
    uint32_t args[]={profile};
    guest_call(sub_00064170,context,1,args);
    if(!MEM8(context+1)||!MEM32(context+8)) stop("native CAF construction did not complete");
    return context;
}
void defjam_fighter_caf_story(uint32_t service,uint32_t fighters) {
    /* A profile-owned fighter retains the original loader and its event timing.
     * Only track its context/voice/finishers for retail motion compatibility;
     * never preassemble or replace the player's real profile object. */
    uint32_t manager=MEM32(service+4),mode=MEM32(service+0x344);
    uint32_t game=MEM32(service);
    for(uint32_t slot=0;slot<4;++slot) {
        uint32_t core=MEM32(service+0x168+slot*4);
        int created=mode==1 ? MEM8(service+0x1aaa+slot*5)==99
            : mode==0 && MEM32(game+0x14)==slot && MEM8(game+0x18);
        if(!created || MEM32(fighters+slot*4)==UINT32_MAX || core<1 || core>86)continue;
        int32_t index=-1;
        if(mode==0 && guest_span(manager,0x5ac80))index=(int32_t)MEM32(manager+0x5ac7c);
        else if(mode==1)index=(int8_t)guest_call(sub_0001E8F0,service,1,&slot);
        if(index<0 || index>=16)stop("Story CAF retail moveset has no signed-in profile");
        uint32_t profile=manager+0x177c+(uint32_t)index*0x5950;
        if(!guest_span(profile,0x5950) || MEM8(profile+0x143)!=core || MEM8(profile+0x4d93)<87 || MEM8(profile+0x4d93)>141)
            stop("Story CAF retail moveset profile differs from its preserved career");
        uint8_t *row=s_story_rows[slot];memset(row,0,240);
        uint32_t value=99;memcpy(row,&value,4);memcpy(row+4,&core,4);
        memcpy(row+8,(const void *)XBOX_PTR(profile+0xfc),20);
        memcpy(row+32,(const void *)XBOX_PTR(profile+0x5564),152);
        memcpy(row+184,(const void *)XBOX_PTR(profile+0x55fc),38);
        uint32_t count=0;
        for(unsigned i=0;i<3;++i) {uint8_t style=MEM8(profile+0x140+i);row[222+i]=style;if(style!=255){if(style>4)stop("Story CAF style slots are unsupported");++count;}}
        if(!count)stop("Story CAF has no preserved style combination");
        memcpy(row+28,&count,4);
        value=MEM8(profile+0x4d93);memcpy(row+228,&value,4); /* Original profile voice route. */
        s_story_profiles[slot]=profile;
        uint32_t context=guest_call(sub_0001E410_gen,service,1,&slot);
        if(!guest_span(context,0x1c))stop("Story CAF has no native context");
        if(s_service && s_service!=service)stop("Story CAF context owner differs");
        s_service=service;s_contexts[slot]=context;s_recipes[slot]=row;
        fprintf(stderr,"[FIGHTERS] Story CAF retail moveset participant=%u core=%u profile=%08X context=%08X career=%u\n",slot,core,profile,context,value);
    }
}
void defjam_fighter_caf_participant(uint32_t service,uint32_t participant,uint32_t selection) {
    uint32_t outfit=participant<4 && s_menu_selection[participant]==selection?s_menu_outfit[participant]:0;
    const uint8_t *row=recipe_row(selection,outfit);
    if(!row) return;
    if(recipe_row(selection,1) && (participant>=4 || s_menu_selection[participant]!=selection)) stop("multi-outfit CAF was not confirmed by its participant");
    uint32_t context=construct_caf(service,participant,row,prepare_profile(row));
    defjam_caf_faces_apply(MEM32(context+8)+0x8B0,participant,selection,outfit,row);
    face_trace(MEM32(context+8)+0x8B0,participant);
    apply_atlases(MEM32(context+8)+0x8B0,extra_row(selection,outfit));
    uint32_t old_manager=MEM32(service+4),old_mode=MEM32(service+0x344);
    MEM32(service+4)=s_profile_workspace;MEM32(service+0x344)=0;MEM32(s_profile_workspace+0x5ac7c)=0;
    uint32_t stats_args[]={participant};guest_call(sub_0001EE80,service,1,stats_args);
    MEM32(service+4)=old_manager;MEM32(service+0x344)=old_mode;
    MEM8(service+0x1e8+participant)=(uint8_t)(participant+1);
    MEM32(service+0x168+participant*4)=word(row+4);
    fprintf(stderr,"[FIGHTERS] CAF prepared participant=%u logical=%u core=%u context=%08X visual=%08X build=%u face=%u\n",
        participant,selection,word(row+4),context,MEM32(context+8),word(row+32),word(row+52));
    fprintf(stderr,"[FIGHTERS] CAF appearance participant=%u logical=%u outfit=%u portrait=%u\n",participant,selection,outfit,defjam_fighter_caf_presentation(participant,selection));
}

/* Original Battle lookup1E410 translates a participant through its signed-in
 * Story profile index. A standalone CPU has none: bind our exact live context
 * by participant, leaving native Story and retail lookups unchanged. */
int defjam_fighter_caf_context(uint32_t service,uint32_t participant,uint32_t *output) {
    if(service!=s_service || participant>=4 || !s_contexts[participant]) return 0;
    if(s_story_profiles[participant])return 0; /* Original profile lookup/assembly owns this path. */
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
        if(s_story_profiles[i] || !context || !MEM8(context) || !s_recipes[i] || MEM32(context+8)+0x8b0!=visual) continue;
        if(apply) {
            if(participant!=i) stop("CAF participant/context differs");
            if(!MEM8(context+1)) stop("CAF visual was not assembled before match loading");
            face_trace(visual,participant);
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
    if(!enabled || !s_service) return;
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
        uint32_t core=MEM32(input+0x20+i*0x18);
        if(core!=word(s_recipes[i]+4) && (!s_story_profiles[i] || core!=word(s_recipes[i]+228))) stop("CAF audio core differs from participant");
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
