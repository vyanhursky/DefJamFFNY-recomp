#include "fighter_window.h"
#include <string.h>
#include <stdlib.h>
static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static int compare_word(const void *left, const void *right) {
    uint32_t a = *(const uint32_t *)left, b = *(const uint32_t *)right;
    return a < b ? -1 : a > b;
}
int fighter_window_at(const FighterWindow *w, uint32_t i, FighterWindowRow *out) {
    const uint8_t *p;
    if (!w || !w->bytes || !out || i >= w->count) return 0;
    p = w->bytes + 120 + i * 24;
    out->stable_handle = word(p); out->selection_key = word(p + 4); out->symbol_hash = word(p + 8);
    out->record_offset = word(p + 12); out->core_id = word(p + 16);
    return 1;
}
int fighter_window_decode(FighterWindow *out, const uint8_t *bytes, size_t size) {
    FighterWindow w = {0};
    uint32_t previous = 0;
    if (!out) return 0;
    memset(out, 0, sizeof *out);
    if (!bytes || size < 144 || size > FIGHTER_WINDOW_MAX_FILE || memcmp(bytes, "FWR1", 4)
        || word(bytes + 4) != 1 || word(bytes + 12) != FIGHTER_WINDOW_BANKS) return 0;
    w.bytes = bytes; w.count = word(bytes + 8); w.table = word(bytes + 16); w.sod_size = word(bytes + 20);
    if (!w.count || w.count > FIGHTER_WINDOW_MAX_COUNT || size != 120 + w.count * 24u
        || w.table > 255 || w.sod_size < 104 || w.sod_size > 64u * 1024u * 1024u) return 0;
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i) {
        const uint8_t *p = bytes + 24 + i * 24;
        FighterWindowBank *b = &w.banks[i];
        b->native_handle = word(p); b->private_handle = word(p + 4); b->symbol_hash = word(p + 8);
        b->selection_key = word(p + 12); b->record_offset = word(p + 16); b->core_id = word(p + 20);
        if (b->native_handle >> 24 != w.table || (b->native_handle & 0xffffffu) >= 0x7ffffcu
            || b->private_handle != (w.table << 24 | (0x7ffffcu + i)) || b->selection_key != 100u + i
            || b->record_offset % 4 || b->record_offset > w.sod_size - 104 || !b->core_id) return 0;
        for (uint32_t j = 0; j < i; ++j)
            if (w.banks[j].native_handle == b->native_handle || w.banks[j].symbol_hash == b->symbol_hash
                || w.banks[j].record_offset == b->record_offset) return 0;
    }
    for (uint32_t i = 0; i < w.count; ++i) {
        FighterWindowRow r;
        fighter_window_at(&w, i, &r);
        if (r.stable_handle >> 24 != w.table || (r.stable_handle & 0xffffffu) >= 0x7ffffcu
            || r.selection_key < 100 || r.selection_key > 0x7fffffffu || (i && r.selection_key <= previous)
            || r.record_offset % 4 || r.record_offset > w.sod_size - 104 || !r.core_id
            || word(bytes + 120 + i * 24 + 20)) return 0;
        /* Cross-domain identities/record ownership must also be unique. */
        for (uint32_t j = 0; j < FIGHTER_WINDOW_BANKS; ++j)
            if (r.record_offset == w.banks[j].record_offset || r.symbol_hash == w.banks[j].symbol_hash) return 0;
        previous = r.selection_key;
    }
    {
        uint32_t *keys = (uint32_t *)malloc(w.count * 3u * sizeof *keys);
        if (!keys) return 0;
        for (uint32_t i = 0; i < w.count; ++i) {
            FighterWindowRow row; fighter_window_at(&w, i, &row);
            keys[i] = row.stable_handle; keys[w.count + i] = row.symbol_hash; keys[w.count * 2u + i] = row.record_offset;
        }
        for (uint32_t domain = 0; domain < 3; ++domain) {
            uint32_t *first = keys + domain * w.count;
            qsort(first, w.count, sizeof *first, compare_word);
            for (uint32_t i = 1; i < w.count; ++i) if (first[i] == first[i - 1]) { free(keys); return 0; }
        }
        free(keys);
    }
    *out = w; return 1;
}
int fighter_window_find(const FighterWindow *w, uint32_t selection, uint32_t *index, FighterWindowRow *out) {
    uint32_t first = 0, end;
    if (!w || !w->bytes || !out) return 0;
    end = w->count;
    while (first < end) {
        uint32_t middle = first + (end - first) / 2;
        fighter_window_at(w, middle, out);
        if (out->selection_key == selection) { if (index) *index = middle; return 1; }
        if (out->selection_key < selection) first = middle + 1; else end = middle;
    }
    return 0;
}
int fighter_window_bind(FighterWindow *w, uint32_t participant, uint32_t selection, FighterWindowRow *out) {
    uint32_t index;
    if (!w || participant >= FIGHTER_WINDOW_BANKS || !fighter_window_find(w, selection, &index, out)
        || (w->frozen && w->selected[participant] != index + 1)) return 0;
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i)
        if (i != participant && w->selected[i] == index + 1) return 0;
    w->selected[participant] = index + 1; return 1;
}
int fighter_window_clear(FighterWindow *w, uint32_t participant) {
    if (!w || !w->bytes || w->frozen || (participant != UINT32_MAX && participant >= FIGHTER_WINDOW_BANKS)) return 0;
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i)
        if (participant == UINT32_MAX || participant == i) w->selected[i] = 0;
    return 1;
}
static int argument_space(unsigned char c) {
    return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f';
}
int fighter_window_integer(const char *text, int32_t *value) {
    uint32_t length, i = 0, magnitude = 0, negative = 0;
    if (!text || !value) return 0;
    for (length = 0; length < 40 && text[length]; ++length) {}
    if (length == 40) return 0;
    while (argument_space((unsigned char)text[i])) ++i;
    if (text[i] == '-' || text[i] == '+') { negative = text[i] == '-'; ++i; }
    if (text[i] < '0' || text[i] > '9') return 0;
    while (text[i] >= '0' && text[i] <= '9') {
        uint32_t digit = (uint32_t)(text[i++] - '0');
        if (magnitude > (2147483647u + negative - digit) / 10u) return 0;
        magnitude = magnitude * 10u + digit;
    }
    while (argument_space((unsigned char)text[i])) ++i;
    if (text[i]) return 0;
    *value = negative ? (int32_t)(-(int64_t)magnitude) : (int32_t)magnitude;
    return 1;
}
int fighter_window_command(FighterWindow *w, const char *command) {
    static const char prefix[] = "Fighters.KeepReady";
    const char *p; uint32_t mask;
    if (!command || strncmp(command, prefix, sizeof prefix - 1)) return 0;
    p = command + sizeof prefix - 1;
    if (*p++ != '(' || *p < '0' || *p > '9') return -1;
    mask = (uint32_t)(*p++ - '0');
    if (*p >= '0' && *p <= '9') {
        if (mask != 1 || *p > '5') return -1;
        mask = 10 + (uint32_t)(*p++ - '0');
    }
    if (*p++ != ')' || *p || !w || !w->bytes || w->frozen) return -1;
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i)
        if ((mask & (1u << i)) && !w->selected[i]) return -1;
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i)
        if (!(mask & (1u << i))) w->selected[i] = 0;
    return 1;
}
uint32_t fighter_window_native(const FighterWindow *w, uint32_t stable) {
    FighterWindowRow row;
    if (!w || !w->bytes) return UINT32_MAX;
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i) {
        if (w->banks[i].private_handle == stable) return w->banks[i].native_handle;
        if (w->selected[i] && fighter_window_at(w, w->selected[i] - 1, &row) && row.stable_handle == stable)
            return w->banks[i].native_handle;
    }
    return UINT32_MAX;
}
uint32_t fighter_window_stable(const FighterWindow *w, uint32_t native) {
    FighterWindowRow row;
    if (!w || !w->bytes) return UINT32_MAX;
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i) if (w->banks[i].native_handle == native)
        return w->selected[i] && fighter_window_at(w, w->selected[i] - 1, &row) ? row.stable_handle : w->banks[i].private_handle;
    return UINT32_MAX;
}
