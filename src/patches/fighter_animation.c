/* Separate animation bank IDs retain native four-participant ownership.
 * No package addresses or fifth participant slot are introduced. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_config.h"
#include "fighter_animation.h"
#include "fighter_runtime.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>

#define ANIMATION_CORE_LIMIT 16384u
#define ANIMATION_TABLE_LIMIT (48u + 8u * (ANIMATION_CORE_LIMIT - 141u))
static uint32_t s_banks[ANIMATION_CORE_LIMIT], s_count;
static char s_archive[2048];

static uint32_t animation_word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static FILE *animation_open(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048)) return NULL;
    return _wfopen(wide, L"rb");
#else
    return fopen(path, "rb");
#endif
}
int defjam_fighter_animation_start(void) {
    const char *path = defjam_fighter_env("RECOMP_FIGHTER_ANIMATIONS");
    const char *bindings = defjam_fighter_env("RECOMP_FIGHTER_ANIMATION_BINDINGS");
    const char *hash = defjam_fighter_env("RECOMP_FIGHTER_ANIMATIONS_SHA256");
    if (!path || !*path) return (!bindings || !*bindings) && (!hash || !*hash);
    if (!defjam_fighter_research_active() || s_count || !bindings || !*bindings
        || strlen(bindings) >= 2048 || !defjam_fighter_file_matches(path, hash)) return 0;
    FILE *file = animation_open(bindings);
    if (!file) return 0;
    uint8_t *table = (uint8_t *)malloc(ANIMATION_TABLE_LIMIT + 1);
    if (!table) { fclose(file); return 0; }
    size_t size = fread(table, 1, ANIMATION_TABLE_LIMIT + 1, file);
    int valid = !ferror(file) && size >= 48 && size <= ANIMATION_TABLE_LIMIT;
    if (fclose(file)) valid = 0;
    uint32_t count = valid ? animation_word(table + 8) : 0;
    char encoded[65];
    if (valid) {
        hex(table + 16, encoded);
        valid = !memcmp(table, "FBA1", 4) && animation_word(table + 4) == 1 && count
            && count <= ANIMATION_CORE_LIMIT - 141 && size == 48u + count * 8u
            && !strcmp(encoded, hash);
    }
    if (valid) {
        file = animation_open(path);
        if (!file) valid = 0;
        else {
            valid = !fseek(file, 0, SEEK_END);
            long bytes = valid ? ftell(file) : -1;
            valid = valid && bytes >= 16 && (uint64_t)bytes <= (512ull << 20)
                && (uint32_t)bytes == animation_word(table + 12);
            if (fclose(file)) valid = 0;
        }
    }
    uint32_t previous = 140;
    for (uint32_t i = 0; valid && i < count; ++i) {
        uint32_t core = animation_word(table + 48 + i * 8), bank = animation_word(table + 52 + i * 8);
        if (core <= previous || core >= ANIMATION_CORE_LIMIT || bank < 1000 || bank > 99999) {
            valid = 0; break;
        }
        s_banks[core] = bank; previous = core;
    }
    if (valid) {
        s_count = count; strcpy(s_archive, path);
        fprintf(stderr, "[FIGHTERS] validated %u core-to-animation bindings\n", count);
    }
    free(table); return valid;
}
const char *defjam_fighter_animation_path(void) { return s_archive; }
uint32_t defjam_fighter_animation_bank(uint32_t character_core, uint32_t inherited) {
    if (!s_count || !defjam_fighter_research_active() || !character_core
        || character_core > ANIMATION_CORE_LIMIT || !s_banks[character_core - 1]) return inherited;
    uint32_t bank = s_banks[character_core - 1];
    fprintf(stderr, "[FIGHTERS] core %u loads owned animation bank %u\n", character_core - 1, bank);
    return bank;
}
