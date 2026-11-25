/* Retail Story CAF: mirror the native compositor into bounded host images.
 * This never changes a guest bitmap, allocation, recipe, palette or material.
 * Source keys are captured before palette mutation; final alpha is native. */
#include "story_caf_hd.h"
#include "story_caf_pixels.h"
#include "fighter_caf.h"
#include "hooks/guest_call.h"
#include "texture_pack.h"
#include "kernel/xbox_memory_layout.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#define SHADOWS 192
#define HOST_LIMIT (96u*1024u*1024u)
typedef struct Shadow { uint32_t bitmap; char id[65]; StoryCafImage image,native; int raw,failed; } Shadow;
static Shadow s_images[SHADOWS];
static uint32_t s_visual;
static int s_failed;
static unsigned s_nested;
static unsigned s_reports;
static unsigned s_loaded,s_native,s_verified;
static uint32_t s_published[32];
/* Palette paint mutates borrowed archives in place. Keep their first, unpainted
 * identity by canonical resource and entry, guarded by the index-data hash.
 * Guest addresses and resource handles may be reused; neither is an identity.
 * Bounded process metadata: <=8192 palette records (~11 MiB), 256 live handles. */
typedef struct SourceMemo { char resource[128],name[5],indices[65],id[65]; uint8_t palette[1024]; unsigned count; } SourceMemo;
static SourceMemo *s_memos;
static unsigned s_memo_count,s_memo_capacity,s_handle_count,s_archive_count;
static struct {uint32_t manager,handle;char resource[128];} s_handles[256];
static struct {uint32_t base;char resource[128];} s_archives[64];
static int span(uint32_t p,uint32_t n) {
    uint32_t a=p>=0x80000000u?p-0x80000000u:p;
    return a>=0x10000u && a<0x4000000u && n<=0x4000000u-a;
}
static size_t image_bytes(const StoryCafImage *p) {return (size_t)p->width*p->height*p->scale*p->scale*4;}
static int budget(void) {
    size_t n=0;for(unsigned i=0;i<SHADOWS;i++)n+=image_bytes(&s_images[i].image)+image_bytes(&s_images[i].native);
    if(n>HOST_LIMIT){s_failed=1;return 0;}return 1;
}
static Shadow *find(uint32_t p) {for(unsigned i=0;i<SHADOWS;i++)if(s_images[i].bitmap==p && p)return &s_images[i];return NULL;}
void story_caf_resource_open(uint32_t manager,uint32_t handle,uint32_t path) {
    if(!s_visual || s_nested || handle==UINT32_MAX)return;
    char text[512];unsigned n=0;
    for(;n<sizeof text;n++){if(!span(path+n,1))return;text[n]=(char)MEM8(path+n);if(!text[n])break;}
    if(n==sizeof text)return;
    const char *base=text;
    for(const char *p=text;*p;p++)if(*p=='|'||*p=='/'||*p=='\\')base=p+1;
    size_t length=strlen(base);if(length<5||n>=128)return;
    char resource[128];
    for(unsigned i=0;i<=n;i++)resource[i]=text[i]=='\\'?'/':(char)tolower((unsigned char)text[i]);
    if(strcmp(resource+n-4,".xsh"))return;
    unsigned at=0;while(at<256 && s_handles[at].resource[0] && (s_handles[at].handle!=handle||s_handles[at].manager!=manager))at++;
    if(at==256){s_failed=1;return;}
    if(!s_handles[at].resource[0])s_handle_count++;
    s_handles[at].manager=manager;s_handles[at].handle=handle;strcpy(s_handles[at].resource,resource);
}
void story_caf_resource_data(uint32_t manager,uint32_t handle,uint32_t output) {
    if(!s_visual || s_nested || !span(output,8))return;
    uint32_t base=MEM32(output);if(!span(base,16)||MEM32(base)!=0x58504853u)return;
    const char *resource=NULL;
    for(unsigned i=0;i<256;i++)if(s_handles[i].resource[0]&&s_handles[i].handle==handle&&s_handles[i].manager==manager){resource=s_handles[i].resource;break;}
    if(!resource)return;
    unsigned at=0;while(at<s_archive_count && s_archives[at].base!=base)at++;
    if(at==64){s_failed=1;return;}if(at==s_archive_count)s_archive_count++;
    s_archives[at].base=base;strcpy(s_archives[at].resource,resource);
}
void story_caf_resource_close(uint32_t manager,uint32_t handle) {
    if(!s_handle_count)return;
    for(unsigned i=0;i<256;i++)if(s_handles[i].resource[0]&&s_handles[i].manager==manager&&s_handles[i].handle==handle){memset(&s_handles[i],0,sizeof s_handles[i]);s_handle_count--;return;}
}
void story_caf_resource_reset(uint32_t manager) {
    if(!s_handle_count)return;
    for(unsigned i=0;i<256;i++)if(s_handles[i].resource[0]&&s_handles[i].manager==manager){memset(&s_handles[i],0,sizeof s_handles[i]);s_handle_count--;}
}
void story_caf_destroy(uint32_t p) {
    if(!s_visual||s_nested)return;Shadow *s=find(p);if(s){story_caf_image_free(&s->image);story_caf_image_free(&s->native);memset(s,0,sizeof *s);}
}
static Shadow *fresh(uint32_t p) {
    if(!p)return NULL;story_caf_destroy(p);
    for(unsigned i=0;i<SHADOWS;i++)if(!s_images[i].bitmap){s_images[i].bitmap=p;return &s_images[i];}
    s_failed=1;return NULL;
}
static uint32_t morton(unsigned x,unsigned y,unsigned w,unsigned h) {
    unsigned out=0,bit=0;for(unsigned b=1;b<w||b<h;b<<=1){if(b<w){if(x&b)out|=1u<<bit;bit++;}if(b<h){if(y&b)out|=1u<<bit;bit++;}}return out;
}
static uint32_t attachment(uint32_t p,unsigned kind) {
    for(unsigned i=0;i<64;i++) {
        if(!span(p,16))return 0;
        int32_t delta=(int32_t)MEM32(p)>>8;
        if(!delta)return 0;
        p+=(uint32_t)delta;if(!span(p,16))return 0;
        if(MEM8(p)==kind)return p;
    }return 0;
}
/* Native decoder for the byte-indexed sources and BGRA working images. Other
 * source encodings retain the game's native compositor output. */
static int descriptor(uint32_t p,RecompTextureSource *out,uint32_t *flags) {
    if(!span(p,20))return 0;unsigned kind=MEM8(p),w=MEM16(p+4),h=MEM16(p+6);
    if(!w||!h||w>256||h>256)return 0;
    uint32_t f=MEM32(p+12),offset=(f&0x1000u)?MEM32(p+16):16,fmt,n;
    if(f>>28)return 0;
    if(kind==0x7b){fmt=0x0b;n=w*h;}else if(kind==0x7d){fmt=(f&0x2000u)?6:0x12;n=w*h*4;}
    else return 0;
    uint32_t pixels=p+offset;if(!span(pixels,n))return 0;
    memset(out,0,sizeof *out);out->width=w;out->height=h;out->row_texels=w;out->format=fmt;out->data=(const void *)XBOX_PTR(p+offset);out->bytes=n;
    if(kind==0x7b){
        uint32_t pal=attachment(p,0x2a);if(!pal||!span(pal,20))return 0;
        unsigned count=MEM16(pal+4);
        uint32_t colors=pal+((MEM32(pal+12)&0x1000u)?MEM32(pal+16):16u);
        if(!count||count>256||!span(colors,count*4))return 0;
        out->palette=(const void *)XBOX_PTR(colors);out->palette_entries=count;
    }
    *flags=f;return 1;
}
static int decode_palette(uint32_t p,StoryCafImage *out,const void *palette,unsigned entries) {
    RecompTextureSource d;uint32_t flags;if(!descriptor(p,&d,&flags)|| (d.format!=0xb&&d.format!=6&&d.format!=0x12))return 0;
    if(palette && d.format==0xb){d.palette=palette;d.palette_entries=entries;}
    uint8_t *pixels=malloc((size_t)d.width*d.height*4);if(!pixels)return 0;
    for(unsigned y=0;y<d.height;y++)for(unsigned x=0;x<d.width;x++) {
        unsigned at=(flags&0x2000u)?morton(x,y,d.width,d.height):y*d.width+x;
        if(at>=d.width*d.height){free(pixels);return 0;}
        const uint8_t *src=(const uint8_t *)d.data+at*(d.format==0xb?1:4);
        if(d.format==0xb){if(*src>=d.palette_entries){free(pixels);return 0;}src=(const uint8_t *)d.palette+*src*4;}
        memcpy(pixels+((size_t)y*d.width+x)*4,src,4);
    }
    story_caf_image_free(out);*out=(StoryCafImage){pixels,d.width,d.height,1,0};return 1;
}
static int decode(uint32_t p,StoryCafImage *out) {return decode_palette(p,out,NULL,0);}
void story_caf_lookup(uint32_t p,uint32_t view,uint32_t name) {
    if(!s_visual||s_failed)return;RecompTextureSource d;uint32_t flags;
    if(!descriptor(p,&d,&flags))return;
    Shadow *s=fresh(p);if(!s)return;s->raw=1;
    const char *resource=NULL;char entry[5]={0};SourceMemo *memo=NULL;
    if(span(view,4)&&span(name,4)) {
        for(unsigned i=0;i<s_archive_count;i++)if(s_archives[i].base==MEM32(view)){resource=s_archives[i].resource;break;}
        for(unsigned i=0;i<4;i++)entry[i]=(char)tolower(MEM8(name+i));
    }
    if(resource && d.format==0xb) {
        RecompTextureSource indices=d;indices.palette=NULL;indices.palette_entries=0;char fingerprint[65];
        if(!texture_pack_hash(&indices,fingerprint)){s->failed=1;return;}
        for(unsigned i=0;i<s_memo_count;i++)if(!strcmp(s_memos[i].resource,resource)&&!memcmp(s_memos[i].name,entry,5)&&!strcmp(s_memos[i].indices,fingerprint)){memo=&s_memos[i];break;}
        if(!memo && s_memo_count<8192) {
            if(s_memo_count==s_memo_capacity) {
                unsigned n=s_memo_capacity?s_memo_capacity*2:256;SourceMemo *grown=realloc(s_memos,(size_t)n*sizeof *grown);
                if(grown){s_memos=grown;s_memo_capacity=n;}
            }
            if(s_memo_count<s_memo_capacity && texture_pack_hash(&d,s->id)) {
                memo=&s_memos[s_memo_count++];strcpy(memo->resource,resource);memcpy(memo->name,entry,5);
                strcpy(memo->indices,fingerprint);strcpy(memo->id,s->id);memo->count=d.palette_entries;memcpy(memo->palette,d.palette,d.palette_entries*4);
            }
        }
    }
    if(memo)strcpy(s->id,memo->id);
    else if(!texture_pack_hash(&d,s->id)){s->failed=1;return;}
    /* Keep the unpainted native baseline for palette-aligned RGB correction. */
    if(d.format==0xb && !decode_palette(p,&s->image,memo?memo->palette:NULL,memo?memo->count:0))s->failed=1;
    budget();
}
static int materialize(Shadow *s,StoryCafImage *out) {
    if(!s||s->failed)return 0;
    if(!s->raw)return story_caf_image_copy(out,&s->image);
    RecompTextureSource d;uint32_t flags;if(!descriptor(s->bitmap,&d,&flags))return 0;
    uint32_t w=0,h=0;uint8_t *hd=texture_pack_source_png(s->id,d.width,d.height,&w,&h);
    if(!hd){s_native++;return decode(s->bitmap,out);} /* Partial packs retain native layers. */
    s_loaded++;
    unsigned scale=w/d.width;
    if(scale<1||scale>4){free(hd);return 0;}
    {
        StoryCafImage painted={0};if(!decode(s->bitmap,&painted)){free(hd);return 0;}
        for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++) {
            size_t at=((size_t)(y/scale)*d.width+x/scale)*4,hi=((size_t)y*w+x)*4;
            if(s->image.pixels)for(unsigned c=0;c<3;c++){int v=(int)hd[hi+c]+painted.pixels[at+c]-s->image.pixels[at+c];hd[hi+c]=(uint8_t)(v<0?0:v>255?255:v);}
            /* Native source alpha controls composition, for BGRA and indexed
             * sources alike. PNG alpha never invents a new coverage mask. */
            hd[hi+3]=painted.pixels[at+3];
        }
        story_caf_image_free(&painted);
    }
    *out=(StoryCafImage){hd,d.width,d.height,scale,scale>1};return 1;
}
void story_caf_convert(uint32_t src,uint32_t dest) {
    if(!s_visual||s_failed||!dest||src==dest)return;
    Shadow *source=find(src);if(!source)return;
    StoryCafImage pixels={0},native={0};int ok=materialize(source,&pixels);
    if(source->raw)ok=decode(dest,&native)&&ok;
    else ok=story_caf_image_copy(&native,&source->native)&&ok;
    Shadow *s=fresh(dest);if(!s){story_caf_image_free(&pixels);story_caf_image_free(&native);return;}
    s->image=pixels;s->native=native;s->failed=!ok;budget();
}
void story_caf_layer(uint32_t dest,uint32_t src,uint32_t placement) {
    if(!s_visual||s_failed)return;Shadow *d=find(dest);if(!d){s_failed=1;return;}
    StoryCafImage pixels={0};Shadow *source=find(src);
    if(!source){story_caf_lookup(src,0,0);source=find(src);}
    uint32_t pos=attachment(src,0x7c);int x=0,y=0;
    if(pos){if(!span(pos,16)){d->failed=1;return;}x=(int32_t)MEM32(pos+8);y=(int32_t)MEM32(pos+12);}
    if(!span(placement,12)){d->failed=1;return;}unsigned mode=MEM8(placement+8);
    if(mode!='b' && mode!='c')return; /* Same no-op as native dispatch. */
    if(!materialize(source,&pixels)||!story_caf_image_layer(&d->image,&pixels,x,y,mode=='b'))d->failed=1;
    story_caf_image_free(&pixels);budget();
    /* Independently replay at native resolution, then compare against the
     * game's actual result after it runs. Any unsupported native behavior
     * disables this atlas instead of presenting a plausible wrong composite. */
    StoryCafImage native={0};
    if(!decode(src,&native)||!story_caf_image_layer(&d->native,&native,x,y,mode=='b'))d->failed=1;
    story_caf_image_free(&native);
}
void story_caf_layer_done(uint32_t dest) {
    if(!s_visual||s_failed)return;Shadow *d=find(dest);if(!d||d->failed)return;
    StoryCafImage actual={0};
    if(!decode(dest,&actual)||actual.width!=d->native.width||actual.height!=d->native.height||
       memcmp(actual.pixels,d->native.pixels,image_bytes(&actual))) {
        d->failed=1;
        if(s_reports++<96)fprintf(stderr,"[STORYHD] native layer differs; retaining native atlas\n");
    } else s_verified++;
    story_caf_image_free(&actual);
}
void story_caf_invalidate(uint32_t visual,int slot) {
    if(slot>=0&&slot<6) {
        uint32_t owner=visual+0xA234u+(unsigned)slot*4;texture_pack_memory_clear(owner);
        for(unsigned i=0;i<32;i++)if(s_published[i]==owner)s_published[i]=0;
    } else if(slot==-1)for(unsigned i=0;i<6;i++)story_caf_invalidate(visual,(int)i);
}
uint32_t story_caf_evict(void) {
    uint32_t count=0;
    for(unsigned i=0;i<32;i++)if(s_published[i]){texture_pack_memory_clear(s_published[i]);s_published[i]=0;count++;}
    return count;
}
static int remember(uint32_t owner) {
    for(unsigned i=0;i<32;i++)if(s_published[i]==owner)return 1;
    for(unsigned i=0;i<32;i++)if(!s_published[i]){s_published[i]=owner;return 1;}
    return 0;
}
int story_caf_begin(uint32_t visual) {
    /* A native load may pump other work. Nested builds run entirely native;
     * the interrupted outer build also falls back rather than mixing owners. */
    if(s_visual){s_nested++;s_failed=1;return -1;}
    if(!span(visual,0xA28c)||!texture_pack_compositor("story-caf-v1"))return 0;
    /* Authored CAF recipes replace/rebind native atlases after construction.
     * Their existing recipe/HD owner has priority over retail source packs.
     * The classifier works before context+1 is set; tracked Story profiles
     * remain on the original loader and are explicitly excluded by it. */
    if(defjam_fighter_caf_visual(visual,0,0)){story_caf_invalidate(visual,-1);return 0;}
    s_visual=visual;s_failed=0;s_loaded=s_native=s_verified=s_archive_count=0;return 1;
}
void story_caf_end(void) {
    if(s_nested){s_nested--;return;}
    if(!s_visual)return;
    for(unsigned i=0;i<6;i++) {
        uint32_t bitmap=MEM32(s_visual+0xA234+i*4);Shadow *s=find(bitmap);
        if(!s)continue; /* Unchanged slots keep their own registration. */
        story_caf_invalidate(s_visual,(int)i);
        if(s_failed||s->failed||!s->image.hd)continue;
        RecompTextureSource d;uint32_t flags;
        if(!descriptor(bitmap,&d,&flags)|| (MEM8(bitmap)!=0x7d&&MEM8(bitmap)!=0x7b)||d.width!=256||d.height!=256)continue;
        unsigned scale=s->image.scale,w=256*scale;
        if(s->image.width!=256||s->image.height!=256)continue;
        StoryCafImage native={0};if(!decode(bitmap,&native))continue;
        for(unsigned y=0;y<w;y++)for(unsigned x=0;x<w;x++) {
            unsigned at=(y/scale)*256+x/scale;
            s->image.pixels[((size_t)y*w+x)*4+3]=native.pixels[at*4+3];
        }
        story_caf_image_free(&native);
        uint32_t cpu=bitmap+((flags&0x1000u)?MEM32(bitmap+16):16);
        int ok=texture_pack_memory_register(s_visual+0xA234+i*4,xbox_PhysRamName(cpu),d.format,256,256,s->image.pixels,w,w);
        if(ok && !remember(s_visual+0xA234+i*4)){story_caf_invalidate(s_visual,(int)i);ok=0;}
        if(s_reports++<96)fprintf(stderr,"[STORYHD] visual=%08X slot=%u scale=%u registered=%d native-alpha=held\n",s_visual,i,scale,ok);
    }
    for(unsigned i=0;i<SHADOWS;i++){story_caf_image_free(&s_images[i].image);story_caf_image_free(&s_images[i].native);memset(&s_images[i],0,sizeof s_images[i]);}
    if(s_failed && s_reports++<96)fprintf(stderr,"[STORYHD] incomplete composition; native fallback retained\n");
    if(s_reports++<96)fprintf(stderr,"[STORYHD] sources loaded=%u native=%u verified-layers=%u fallback=%d\n",s_loaded,s_native,s_verified,s_failed);
    s_visual=0;s_failed=0;
}
