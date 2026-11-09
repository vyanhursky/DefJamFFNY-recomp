#include "fighter_names.h"
#include <string.h>

static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint16_t half(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }

int fighter_names_decode(FighterNames *out, const uint8_t *bytes, size_t size) {
    uint32_t count, text_size, text_offset, end = 0, previous = 0;
    if (!out) return 0;
    memset(out, 0, sizeof(*out));
    if (!bytes || size < 16 || size > FIGHTER_NAMES_MAX_FILE || memcmp(bytes, "FML1", 4) || word(bytes + 4) != 1) return 0;
    count = word(bytes + 8); text_size = word(bytes + 12);
    if (count > FIGHTER_NAMES_MAX_COUNT || text_size > FIGHTER_NAMES_MAX_TEXT) return 0;
    text_offset = 16 + count * 12;
    if (text_offset > size || text_size != size - text_offset) return 0;
    for (uint32_t i = 0; i < count; ++i) {
        const uint8_t *row = bytes + 16 + i * 12;
        uint32_t key = word(row), offset = word(row + 4), length = word(row + 8);
        const uint8_t *text;
        if ((i && key <= previous) || offset != end || length < 2 || (length & 1) || offset > text_size || length > text_size - offset) return 0;
        text = bytes + text_offset + offset;
        if (half(text + length - 2) != 0) return 0;
        for (uint32_t j = 0; j + 2 < length; j += 2) {
            uint16_t c = half(text + j);
            if (!c) return 0;
            if (c >= 0xD800 && c <= 0xDBFF) {
                uint16_t next;
                if (j + 4 >= length) return 0;
                next = half(text + j + 2);
                if (next < 0xDC00 || next > 0xDFFF) return 0;
                j += 2;
            } else if (c >= 0xDC00 && c <= 0xDFFF) return 0;
        }
        previous = key; end = offset + length;
    }
    if (end != text_size) return 0;
    out->bytes = bytes; out->size = size; out->count = count;
    out->text_offset = text_offset; out->text_size = text_size;
    return 1;
}

int fighter_names_find(const FighterNames *names, uint32_t key, uint32_t *offset, uint32_t *size) {
    uint32_t first = 0, end;
    if (!names || !names->bytes || !offset || !size) return 0;
    end = names->count;
    while (first < end) {
        uint32_t middle = first + (end - first) / 2;
        const uint8_t *row = names->bytes + 16 + middle * 12;
        uint32_t found = word(row);
        if (found == key) { *offset = word(row + 4); *size = word(row + 8); return 1; }
        if (found < key) first = middle + 1; else end = middle;
    }
    return 0;
}
