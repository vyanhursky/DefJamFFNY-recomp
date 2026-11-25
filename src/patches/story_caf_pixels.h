#ifndef DEFJAM_STORY_CAF_PIXELS_H
#define DEFJAM_STORY_CAF_PIXELS_H
#include <stdint.h>
/* Pure host-side BGRA operations. Native coordinates and image construction
 * stay unchanged. Scale is an integer 1..4, native edges at most 256. */
typedef struct StoryCafImage { uint8_t *pixels; unsigned width,height,scale; int hd; } StoryCafImage;
void story_caf_image_free(StoryCafImage *image);
int story_caf_image_copy(StoryCafImage *out,const StoryCafImage *source);
int story_caf_image_layer(StoryCafImage *dest,const StoryCafImage *source,int x,int y,int blend);
#endif
