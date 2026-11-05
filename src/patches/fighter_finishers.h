#ifndef DEFJAM_FIGHTER_FINISHERS_H
#define DEFJAM_FIGHTER_FINISHERS_H
#include "recomp/gen/recomp_types.h"
typedef struct FighterFinisherScope { uint32_t subject, counterpart, core; } FighterFinisherScope;
int defjam_fighter_finishers_start(void);
const char *defjam_fighter_finishers_path(void);
void defjam_fighter_finishers_mask(uint32_t base, uint32_t count, uint32_t mask);
void defjam_fighter_finishers_loaded(uint32_t provider);
void defjam_fighter_finishers_release(uint32_t manager);
uint32_t defjam_fighter_finisher_name(uint32_t mode, uint32_t ordinal, uint32_t caller);
FighterFinisherScope defjam_fighter_finisher_enter(uint32_t actor);
void defjam_fighter_finisher_leave(FighterFinisherScope previous);
uint32_t defjam_fighter_finisher_motion(uint32_t actor, uint32_t motion, uint32_t mode, uint32_t caller);
uint32_t defjam_fighter_finisher_parameters(uint32_t output, uint32_t source, uint32_t caller);
#endif
