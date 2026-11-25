#ifndef DEFJAM_STORY_CAF_HD_H
#define DEFJAM_STORY_CAF_HD_H
#include <stdint.h>
int story_caf_begin(uint32_t visual);
void story_caf_end(void);
void story_caf_lookup(uint32_t bitmap,uint32_t view,uint32_t name);
void story_caf_resource_open(uint32_t manager,uint32_t handle,uint32_t path);
void story_caf_resource_data(uint32_t manager,uint32_t handle,uint32_t output);
void story_caf_resource_close(uint32_t manager,uint32_t handle);
void story_caf_resource_reset(uint32_t manager);
void story_caf_convert(uint32_t source,uint32_t dest);
void story_caf_layer(uint32_t dest,uint32_t source,uint32_t placement);
void story_caf_layer_done(uint32_t dest);
void story_caf_destroy(uint32_t bitmap);
void story_caf_invalidate(uint32_t visual,int slot);
/* Optional Story replacements yield to an existing authored CAF HD allocation.
 * Clears only Story slot owners; returns the number retired for one retry. */
uint32_t story_caf_evict(void);
#endif
