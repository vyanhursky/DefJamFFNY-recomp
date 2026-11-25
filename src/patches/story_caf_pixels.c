#include "story_caf_pixels.h"
#include <stdlib.h>
#include <string.h>
static int valid(const StoryCafImage *p) {
    return p && p->pixels && p->width && p->height && p->width<=256 && p->height<=256 && p->scale>=1 && p->scale<=4;
}
void story_caf_image_free(StoryCafImage *p) {free(p->pixels);memset(p,0,sizeof *p);}
int story_caf_image_copy(StoryCafImage *out,const StoryCafImage *p) {
    if(!valid(p) || out==p)return 0;
    size_t n=(size_t)p->width*p->height*p->scale*p->scale*4;
    uint8_t *pixels=malloc(n);if(!pixels)return 0;memcpy(pixels,p->pixels,n);
    story_caf_image_free(out);*out=*p;out->pixels=pixels;return 1;
}
static int promote(StoryCafImage *p,unsigned scale) {
    if(p->scale==scale)return 1;
    unsigned w=p->width*scale,h=p->height*scale,oldw=p->width*p->scale;
    uint8_t *pixels=malloc((size_t)w*h*4);if(!pixels)return 0;
    for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++)
        memcpy(pixels+((size_t)y*w+x)*4,p->pixels+((size_t)(y*p->scale/scale)*oldw+x*p->scale/scale)*4,4);
    free(p->pixels);p->pixels=pixels;p->scale=scale;return 1;
}
int story_caf_image_layer(StoryCafImage *d,const StoryCafImage *s,int ox,int oy,int blend) {
    if(!valid(d)||!valid(s)||s==d||ox < -256||ox>256||oy < -256||oy>256)return 0;
    unsigned scale=d->scale>s->scale?d->scale:s->scale;
    if(!promote(d,scale))return 0;
    int dw=(int)(d->width*scale),dh=(int)(d->height*scale),sw=(int)(s->width*scale),sh=(int)(s->height*scale);
    unsigned source_width=s->width*s->scale;
    for(int y=0;y<sh;y++)for(int x=0;x<sw;x++) {
        int dx=x+ox*(int)scale,dy=y+oy*(int)scale;if(dx<0||dy<0||dx>=dw||dy>=dh)continue;
        const uint8_t *a=s->pixels+((size_t)((unsigned)y*s->scale/scale)*source_width+(unsigned)x*s->scale/scale)*4;
        uint8_t *b=d->pixels+((size_t)dy*dw+dx)*4;
        if(!blend||a[3]==255)memcpy(b,a,4);
        else if(a[3]) {
            for(unsigned c=0;c<3;c++)b[c]=(uint8_t)((a[c]*a[3]+b[c]*(255-a[3])+128)>>8);
            if(a[3]>b[3])b[3]=a[3];
        }
    }
    d->hd|=s->hd;return 1;
}
