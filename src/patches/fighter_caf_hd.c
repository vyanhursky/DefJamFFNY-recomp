/* Versioned, sealed HD CAF RGB. Original native bitmaps and guest allocation
 * sizes stay unchanged; host replacements are owned by each live visual. */
#include "fighter_caf_hd.h"
#include "story_caf_hd.h"
#include "fighter_caf_layout.h"
#include "fighter_fatal.h"
#include "hooks/guest_call.h"
#include "texture_pack.h"
#include "kernel/xbox_memory_layout.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Reuse the pinned toolkit's bounded deflate decoder; no new dependency. */
#define STBI_ONLY_ZLIB
#define STBI_SUPPORT_ZLIB
#define STBI_NO_STDIO
#define STB_IMAGE_STATIC
#define STB_IMAGE_IMPLEMENTATION
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4505 4100)
#else
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#pragma GCC diagnostic ignored "-Wunused-parameter"
#endif
#include "stb/stb_image.h"
#ifdef _MSC_VER
#pragma warning(pop)
#else
#pragma GCC diagnostic pop
#endif
static const uint8_t *s_hd; /* hd section inside the container, which stays resident */
static uint32_t s_hd_count,s_hd_owners[4];
static uint32_t hd_word(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void hd_stop(const char *why) {defjam_fighter_fatal("HD CAF",why);}
/* Rows, then edge-prefixed BGRA blocks. Every block must be referenced exactly where a row says it starts. */
static int hd_valid(const uint8_t *data,size_t size,uint32_t count,const uint8_t *(*recipe)(uint32_t,uint32_t)) {
    if(size>CAF_HD_MAX_BYTES || !count || count>49152) return 0;
    uint32_t offsets[CAF_HD_MAX_BLOCKS],blocks=0;uint8_t used[CAF_HD_MAX_BLOCKS]={0};
    size_t base=(size_t)count*CAF_HD_STRIDE,at=base,expanded=0;
    if(base>=size) return 0;
    while(at<size) {
        if(blocks==CAF_HD_MAX_BLOCKS || size-at<4) return 0;
        uint32_t tag=hd_word(data+at),edge=tag&0x3fffffffu;
        if(edge!=512 && edge!=1024 && edge!=2048) return 0;
        if((tag&0xc0000000u)==0x40000000u)return 0;
        expanded+=(size_t)edge*edge*4;
        if(expanded>CAF_CONTAINER_MAX_BYTES)return 0;
        size_t bytes=4+(size_t)edge*edge*((tag&0x80000000u)?3u:4u);
        if((tag&0xc0000000u)==0xc0000000u) {
            if(size-at<8)return 0;
            uint32_t packed=hd_word(data+at+4);bytes=8+(size_t)packed;
            if(!packed || bytes>size-at || packed>CAF_HD_MAX_BYTES)return 0;
            size_t rgb_bytes=(size_t)edge*edge*3;
            char *rgb=malloc(rgb_bytes);if(!rgb)return 0;
            int decoded=stbi_zlib_decode_buffer(rgb,(int)rgb_bytes,(const char *)data+at+8,(int)packed);
            free(rgb);if(decoded!=(int)rgb_bytes)return 0;
        }
        if(bytes>size-at) return 0;
        offsets[blocks++]=(uint32_t)at;at+=bytes;
    }
    for(uint32_t i=0;i<count;i++) {
        const uint8_t *row=data+(size_t)i*CAF_HD_STRIDE;int any=0;
        if(!recipe(hd_word(row+CAF_HD_SELECTION),hd_word(row+CAF_HD_OUTFIT))) return 0;
        for(uint32_t j=0;j<i;j++) if(!memcmp(row,data+(size_t)j*CAF_HD_STRIDE,8)) return 0;
        for(unsigned slot=0;slot<CAF_EXTRA_ATLAS_COUNT;slot++) {
            uint32_t offset=hd_word(row+CAF_HD_ATLAS_AT(slot));if(!offset)continue;
            unsigned block=0;while(block<blocks && offsets[block]!=offset)++block;
            if(block==blocks)return 0;
            used[block]=1;any=1;
        }
        if(!any)return 0;
    }
    for(unsigned i=0;i<blocks;i++)if(!used[i])return 0;
    return 1;
}
int defjam_caf_hd_start(const uint8_t *(*recipe)(uint32_t,uint32_t),const uint8_t *section,size_t size,uint32_t count) {
    if(s_hd || !hd_valid(section,size,count,recipe))return 0;
    s_hd=section;s_hd_count=count;
    fprintf(stderr,"[FIGHTERS] validated %u HD CAF outfits (%zu host bytes)\n",count,size);return 1;
}
void defjam_caf_hd_release(void) {s_hd=NULL;s_hd_count=0;}
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
        const uint8_t *candidate=s_hd+(size_t)i*CAF_HD_STRIDE;
        if(hd_word(candidate+CAF_HD_SELECTION)==selection && hd_word(candidate+CAF_HD_OUTFIT)==outfit){row=candidate;break;}
    }
    if(!row)return;
    unsigned owner=0;while(owner<4 && s_hd_owners[owner] && s_hd_owners[owner]!=visual)++owner;
    if(owner==4)hd_stop("more than four live visuals");
    texture_pack_memory_clear(visual);s_hd_owners[owner]=visual;
    for(unsigned slot=0;slot<CAF_EXTRA_ATLAS_COUNT;slot++) {
        uint32_t offset=hd_word(row+CAF_HD_ATLAS_AT(slot));if(!offset)continue;
        uint32_t bitmap=MEM32(visual+0xA234+slot*4);
        if(!hd_span(bitmap,20) || MEM8(bitmap)!=0x7D || MEM16(bitmap+4)!=256 || MEM16(bitmap+6)!=256)hd_stop("native fallback bitmap differs");
        uint32_t flags=MEM32(bitmap+12),pixels=bitmap+((flags&0x1000u)?MEM32(bitmap+16):16u);
        if(!hd_span(pixels,256u*256u*4u))hd_stop("native alpha exceeds guest memory");
        uint32_t tag=hd_word(s_hd+offset),edge=tag&0x3fffffffu,scale=edge/256;
        uint8_t *bgra=malloc((size_t)edge*edge*4);
        if(!bgra && story_caf_evict())bgra=malloc((size_t)edge*edge*4);
        if(!bgra)hd_stop("HD material allocation failed");
        if(tag&0x80000000u) {
            const uint8_t *rgb=s_hd+offset+4;uint8_t *decoded=NULL;
            if(tag&0x40000000u) {
                size_t bytes=(size_t)edge*edge*3;decoded=malloc(bytes);
                if(!decoded || stbi_zlib_decode_buffer((char *)decoded,(int)bytes,(const char *)s_hd+offset+8,(int)hd_word(s_hd+offset+4))!=(int)bytes)
                {
                    free(decoded);free(bgra);texture_pack_memory_clear(visual);
                    fprintf(stderr,"[FIGHTERS] CAF packed HD decode unavailable; retaining native atlas fallback logical=%u outfit=%u\n",selection,outfit);
                    return;
                }
                rgb=decoded;
            }
            for(size_t i=0;i<(size_t)edge*edge;++i)memcpy(bgra+i*4,rgb+i*3,3);
            free(decoded);
        } else memcpy(bgra,s_hd+offset+4,(size_t)edge*edge*4);
        for(uint32_t y=0;y<edge;y++)for(uint32_t x=0;x<edge;x++) {
            uint32_t nx=x/scale,ny=y/scale;
            uint32_t native=(flags&0x2000u)?hd_swizzle(nx)|(hd_swizzle(ny)<<1):ny*256+nx;
            bgra[((size_t)y*edge+x)*4+3]=MEM8(pixels+native*4+3);
        }
        /* The device sees MmGetPhysicalAddress's RAM-mirror name, not the
         * CPU heap VA. Use the kernel's existing mapping, including its
         * configurable alias; never guess by stripping/adding address bits. */
        uint32_t address=xbox_PhysRamName(pixels);
        int ok=texture_pack_memory_register(visual,address,(flags&0x2000u)?0x06:0x12,256,256,bgra,edge,edge);
        if(!ok && story_caf_evict())ok=texture_pack_memory_register(visual,address,(flags&0x2000u)?0x06:0x12,256,256,bgra,edge,edge);
        free(bgra);if(!ok)hd_stop("HD material exceeds renderer budget or source ownership");
        fprintf(stderr,"[FIGHTERS] CAF HD logical=%u outfit=%u slot=%u %ux%u source=%08X original-alpha=held\n",selection,outfit,slot,edge,edge,address);
    }
}
void defjam_caf_hd_clear(void) {
    for(unsigned i=0;i<4;i++)if(s_hd_owners[i]){texture_pack_memory_clear(s_hd_owners[i]);s_hd_owners[i]=0;}
}
