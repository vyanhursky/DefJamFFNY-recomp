#ifndef DEFJAM_FIGHTER_CINEMATIC_H
#define DEFJAM_FIGHTER_CINEMATIC_H
#include "recomp/gen/recomp_types.h"
int defjam_fighter_cinematic_start(void);
int defjam_fighter_cinematic_proofs(void);
const char *defjam_fighter_cinematic_path(void);
void defjam_fighter_cinematic_cache_begin(uint32_t manager);
uint32_t defjam_fighter_cinematic_allocation(uint32_t caller, uint32_t bytes);
void defjam_fighter_cinematic_cache_finish(uint32_t manager);
void defjam_fighter_cinematic_cache_poll(uint32_t manager);
int defjam_fighter_cinematic_cache_ready(uint32_t manager);
uint32_t defjam_fighter_cinematic_cache_index(uint32_t manager, uint32_t native);
void defjam_fighter_cinematic_cache_release(uint32_t manager);
uint64_t defjam_fighter_cinematic_enter(uint32_t manager, uint32_t descriptor, uint32_t request);
void defjam_fighter_cinematic_leave(uint64_t previous, uint32_t request);
void defjam_fighter_cinematic_name(uint32_t descriptor);
void defjam_fighter_cinematic_selected(uint32_t descriptor, uint32_t name);
void defjam_fighter_cinematic_bind(uint32_t descriptor);
#endif
