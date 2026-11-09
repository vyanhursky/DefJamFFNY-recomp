/* PosePaletteBank provenance for ordinary and created actors. 215E0 borrows
 * serialized storage; 21500 owns it. Both use the same in-place ELF fixup.
 * Capture .data before109F80 mutates section offsets, retire before21670/A0
 * release storage, and check the current wrapper root on every use. */
#include "fighter_palette_context.h"
#include "fighter_runtime.h"
#include "recomp/gen/recomp_types.h"
#include <math.h>
#include <string.h>

#define PALETTE_CONTEXTS 128u
#define PALETTE_BYTES (64u * 1024u * 1024u)
typedef struct PaletteContext { uint32_t wrapper, root, begin, bytes; } PaletteContext;
static PaletteContext s_contexts[PALETTE_CONTEXTS];
static RECOMP_TLS FighterPaletteScope s_scope;

static int span(uint32_t begin, uint32_t bytes, uint32_t at, uint32_t size) {
    return begin && bytes && begin <= UINT32_MAX - bytes && size && at >= begin
        && at - begin <= bytes && size <= bytes - (at - begin);
}
static uint16_t half(uint32_t at) { return (uint16_t)(MEM8(at) | (uint16_t)MEM8(at+1)<<8); }
void defjam_fighter_palette_release(uint32_t wrapper) {
    for (unsigned i=0;i<PALETTE_CONTEXTS;++i)
        if (s_contexts[i].wrapper == wrapper) memset(&s_contexts[i],0,sizeof s_contexts[i]);
}
FighterPaletteScope defjam_fighter_palette_begin(uint32_t wrapper) {
    FighterPaletteScope previous=s_scope;
    memset(&s_scope,0,sizeof s_scope);
    if (wrapper && defjam_fighter_research_active()) {
        defjam_fighter_palette_release(wrapper); s_scope.wrapper=wrapper;
    }
    return previous;
}
void defjam_fighter_palette_input(uint32_t descriptor) {
    if (!s_scope.wrapper || !descriptor) return;
    uint32_t raw=MEM32(descriptor+0x10), bytes=MEM32(descriptor+0x14);
    if (!raw || bytes < 52 || bytes > PALETTE_BYTES || raw > UINT32_MAX-bytes
        || MEM32(descriptor+0x18) || memcmp((const void *)XBOX_PTR(raw),"\177ELF\1\1\1",7)
        || half(raw+0x2E)!=40 || half(raw+0x30)!=6) return;
    uint32_t table=MEM32(raw+0x20);
    if (table > bytes || 240 > bytes-table) return;
    uint32_t at=raw+table+40, offset=MEM32(at+0x10), size=MEM32(at+0x14);
    if (MEM32(at+4)!=1 || offset > bytes || !size || size > bytes-offset) return;
    s_scope.begin=raw+offset; s_scope.bytes=size;
}
void defjam_fighter_palette_end(FighterPaletteScope previous,int success) {
    if (success && s_scope.wrapper && s_scope.begin) {
        uint32_t root=MEM32(s_scope.wrapper);
        if (span(s_scope.begin,s_scope.bytes,root,16)) {
            for (unsigned i=0;i<PALETTE_CONTEXTS;++i) if (!s_contexts[i].wrapper) {
                s_contexts[i]=(PaletteContext){s_scope.wrapper,root,s_scope.begin,s_scope.bytes};
                break; /* Exhaustion fails closed at the graph's use gate. */
            }
        }
    }
    s_scope=previous;
}
int defjam_fighter_palette_check(uint32_t wrapper,uint32_t root,uint32_t bones,const uint32_t required[2]) {
    if (!wrapper || !root || !bones || bones > 4096 || !required) return 0;
    const PaletteContext *context=NULL;
    for (unsigned i=0;i<PALETTE_CONTEXTS;++i)
        if (s_contexts[i].wrapper==wrapper) { context=&s_contexts[i]; break; }
    if (!context || context->root!=root || MEM32(wrapper)!=root
        || !span(context->begin,context->bytes,root,16) || half(root+4)!=2) return 0;
    for (unsigned selector=0;selector<2;++selector) {
        uint32_t palette=MEM32(root+8+4*selector);
        if (!span(context->begin,context->bytes,palette,12)) return 0;
        uint32_t frames=MEM8(palette+8), quats=MEM8(palette+9), vectors=MEM8(palette+10);
        uint32_t channels=quats+vectors, samples=MEM32(palette), destinations=MEM32(palette+4);
        if (!frames || frames < required[selector] || MEM8(palette+11) || !channels
            || !span(context->begin,context->bytes,destinations,2*channels)
            || !span(context->begin,context->bytes,samples,16*channels*frames)) return 0;
        uint8_t occupied[49152]={0};
        for (unsigned channel=0;channel<channels;++channel) {
            uint32_t destination=half(destinations+2*channel), width=channel<quats?4u:3u;
            if (destination+width > 12*bones
                || (width==4 ? destination%12!=4 : (destination%12!=0 && destination%12!=8))) return 0;
            for (unsigned d=0;d<width;++d) if (occupied[destination+d]++) return 0;
            for (unsigned frame=0;frame<frames;++frame) {
                float values[4]; memcpy(values,(const void *)XBOX_PTR(samples+16*(frame*channels+channel)),16);
                double norm=0;
                for (unsigned d=0;d<width;++d) {
                    if (!isfinite(values[d]) || fabs(values[d])>1000000) return 0;
                    norm+=(double)values[d]*values[d];
                }
                if (width==4 && fabs(norm-1)>0.002) return 0;
            }
        }
    }
    return 1;
}
