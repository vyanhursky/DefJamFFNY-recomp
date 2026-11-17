/* Custom Story clothing (src/patches/clothing.c, docs/custom-clothing.md). */
#ifndef DEFJAM_CLOTHING_H
#define DEFJAM_CLOTHING_H
#include <stdint.h>

/* Limits shared with setup/clothing_pack.py (a unit test keeps them equal). */
#define CLOTHING_MAX_ITEMS 256
#define CLOTHING_MAX_NAME 40
#define CLOTHING_MAX_FITS 64

/* Before the XBE loads, after the songs: read <data>/cache/clothing and serve the game's
 * database, garment archive and thumbnail archive with the items added. Chains to the
 * redirect installed before it. */
void clothing_start(const char *data_root, const char *game_dir);

/* After a profile load (sub_00014540, this = the profile manager). */
void clothing_after_load(uint32_t manager);

/* Every front-end call (the FuncCall hook), before it runs. */
void clothing_on_funccall(const char *text);

/* The string-table lookup (sub_00045180): a custom item's name when the game has none. */
uint32_t clothing_localized(uint32_t key, uint32_t native_value);

/* An item-state set (the profile's clothing, jewelry, ... sets; vtable 0x2862D4 for clothing)
 * was filled from the database (sub_000151C0, this = the set): keep only retail keys in it, so
 * the retail items keep their positions and the save's fixed state block stays the right size. */
void clothing_after_build(uint32_t set);

/* The set's methods, for a key of an added row. Returns 1 when it handled the call (the
 * result in *result), 0 to let the game's own method run. */
enum {
    CLOTHING_GET = 1,        /* sub_00017260 (key) -> state or -1 */
    CLOTHING_SET,            /* sub_000173A0 (key, state) */
    CLOTHING_OR_ALL,         /* sub_00017410 (handle, unused, bits): every colour */
    CLOTHING_ANY,            /* sub_00017310 (handle) -> the states of every colour, or'ed */
    CLOTHING_OR,             /* sub_00017480 (key, bits) */
    CLOTHING_CLEAR,          /* sub_000174D0 (key, bits) */
};
int clothing_set_call(int op, uint32_t set, uint32_t a1, uint32_t a2, uint32_t a3, uint32_t *result);

/* sub_000168E0 (state) set every item of a set to `state` (the retail cheats). */
void clothing_set_all(uint32_t set, uint32_t state);

/* sub_000D23B0 (name, row) copies a profile row into a save: added items are their base items
 * during the copy, and come back after it. */
void clothing_before_save(uint32_t row);
void clothing_after_save(void);

/* sub_000156D0 copied a profile row in from a save: added items worn when it was saved come back
 * (before the next front-end call), if their pack is enabled. */
void clothing_after_row_load(void);

/* For forks (FFNY Online): the clothing-set-1 digest of the enabled packs ("" when none); the
 * retail base handle of a clothing handle (the handle itself when it is not an added item); and a
 * part array (a Story hero's 38 appearance words) with every added item as its base item. */
const char *clothing_set_digest(void);
uint32_t clothing_base_handle(uint32_t handle);
void clothing_retail_parts(const uint32_t *parts, uint32_t *out, int count);

#endif
