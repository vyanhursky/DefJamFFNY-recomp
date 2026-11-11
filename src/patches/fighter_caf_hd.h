#ifndef DEFJAM_FIGHTER_CAF_HD_H
#define DEFJAM_FIGHTER_CAF_HD_H
#include <stddef.h>
#include <stdint.h>
/* section points at the hd section inside the loaded fighter-caf.bin and must stay valid until release. */
int defjam_caf_hd_start(const uint8_t *(*recipe)(uint32_t,uint32_t),const uint8_t *section,size_t size,uint32_t count);
void defjam_caf_hd_apply(uint32_t visual,uint32_t selection,uint32_t outfit);
void defjam_caf_hd_clear(void);
void defjam_caf_hd_release(void);
#endif
