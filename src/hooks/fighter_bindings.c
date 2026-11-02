#include "fighter_bindings.h"
#include <string.h>

static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint32_t field(const FighterBindings *b, uint32_t index, uint32_t offset) {
    return word(b->bytes + 24 + index * 24 + offset);
}
int fighter_bindings_at(const FighterBindings *b, uint32_t index, FighterBinding *out) {
    if (!b || !b->bytes || !out || index >= b->count) return 0;
    out->stable_handle = field(b, index, 0); out->native_handle = field(b, index, 4);
    out->symbol_hash = field(b, index, 8); out->selection_key = field(b, index, 12);
    out->core_id = field(b, index, 16); out->flags = field(b, index, 20);
    return 1;
}
int fighter_bindings_decode(FighterBindings *out, const uint8_t *bytes, size_t size) {
    FighterBindings b = {0};
    uint32_t active = 0, previous = 0;
    if (!out) return 0;
    memset(out, 0, sizeof(*out));
    if (!bytes || size < 24 || size > FIGHTER_BINDINGS_MAX_FILE || memcmp(bytes, "FMB1", 4)
        || word(bytes + 4) != 1 || word(bytes + 20)) return 0;
    b.bytes = bytes; b.count = word(bytes + 8); b.active_count = word(bytes + 12); b.table = word(bytes + 16);
    if (!b.count || b.count > FIGHTER_BINDINGS_MAX_COUNT || b.active_count > b.count || b.table >= 256
        || size != 24u + b.count * 32u + b.active_count * 4u) return 0;
    b.native_index = 24 + b.count * 24;
    b.symbol_index = b.native_index + b.active_count * 4;
    b.selection_index = b.symbol_index + b.count * 4;
    for (uint32_t i = 0; i < b.count; ++i) {
        FighterBinding row;
        fighter_bindings_at(&b, i, &row);
        if ((i && row.stable_handle <= previous) || row.stable_handle >> 24 != b.table
            || (row.stable_handle & 0xffffffu) >= 0x800000u || row.flags > 3
            || row.selection_key > 0x7fffffffu || ((row.flags & 1) && row.selection_key < 100)) return 0;
        if (row.flags & 2) {
            if (row.native_handle == UINT32_MAX || row.native_handle >> 24 != b.table
                || (row.native_handle & 0xffffffu) >= 0x800000u || !row.core_id || row.core_id > 0x7fffffffu) return 0;
            ++active;
        } else if (row.native_handle != UINT32_MAX || row.core_id) return 0;
        previous = row.stable_handle;
    }
    if (active != b.active_count) return 0;
    /* Each index is a complete permutation: strict unique values and the exact
     * corresponding population size exclude duplicates and omitted rows. */
    for (uint32_t domain = 0; domain < 3; ++domain) {
        uint32_t offset = domain == 0 ? b.native_index : domain == 1 ? b.symbol_index : b.selection_index;
        uint32_t count = domain == 0 ? b.active_count : b.count;
        previous = 0;
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t index = word(bytes + offset + i * 4), value;
            if (index >= b.count || (!domain && !(field(&b, index, 20) & 2))) return 0;
            value = field(&b, index, 4 + domain * 4);
            if (i && value <= previous) return 0;
            previous = value;
        }
    }
    *out = b;
    return 1;
}
int fighter_bindings_find(const FighterBindings *b, FighterBindingKey domain, uint32_t key, FighterBinding *out) {
    uint32_t first = 0, end, offset = 0, column = 0;
    if (!b || !b->bytes || !out || domain < FIGHTER_BINDING_STABLE || domain > FIGHTER_BINDING_SELECTION) return 0;
    end = b->count;
    if (domain == FIGHTER_BINDING_NATIVE) { end = b->active_count; offset = b->native_index; column = 4; }
    else if (domain == FIGHTER_BINDING_SYMBOL) { offset = b->symbol_index; column = 8; }
    else if (domain == FIGHTER_BINDING_SELECTION) { offset = b->selection_index; column = 12; }
    while (first < end) {
        uint32_t middle = first + (end - first) / 2;
        uint32_t index = domain == FIGHTER_BINDING_STABLE ? middle : word(b->bytes + offset + middle * 4);
        uint32_t value = field(b, index, column);
        if (value == key) return fighter_bindings_at(b, index, out);
        if (value < key) first = middle + 1; else end = middle;
    }
    return 0;
}
