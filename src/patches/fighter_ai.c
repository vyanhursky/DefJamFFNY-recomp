/* Data-only profile bindings retain native stage and AI record ownership. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_ai.h"
#include "fighter_runtime.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>

#define AI_CORE_LIMIT 16384u
#define AI_TABLE_LIMIT (48u + 36u * (AI_CORE_LIMIT - 141u))
static char s_profiles[AI_CORE_LIMIT][32];
static uint32_t s_count;
static char s_archive[2048];

static uint32_t ai_word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static FILE *ai_open(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048)) return NULL;
    return _wfopen(wide, L"rb");
#else
    return fopen(path, "rb");
#endif
}
int defjam_fighter_ai_start(void) {
    const char *path = getenv("RECOMP_FIGHTER_AI");
    const char *bindings = getenv("RECOMP_FIGHTER_AI_BINDINGS");
    const char *hash = getenv("RECOMP_FIGHTER_AI_SHA256");
    if (!path || !*path) return (!bindings || !*bindings) && (!hash || !*hash);
    if (!defjam_fighter_research_active() || s_count || !bindings || !*bindings
        || strlen(bindings) >= 2048 || !mod_file_matches(path, hash)) return 0;
    FILE *file = ai_open(bindings);
    if (!file) return 0;
    uint8_t *table = (uint8_t *)malloc(AI_TABLE_LIMIT + 1);
    if (!table) { fclose(file); return 0; }
    size_t size = fread(table, 1, AI_TABLE_LIMIT + 1, file);
    int valid = !ferror(file) && size >= 48 && size <= AI_TABLE_LIMIT;
    if (fclose(file)) valid = 0;
    uint32_t count = valid ? ai_word(table + 8) : 0;
    char encoded[65];
    if (valid) {
        hex(table + 16, encoded);
        valid = !memcmp(table, "FIA1", 4) && ai_word(table + 4) == 1 && count
            && count <= AI_CORE_LIMIT - 141 && size == 48u + count * 36u
            && !strcmp(encoded, hash);
    }
    if (valid) {
        file = ai_open(path);
        if (!file) valid = 0;
        else {
            valid = !fseek(file, 0, SEEK_END);
            long bytes = valid ? ftell(file) : -1;
            valid = valid && bytes >= 16 && (uint64_t)bytes <= (512ull << 20)
                && (uint32_t)bytes == ai_word(table + 12);
            if (fclose(file)) valid = 0;
        }
    }
    uint32_t previous = 140;
    memset(s_profiles, 0, sizeof(s_profiles));
    for (uint32_t i = 0; valid && i < count; ++i) {
        const uint8_t *row = table + 48 + i * 36;
        uint32_t core = ai_word(row);
        if (core <= previous || core >= AI_CORE_LIMIT || !row[4]) { valid = 0; break; }
        int ended = 0;
        for (unsigned j = 4; j < 36; ++j) {
            uint8_t c = row[j];
            if (!c) ended = 1;
            else if (ended || !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                     || (c >= '0' && c <= '9') || c == '_' || c == '-')) { valid = 0; break; }
        }
        if (!ended) valid = 0;
        if (valid) { memcpy(s_profiles[core], row + 4, 32); previous = core; }
    }
    if (valid) {
        s_count = count; strcpy(s_archive, path);
        fprintf(stderr, "[FIGHTERS] validated %u core-to-AI bindings\n", count);
    }
    free(table); return valid;
}
const char *defjam_fighter_ai_path(void) { return s_archive; }
/* C9110 consumes writable D6EE0 configuration. The four profile strings are
 * independent of its stage, controller flags and four native owned AI records. */
void defjam_fighter_ai_bind(uint32_t config) {
    if (!s_count || !defjam_fighter_research_active()) return;
    for (unsigned slot = 0; slot < 4; ++slot) {
        uint32_t core = MEM32(0x3B90B8 + slot * 4);
        if (core >= AI_CORE_LIMIT || !s_profiles[core][0] || !MEM8(config + 0x24 + slot * 32)) continue;
        memcpy(XBOX_PTR(config + 0x24 + slot * 32), s_profiles[core], 32);
        fprintf(stderr, "[FIGHTERS] AI slot %u core %u profile %s\n", slot, core, s_profiles[core]);
    }
}
void defjam_fighter_ai_loaded(uint32_t self, uint32_t config) {
    if (!s_count || !defjam_fighter_research_active()) return;
    for (unsigned slot = 0; slot < 4; ++slot) {
        uint32_t core = MEM32(0x3B90B8 + slot * 4);
        if (core >= AI_CORE_LIMIT || !s_profiles[core][0] || !MEM8(config + 0x24 + slot * 32)) continue;
        if (memcmp(XBOX_PTR(config + 0x24 + slot * 32), s_profiles[core], 32)) {
            fprintf(stderr, "[FIGHTERS] AI stopped: owned profile fell back in slot %u\n", slot);
            fflush(stderr); exit(1);
        }
        for (unsigned row = 0; row < 4; ++row) {
            uint32_t record = self + 4 + slot * 0x890 + row * 0x60;
            fprintf(stderr, "[FIGHTERS] AI parsed slot %u core %u tendency %u:", slot, core, row);
            for (unsigned field = 0; field < 24; ++field) fprintf(stderr, " %d", (int32_t)MEM32(record + field * 4));
            fprintf(stderr, "\n");
        }
    }
}
