#ifndef DEFJAM_FIGHTER_NAMES_H
#define DEFJAM_FIGHTER_NAMES_H
#include <stddef.h>
#include <stdint.h>

#define FIGHTER_NAMES_MAX_COUNT 16384u
#define FIGHTER_NAMES_MAX_TEXT (1024u * 1024u)
#define FIGHTER_NAMES_MAX_FILE (16u + FIGHTER_NAMES_MAX_COUNT * 12u + FIGHTER_NAMES_MAX_TEXT)

typedef struct FighterNames {
    const uint8_t *bytes;
    size_t size;
    uint32_t count, text_offset, text_size;
} FighterNames;

/* Borrowed immutable buffer; no addresses or executable instructions in FML1. */
int fighter_names_decode(FighterNames *out, const uint8_t *bytes, size_t size);
int fighter_names_find(const FighterNames *names, uint32_t key, uint32_t *offset, uint32_t *size);
#endif
