#ifndef DEFJAM_FIGHTER_MOTION_H
#define DEFJAM_FIGHTER_MOTION_H
#include <stdint.h>
/* Internal validated-template research lane, not authored behavior admission. */
int defjam_fighter_motion_start(void);
const char *defjam_fighter_motion_path(void);
int defjam_fighter_motion_audio(uint32_t input);
void defjam_fighter_motion_register(uint32_t source);
void defjam_fighter_motion_release(uint32_t owner);
uint32_t defjam_fighter_motion_bank(uint32_t bank);
int defjam_fighter_motion_parameters(uint32_t actor);
int defjam_fighter_motion_state(uint32_t output, uint32_t context, uint32_t id);
int defjam_fighter_motion_present(uint32_t context, uint32_t id);
int defjam_fighter_motion_frame(uint32_t local);
int defjam_fighter_motion_scale(void);
int defjam_fighter_motion_blazin_mask(void);
void defjam_fighter_motion_ai_profiles(uint32_t output, uint32_t input);
uint32_t defjam_fighter_motion_ai_capture(uint32_t config, char expected[128]);
void defjam_fighter_motion_ai_verify(uint32_t config, uint32_t mask, const char expected[128]);
#endif
