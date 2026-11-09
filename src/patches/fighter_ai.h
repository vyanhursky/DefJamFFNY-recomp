#ifndef DEFJAM_FIGHTER_AI_H
#define DEFJAM_FIGHTER_AI_H
#include "recomp/gen/recomp_types.h"
int defjam_fighter_ai_start(void);
const char *defjam_fighter_ai_path(void);
void defjam_fighter_ai_bind(uint32_t config);
void defjam_fighter_ai_loaded(uint32_t self, uint32_t config);
#endif
