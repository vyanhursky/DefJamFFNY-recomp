#ifndef DEFJAM_FIGHTER_CAF_HD_H
#define DEFJAM_FIGHTER_CAF_HD_H
#include <stdint.h>
int defjam_caf_hd_start(const uint8_t *(*recipe)(uint32_t,uint32_t));
void defjam_caf_hd_apply(uint32_t visual,uint32_t selection,uint32_t outfit);
void defjam_caf_hd_clear(void);
#endif
