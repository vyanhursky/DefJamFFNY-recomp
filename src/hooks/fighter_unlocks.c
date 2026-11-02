#include "fighter_unlocks.h"
static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
uint32_t fighter_unlocks_at(const uint8_t *bytes, uint32_t index) {
    return word(bytes + 0x1294 + index * 4);
}
int fighter_unlocks_decode(const uint8_t *bytes, size_t size, uint32_t *count) {
    uint32_t n, previous = 0;
    if (!count) return 0;
    *count = 0;
    if (!bytes || size != FIGHTER_SETTINGS_SIZE || word(bytes + 0x1290) != UINT32_MAX) return 0;
    n = word(bytes + 0x1218);
    if (n > FIGHTER_UNLOCK_CAPACITY) return 0;
    for (uint32_t i = 0; i < n; ++i) {
        uint32_t identity = fighter_unlocks_at(bytes, i) & ~FIGHTER_UNLOCK_METADATA;
        if (i && identity <= previous) return 0;
        previous = identity;
    }
    *count = n;
    return 1;
}
