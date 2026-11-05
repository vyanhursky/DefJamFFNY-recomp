#ifndef DEFJAM_FIGHTER_CINEMATIC_H
#define DEFJAM_FIGHTER_CINEMATIC_H
#include "recomp/gen/recomp_types.h"
int defjam_fighter_cinematic_start(void);
const char *defjam_fighter_cinematic_path(void);
uint64_t defjam_fighter_cinematic_enter(uint32_t manager, uint32_t descriptor, uint32_t request);
void defjam_fighter_cinematic_leave(uint64_t previous, uint32_t request);
void defjam_fighter_cinematic_name(uint32_t descriptor);
void defjam_fighter_cinematic_selected(uint32_t descriptor, uint32_t name);
#endif
