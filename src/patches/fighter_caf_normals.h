#ifndef DEFJAM_FIGHTER_CAF_NORMALS_H
#define DEFJAM_FIGHTER_CAF_NORMALS_H
#include <stdint.h>
int defjam_caf_normals_start(const uint8_t *(*recipe)(uint32_t,uint32_t),const uint8_t *rows,uint32_t count);
void defjam_caf_normals_release(void);
void defjam_caf_normals_clear(void);
void defjam_caf_normals_detach(uint32_t visual,uint32_t participant);
void defjam_caf_normals_apply(uint32_t visual,uint32_t participant,uint32_t selection,uint32_t outfit);
#endif
