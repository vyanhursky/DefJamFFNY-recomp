#ifndef DEFJAM_FIGHTER_CAF_H
#define DEFJAM_FIGHTER_CAF_H
#include <stddef.h>
#include <stdint.h>
int defjam_fighter_caf_start(void);
typedef struct CafContainer {
    uint32_t recipe_count, extras_count, extras_bytes, hd_count, hd_bytes, faces_count;
} CafContainer;
/* Decodes and bounds-checks a fighter-caf.bin header: sections must tile the file exactly. */
int defjam_fighter_caf_container(const uint8_t *data, size_t size, CafContainer *out);
void defjam_fighter_caf_participant(uint32_t service, uint32_t participant, uint32_t selection);
void defjam_fighter_caf_story(uint32_t service, uint32_t fighters);
void defjam_fighter_caf_begin_match(void);
uint32_t defjam_fighter_caf_selection(uint32_t participant);
void defjam_fighter_caf_clear(void);
int defjam_fighter_caf_visual(uint32_t visual, uint32_t participant, int apply);
int defjam_fighter_caf_context(uint32_t service, uint32_t participant, uint32_t *output);
int defjam_fighter_caf_audio(uint32_t input);
void defjam_fighter_caf_finishers(void);
void defjam_fighter_caf_menu_clear(uint32_t participant);
int defjam_fighter_caf_outfit(uint32_t participant, uint32_t selection, uint32_t outfit);
uint32_t defjam_fighter_caf_presentation(uint32_t participant, uint32_t selection);
#endif
