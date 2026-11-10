#ifndef DEFJAM_FIGHTER_CAF_H
#define DEFJAM_FIGHTER_CAF_H
#include <stdint.h>
int defjam_fighter_caf_start(void);
void defjam_fighter_caf_participant(uint32_t service, uint32_t participant, uint32_t selection);
void defjam_fighter_caf_clear(void);
int defjam_fighter_caf_visual(uint32_t visual, uint32_t participant, int apply);
int defjam_fighter_caf_context(uint32_t service, uint32_t participant, uint32_t *output);
int defjam_fighter_caf_audio(uint32_t input);
void defjam_fighter_caf_finishers(void);
void defjam_fighter_caf_menu_clear(uint32_t participant);
int defjam_fighter_caf_outfit(uint32_t participant, uint32_t selection, uint32_t outfit);
uint32_t defjam_fighter_caf_presentation(uint32_t participant, uint32_t selection);
#endif
