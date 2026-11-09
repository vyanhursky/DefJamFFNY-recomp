#ifndef DEFJAM_FIGHTER_BINDINGS_H
#define DEFJAM_FIGHTER_BINDINGS_H
#include <stddef.h>
#include <stdint.h>

#define FIGHTER_BINDINGS_MAX_COUNT 16384u
#define FIGHTER_BINDINGS_MAX_FILE (24u + 36u * FIGHTER_BINDINGS_MAX_COUNT)
#define FIGHTER_HANDLE_ABSENT UINT32_MAX
typedef enum FighterBindingKey {
    FIGHTER_BINDING_STABLE, FIGHTER_BINDING_NATIVE, FIGHTER_BINDING_SYMBOL, FIGHTER_BINDING_SELECTION
} FighterBindingKey;
typedef struct FighterBinding {
    uint32_t stable_handle, native_handle, symbol_hash, selection_key, core_id, flags;
} FighterBinding;
typedef struct FighterBindings {
    const uint8_t *bytes;
    uint32_t count, active_count, table, native_index, symbol_index, selection_index;
} FighterBindings;
/* Borrows immutable storage. No guest pointers or executable instructions. */
int fighter_bindings_decode(FighterBindings *out, const uint8_t *bytes, size_t size);
int fighter_bindings_at(const FighterBindings *bindings, uint32_t index, FighterBinding *out);
int fighter_bindings_find(const FighterBindings *bindings, FighterBindingKey domain, uint32_t key, FighterBinding *out);
#endif
