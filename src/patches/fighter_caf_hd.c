/* Versioned, sealed HD CAF RGB. Original native bitmaps and guest allocation
 * sizes stay unchanged; host replacements are owned by each live visual. */
#include "fighter_caf_hd.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include "texture_pack.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define HD_MAX (128u*1024u*1024u)
#define HD_ROW 32u
static uint8_t *s_hd;
static uint32_t s_hd_count,s_hd_owners[4];
static uint32_t hd_word(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void hd_stop(const char *why) {fprintf(stderr,"[FIGHTERS] HD CAF stopped: %s\n",why);fflush(stderr);exit(1);}
static int hd_valid(const uint8_t *data,size_t size,const uint8_t *(*recipe)(uint32_t,uint32_t)) {
    if(size<16 || size>HD_MAX || memcmp(data,"FCH1",4) || hd_word(data+4)!=1 || hd_word(data+12)!=HD_ROW) return 0;
    uint32_t count=hd_word(data+8),offsets[128],blocks=0;uint8_t used[128]={0};
    if(!count || count>49152) return 0;
    size_t base=16+(size_t)count*HD_ROW,at=base;
    if(base>=size) return 0;
    while(at<size) {
        if(blocks==128 || size-at<4) return 0;
        uint32_t edge=hd_word(data+at);
        if(edge!=512 && edge!=1024 && edge!=2048) return 0;
        size_t bytes=4+(size_t)edge*edge*4;
        if(bytes>size-at) return 0;
        offsets[blocks++]=(uint32_t)at;at+=bytes;
    }
    for(uint32_t i=0;i<count;i++) {
        const uint8_t *row=data+16+i*HD_ROW;int any=0;
        if(!recipe(hd_word(row),hd_word(row+4))) return 0;
        for(uint32_t j=0;j<i;j++) if(!memcmp(row,data+16+j*HD_ROW,8)) return 0;
        for(unsigned slot=0;slot<6;slot++) {
            uint32_t offset=hd_word(row+8+slot*4);if(!offset)continue;
            unsigned block=0;while(block<blocks && offsets[block]!=offset)++block;
            if(block==blocks)return 0;
            used[block]=1;any=1;
        }
        if(!any)return 0;
    }
    for(unsigned i=0;i<blocks;i++)if(!used[i])return 0;
    return 1;
}
int defjam_caf_hd_start(const uint8_t *(*recipe)(uint32_t,uint32_t)) {
    const char *path=getenv("RECOMP_FIGHTER_CAF_HD"),*hash=getenv("RECOMP_FIGHTER_CAF_HD_SHA256");
    if(!path || !*path)return !hash || !*hash;
    if(s_hd || !mod_file_matches(path,hash))return 0;
    FILE *file;
#if defined(_WIN32)
    wchar_t wide[2048];if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,2048))return 0;
    file=_wfopen(wide,L"rb");
#else
    file=fopen(path,"rb");
#endif
    if(!file)return 0;
    if(fseek(file,0,SEEK_END)){fclose(file);return 0;}
    long length=ftell(file);
    if(length<16 || (unsigned long)length>HD_MAX || fseek(file,0,SEEK_SET)){fclose(file);return 0;}
    uint8_t *data=malloc((size_t)length+1);if(!data){fclose(file);return 0;}
    size_t size=fread(data,1,(size_t)length+1,file);int ok=!ferror(file) && size==(size_t)length;fclose(file);
    if(!ok || !hd_valid(data,size,recipe)){free(data);return 0;}
    s_hd=data;s_hd_count=hd_word(data+8);
    fprintf(stderr,"[FIGHTERS] validated %u HD CAF outfits (%zu host bytes)\n",s_hd_count,size);return 1;
}
static int hd_span(uint32_t p,uint32_t size) {
    uint32_t at=p>=0x80000000u?p-0x80000000u:p;
    return at>=0x10000u && at<0x4000000u && size<=0x4000000u-at;
}
static uint32_t hd_swizzle(uint32_t value) {
    value=(value|(value<<4))&0x0F0Fu;value=(value|(value<<2))&0x3333u;
    return (value|(value<<1))&0x5555u;
}
void defjam_caf_hd_apply(uint32_t visual,uint32_t selection,uint32_t outfit) {
    const uint8_t *row=NULL;
    for(uint32_t i=0;i<s_hd_count;i++) {
        const uint8_t *candidate=s_hd+16+i*HD_ROW;
        if(hd_word(candidate)==selection && hd_word(candidate+4)==outfit){row=candidate;break;}
    }
    if(!row)return;
    unsigned owner=0;while(owner<4 && s_hd_owners[owner] && s_hd_owners[owner]!=visual)++owner;
    if(owner==4)hd_stop("more than four live visuals");
    texture_pack_memory_clear(visual);s_hd_owners[owner]=visual;
    for(unsigned slot=0;slot<6;slot++) {
        uint32_t offset=hd_word(row+8+slot*4);if(!offset)continue;
        uint32_t bitmap=MEM32(visual+0xA234+slot*4);
        if(!hd_span(bitmap,20) || MEM8(bitmap)!=0x7D || MEM16(bitmap+4)!=256 || MEM16(bitmap+6)!=256)hd_stop("native fallback bitmap differs");
        uint32_t flags=MEM32(bitmap+12),pixels=bitmap+((flags&0x1000u)?MEM32(bitmap+16):16u);
        if(!hd_span(pixels,256u*256u*4u))hd_stop("native alpha exceeds guest memory");
        uint32_t edge=hd_word(s_hd+offset),scale=edge/256;
        uint8_t *bgra=malloc((size_t)edge*edge*4);if(!bgra)hd_stop("HD material allocation failed");
        memcpy(bgra,s_hd+offset+4,(size_t)edge*edge*4);
        for(uint32_t y=0;y<edge;y++)for(uint32_t x=0;x<edge;x++) {
            uint32_t nx=x/scale,ny=y/scale;
            uint32_t native=(flags&0x2000u)?hd_swizzle(nx)|(hd_swizzle(ny)<<1):ny*256+nx;
            bgra[((size_t)y*edge+x)*4+3]=MEM8(pixels+native*4+3);
        }
        uint32_t address=pixels>=0x80000000u?pixels-0x80000000u:pixels;
        int ok=texture_pack_memory_register(visual,address,(flags&0x2000u)?0x06:0x12,256,256,bgra,edge,edge);
        free(bgra);if(!ok)hd_stop("HD material exceeds renderer budget or source ownership");
        fprintf(stderr,"[FIGHTERS] CAF HD logical=%u outfit=%u slot=%u %ux%u source=%08X original-alpha=held\n",selection,outfit,slot,edge,edge,address);
    }
}
void defjam_caf_hd_clear(void) {
    for(unsigned i=0;i<4;i++)if(s_hd_owners[i]){texture_pack_memory_clear(s_hd_owners[i]);s_hd_owners[i]=0;}
}
