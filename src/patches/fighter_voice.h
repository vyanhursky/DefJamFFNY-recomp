#ifndef DEFJAM_FIGHTER_VOICE_H
#define DEFJAM_FIGHTER_VOICE_H
#include <stdint.h>
int defjam_fighter_voice_start(void);
const char *defjam_fighter_voice_path(void);
void defjam_fighter_voice_select(uint32_t input);
void defjam_fighter_voice_restore(void);
int defjam_fighter_voice_load(uint32_t selector);
void defjam_fighter_voice_observe(uint32_t family, uint32_t voice, uint32_t result);
#endif
