#ifndef DEFJAM_FIGHTER_CAF_FACE_H
#define DEFJAM_FIGHTER_CAF_FACE_H
#include <stdint.h>
/* rows points at count sculpt rows inside the loaded fighter-caf.bin and must stay valid. */
int defjam_caf_faces_start(const uint8_t *(*recipe)(uint32_t,uint32_t),const uint8_t *rows,uint32_t count);
void defjam_caf_faces_clear(void);
void defjam_caf_faces_apply(uint32_t visual,uint32_t participant,uint32_t selection,uint32_t outfit,const uint8_t *recipe);
#endif
