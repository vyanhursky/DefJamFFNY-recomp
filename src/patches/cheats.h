/* Cheats ([cheats] settings and the overlay's Cheats page). docs/cheats.md for players,
 * docs/research/cheat-menu.md for the fields. */
#ifndef DEFJAM_CHEATS_H
#define DEFJAM_CHEATS_H

#include <stddef.h>
#include <stdint.h>
#include "recomp_settings.h"

#ifdef __cplusplus
extern "C" {
#endif

/* The [cheats] settings, for pc_settings.c's one table. */
size_t cheats_settings(RecompSetting *out, size_t max);
/* Re-read the settings (start-up and every change). */
void cheats_apply_settings(void);

/* Guest-thread hooks, from src/recomp_manual.c. */
void cheats_fight_step(void);           /* sub_00087700_enter: one fight step is about to run */
void cheats_health_change(void);        /* sub_001A50B0_enter: a health change is about to apply */

/* The Story profile in use (the UI reads and changes it; the writes are single aligned words). */
typedef struct CheatsStory {
    int valid;              /* a profile slot is in use */
    int slot;               /* 0..15 */
    uint32_t cash;
    uint32_t dev_points;
} CheatsStory;
void cheats_story_read(CheatsStory *out);
#define CHEATS_STORY_MAX 999999u
int cheats_story_set_cash(uint32_t value);          /* 1 when written */
int cheats_story_set_dev_points(uint32_t value);

#ifdef __cplusplus
}
#endif

#endif
