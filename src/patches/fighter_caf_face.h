#ifndef DEFJAM_FIGHTER_CAF_FACE_H
#define DEFJAM_FIGHTER_CAF_FACE_H
#include <stdint.h>
int defjam_caf_faces_start(const uint8_t *(*recipe)(uint32_t,uint32_t));
void defjam_caf_faces_clear(void);
void defjam_caf_faces_apply(uint32_t visual,uint32_t participant,uint32_t selection,uint32_t outfit,const uint8_t *recipe);
#endif
