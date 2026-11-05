/* Independent simple intro/victory bindings, with native resource ownership. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_cinematic.h"
#include "fighter_runtime.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>

#define CIN_CORE_LIMIT 16384u
#define CIN_TABLE_LIMIT (88u + 20u * (CIN_CORE_LIMIT - 141u))
static char s_clips[CIN_CORE_LIMIT][2][8];
static uint32_t s_count;
static char s_archive[2048];
static RECOMP_TLS uint64_t s_context;

static uint32_t cin_word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static FILE *cin_open(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048)) return NULL;
    return _wfopen(wide, L"rb");
#else
    return fopen(path, "rb");
#endif
}
static void cin_stop(const char *message) {
    fprintf(stderr, "[FIGHTERS] cinematic stopped: %s\n", message);
    fflush(stderr); exit(1);
}
static int cin_size(const char *path, uint32_t expected) {
    FILE *file = cin_open(path);
    if (!file) return 0;
    int ok = !fseek(file, 0, SEEK_END);
    long size = ok ? ftell(file) : -1;
    ok = ok && size >= 16 && (uint64_t)size <= (512ull << 20) && (uint32_t)size == expected;
    if (fclose(file)) ok = 0;
    return ok;
}
int defjam_fighter_cinematic_start(void) {
    const char *path = getenv("RECOMP_FIGHTER_CINEMATIC_BANKS");
    const char *bindings = getenv("RECOMP_FIGHTER_CINEMATIC_BINDINGS");
    const char *hash = getenv("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256");
    const char *nis = getenv("RECOMP_FIGHTER_RESEARCH_CINEMATICS");
    const char *nis_hash = getenv("RECOMP_FIGHTER_RESEARCH_CINEMATICS_SHA256");
    if (!path || !*path) return (!bindings || !*bindings) && (!hash || !*hash);
    if (!defjam_fighter_research_active() || s_count || !bindings || !*bindings
        || strlen(path) >= sizeof s_archive || strlen(bindings) >= 2048 || !nis || !*nis
        || !mod_file_matches(path, hash) || !mod_file_matches(nis, nis_hash)) return 0;
    FILE *file = cin_open(bindings);
    if (!file) return 0;
    uint8_t *table = (uint8_t *)malloc(CIN_TABLE_LIMIT + 1);
    if (!table) { fclose(file); return 0; }
    size_t size = fread(table, 1, CIN_TABLE_LIMIT + 1, file);
    int valid = !ferror(file) && size >= 88 && size <= CIN_TABLE_LIMIT;
    if (fclose(file)) valid = 0;
    uint32_t count = valid ? cin_word(table + 8) : 0;
    char banks_digest[65], nis_digest[65];
    if (valid) {
        hex(table + 24, banks_digest); hex(table + 56, nis_digest);
        valid = !memcmp(table, "FIC1", 4) && cin_word(table + 4) == 1 && count
            && count <= CIN_CORE_LIMIT - 141 && size == 88u + count * 20u
            && cin_word(table + 20) == 0 && !strcmp(banks_digest, hash) && !strcmp(nis_digest, nis_hash)
            && cin_size(path, cin_word(table + 12)) && cin_size(nis, cin_word(table + 16));
    }
    uint32_t previous = 140;
    memset(s_clips, 0, sizeof s_clips);
    for (uint32_t i = 0; valid && i < count; ++i) {
        const uint8_t *row = table + 88 + i * 20;
        uint32_t core = cin_word(row);
        if (core <= previous || core >= CIN_CORE_LIMIT) { valid = 0; break; }
        for (unsigned category = 0; category < 2; ++category) {
            const uint8_t *name = row + 4 + category * 8;
            if (name[0] != 'F' || name[1] != (category ? 'V' : 'I') || name[7]) valid = 0;
            for (unsigned j = 2; j < 7; ++j) if (name[j] < '0' || name[j] > '9') valid = 0;
        }
        if (valid) { memcpy(s_clips[core], row + 4, 16); previous = core; }
    }
    if (valid) {
        s_count = count; strcpy(s_archive, path);
        fprintf(stderr, "[FIGHTERS] validated %u independent cinematic bindings\n", count);
    }
    free(table); return valid;
}
const char *defjam_fighter_cinematic_path(void) { return s_archive; }

/* 87AF0's request supplies the actual visual-table participant. Its camera
 * selector is a different field; descriptor allocation order is irrelevant. */
uint64_t defjam_fighter_cinematic_enter(uint32_t manager, uint32_t descriptor, uint32_t request) {
    uint64_t previous = s_context;
    s_context = 0;
    if (!s_count || !defjam_fighter_research_active() || MEM32(request) != 1 || MEM32(request + 12) > 1)
        return previous;
    uint32_t slot = MEM32(request + 4);
    if (slot >= 4) return previous;
    uint32_t core = MEM32(0x3B90B8 + slot * 4);
    if (core >= CIN_CORE_LIMIT || !s_clips[core][0][0]) return previous;
    uint32_t config = MEM32(manager + 0x2FF5C);
    if (!config || MEM32(config + 0xA8 + slot * 4) != core + 1)
        cin_stop("participant core differs from native cinematic configuration");
    if (MEM32(manager + 0x2B9EC) & 0x02000000u)
        cin_stop("owned simple sequence cannot use the two-actor cinematic path");
    s_context = ((uint64_t)descriptor << 32) | core;
    return previous;
}
void defjam_fighter_cinematic_leave(uint64_t previous, uint32_t request) {
    if (s_context && MEM32(request + 0x20) != 1)
        cin_stop("owned simple sequence has unexpected actor ownership");
    s_context = previous;
}
void defjam_fighter_cinematic_name(uint32_t descriptor) {
    if (!s_context || (uint32_t)(s_context >> 32) != descriptor || !defjam_fighter_research_active()) return;
    char label[9];
    snprintf(label, sizeof label, "fmc%05u", (uint32_t)s_context);
    memcpy(XBOX_PTR(descriptor + 0xA8), label, sizeof label);
}
void defjam_fighter_cinematic_selected(uint32_t descriptor, uint32_t name) {
    if (!s_count || !defjam_fighter_research_active()) return;
    const uint8_t *label = (const uint8_t *)XBOX_PTR(descriptor + 0xA8);
    if (memcmp(label, "fmc", 3) || label[8]) return;
    uint32_t core = 0;
    for (unsigned i = 3; i < 8; ++i) {
        if (label[i] < '0' || label[i] > '9') return;
        core = core * 10 + label[i] - '0';
    }
    if (core >= CIN_CORE_LIMIT || !s_clips[core][0][0]) return;
    uint32_t category = MEM32(descriptor + 0xA4);
    if (MEM32(descriptor + 0x19C) != 1 || category > 1
        || memcmp(XBOX_PTR(name), s_clips[core][category], 8))
        cin_stop("native XML selected a different owned cinematic");
    fprintf(stderr, "[FIGHTERS] cinematic core %u category %u selected %s\n", core, category, s_clips[core][category]);
}
