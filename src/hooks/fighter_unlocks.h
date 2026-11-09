#ifndef DEFJAM_FIGHTER_UNLOCKS_H
#define DEFJAM_FIGHTER_UNLOCKS_H
#include <stddef.h>
#include <stdint.h>
#define FIGHTER_SETTINGS_SIZE 0x1490u
#define FIGHTER_UNLOCK_CAPACITY 80u
#define FIGHTER_UNLOCK_METADATA 0x00800000u
/* Native Options payload, not a complete MC02 file. No ownership/allocation. */
int fighter_unlocks_decode(const uint8_t *bytes, size_t size, uint32_t *count);
/* Only after successful decode, with index less than its returned count. */
uint32_t fighter_unlocks_at(const uint8_t *bytes, uint32_t index);
#endif
