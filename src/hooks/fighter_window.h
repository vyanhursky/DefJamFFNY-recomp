#ifndef DEFJAM_FIGHTER_WINDOW_H
#define DEFJAM_FIGHTER_WINDOW_H
#include <stddef.h>
#include <stdint.h>
#define FIGHTER_WINDOW_BANKS 4u
#define FIGHTER_WINDOW_MAX_COUNT 16380u
#define FIGHTER_WINDOW_MAX_FILE (120u + 24u * FIGHTER_WINDOW_MAX_COUNT)
typedef struct FighterWindowBank {
    uint32_t native_handle, private_handle, symbol_hash, selection_key, record_offset, core_id;
} FighterWindowBank;
typedef struct FighterWindowRow {
    /* FWR2: zero means independent; retail selection+1 includes native ID zero. */
    uint32_t stable_handle, selection_key, symbol_hash, record_offset, core_id, retail_selection_plus_one;
} FighterWindowRow;
typedef struct FighterWindow {
    const uint8_t *bytes;
    uint32_t count, table, sod_size;
    FighterWindowBank banks[FIGHTER_WINDOW_BANKS];
    /* Index+1, zero means unbound. No native ID is a persistent identity. */
    uint32_t selected[FIGHTER_WINDOW_BANKS];
    int frozen;
} FighterWindow;
int fighter_window_decode(FighterWindow *out, const uint8_t *bytes, size_t size);
int fighter_window_at(const FighterWindow *window, uint32_t index, FighterWindowRow *out);
int fighter_window_find(const FighterWindow *window, uint32_t selection, uint32_t *index, FighterWindowRow *out);
/* Rebinding a frozen match is forbidden; identical repeated submissions work. */
int fighter_window_bind(FighterWindow *window, uint32_t participant, uint32_t selection, FighterWindowRow *out);
/* UINT32_MAX clears all pre-match ownership. Never releases a frozen match. */
int fighter_window_clear(FighterWindow *window, uint32_t participant);
/* Fixed runtime-owned menu command: 0 unknown, 1 handled, -1 invalid/state mismatch.
 * Validates completely before changing any pre-match ownership. */
int fighter_window_command(FighterWindow *window, const char *command);
/* Bounded decimal native arguments, including the original menus' whitespace. */
int fighter_window_integer(const char *text, int32_t *value);
/* Ends selection ownership only; says nothing about model/resource teardown. */
int fighter_window_finish(FighterWindow *window);
uint32_t fighter_window_native(const FighterWindow *window, uint32_t stable);
uint32_t fighter_window_stable(const FighterWindow *window, uint32_t native);
#endif
