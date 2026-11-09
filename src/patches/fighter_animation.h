#ifndef DEFJAM_FIGHTER_ANIMATION_H
#define DEFJAM_FIGHTER_ANIMATION_H
#include "recomp/gen/recomp_types.h"
int defjam_fighter_animation_start(void);
const char *defjam_fighter_animation_path(void);
uint32_t defjam_fighter_animation_bank(uint32_t character_core, uint32_t inherited);
#endif
