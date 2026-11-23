#ifndef DEFJAM_FIGHTER_KEYS_H
#define DEFJAM_FIGHTER_KEYS_H
/* Which selection keys mark a fighter as ours. Same values as setup/fighter_keys.py, which says
 * what each one means; tests/unit/test_fighter_keys.py checks that the two files agree, and the
 * game refuses a fighter manifest compiled with another pair (pc_mods.cpp).
 *
 * The game's own fighters use keys below DEFJAM_FIGHTER_RETAIL_LIMIT, a fact of the game.
 * Custom fighters get logical keys from DEFJAM_FIGHTER_LOGICAL_FIRST up; during a match each is
 * mapped onto one of four native bank rows, DEFJAM_FIGHTER_BANK_FIRST to +3. A fork that uses
 * part of the range above the retail roster itself can move both, here and in the Python module.
 * Only the defaults are tested in the game by this project. */
#define DEFJAM_FIGHTER_RETAIL_LIMIT 100u
#ifndef DEFJAM_FIGHTER_BANK_FIRST
#define DEFJAM_FIGHTER_BANK_FIRST 100u
#endif
#ifndef DEFJAM_FIGHTER_LOGICAL_FIRST
#define DEFJAM_FIGHTER_LOGICAL_FIRST 100u
#endif
#if DEFJAM_FIGHTER_BANK_FIRST < DEFJAM_FIGHTER_RETAIL_LIMIT || DEFJAM_FIGHTER_BANK_FIRST > 124u
#error "DEFJAM_FIGHTER_BANK_FIRST must be 100 to 124"
#endif
#if DEFJAM_FIGHTER_LOGICAL_FIRST < DEFJAM_FIGHTER_RETAIL_LIMIT || DEFJAM_FIGHTER_LOGICAL_FIRST > 0x7ffffff0u
#error "DEFJAM_FIGHTER_LOGICAL_FIRST must be 100 to 0x7ffffff0"
#endif
#endif
