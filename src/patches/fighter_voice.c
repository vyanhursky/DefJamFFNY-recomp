/* Owned voice IDs have a separate namespace from fighter cores and inherited
 * audio templates. Research-only activation uses a compiler-owned archive.
 * Native HDR allocation, bank registration and unloading retain ownership.
 */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_voice.h"
#include "fighter_runtime.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>

#define VOICE_CORE_LIMIT 16384u
#define VOICE_TABLE_LIMIT (48u + 8u * (VOICE_CORE_LIMIT - 141u))
#define STEM_LIMIT 76u
#define STEM_BYTES 96u
static uint16_t s_voices[VOICE_CORE_LIMIT];
static uint32_t s_selected[4], s_count, s_observed;
static char s_archive[2048];
extern void sub_0001C960(void);

static void voice_stop(const char *message) {
    fprintf(stderr, "[FIGHTERS] voice stopped: %s\n", message);
    fflush(stderr); exit(1);
}
static uint32_t voice_word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static FILE *voice_open(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048)) return NULL;
    return _wfopen(wide, L"rb");
#else
    return fopen(path, "rb");
#endif
}
int defjam_fighter_voice_start(void) {
    const char *path = getenv("RECOMP_FIGHTER_VOICES");
    const char *bindings = getenv("RECOMP_FIGHTER_VOICE_BINDINGS");
    const char *hash = getenv("RECOMP_FIGHTER_VOICES_SHA256");
    if (!path || !*path) return (!bindings || !*bindings) && (!hash || !*hash);
    if (!defjam_fighter_research_active() || s_count || !bindings || !*bindings
        || strlen(bindings) >= 2048 || !mod_file_matches(path, hash)) return 0;
    FILE *file = voice_open(bindings);
    if (!file) return 0;
    uint8_t *table = (uint8_t *)malloc(VOICE_TABLE_LIMIT + 1);
    if (!table) { fclose(file); return 0; }
    size_t size = fread(table, 1, VOICE_TABLE_LIMIT + 1, file);
    int valid = !ferror(file) && size >= 48 && size <= VOICE_TABLE_LIMIT;
    if (fclose(file)) valid = 0;
    uint32_t count = valid ? voice_word(table + 8) : 0;
    char encoded[65];
    if (valid) {
        hex(table + 16, encoded);
        valid = !memcmp(table, "FVA1", 4) && voice_word(table + 4) == 1 && count
            && count <= VOICE_CORE_LIMIT - 141 && size == 48u + count * 8u
            && !strcmp(encoded, hash);
    }
    if (valid) {
        file = voice_open(path);
        if (!file) valid = 0;
        else {
            valid = !fseek(file, 0, SEEK_END);
            long bytes = valid ? ftell(file) : -1;
            valid = valid && bytes >= 16 && (uint64_t)bytes <= (512ull << 20)
                && (uint32_t)bytes == voice_word(table + 12);
            if (fclose(file)) valid = 0;
        }
    }
    memset(s_voices, 0xFF, sizeof(s_voices));
    uint32_t previous = 140;
    for (uint32_t i = 0; valid && i < count; ++i) {
        uint32_t core = voice_word(table + 48 + i * 8), voice = voice_word(table + 52 + i * 8);
        if (core <= previous || core >= VOICE_CORE_LIMIT || voice < 600 || voice >= 65535) {
            valid = 0; break;
        }
        s_voices[core] = (uint16_t)voice; previous = core;
    }
    if (valid) {
        s_count = count; strcpy(s_archive, path);
        for (unsigned i = 0; i < 4; ++i) s_selected[i] = UINT32_MAX;
        fprintf(stderr, "[FIGHTERS] validated %u core-to-voice bindings\n", count);
    }
    free(table); return valid;
}
const char *defjam_fighter_voice_path(void) { return s_archive; }
void defjam_fighter_voice_select(uint32_t input) {
    if (!s_count || !defjam_fighter_research_active() || MEM8(0x340540)) return;
    for (uint32_t slot = 0; slot < 4; ++slot) {
        uint32_t core = MEM32(input + 0x20 + slot * 0x18);
        s_selected[slot] = core && core <= VOICE_CORE_LIMIT && s_voices[core - 1] != UINT16_MAX
            ? s_voices[core - 1] : UINT32_MAX;
    }
}
static void add_stem(char stems[STEM_LIMIT][STEM_BYTES], uint32_t *count, const char *value) {
    if (*count >= STEM_LIMIT || strlen(value) >= STEM_BYTES) voice_stop("resource stem budget");
    strcpy(stems[(*count)++], value);
}
static int compare_stems(const void *left, const void *right) {
    return strcmp((const char *)left, (const char *)right);
}
int defjam_fighter_voice_load(uint32_t selector) {
    if (!s_count || !defjam_fighter_research_active()) return 0;
    int changed = 0;
    for (uint32_t slot = 0; slot < 4; ++slot)
        if (s_selected[slot] != UINT32_MAX && MEM32(0x3403A4 + slot * 0x64) != UINT32_MAX) changed = 1;
    if (!changed) return 0;

    char stems[STEM_LIMIT][STEM_BYTES], name[STEM_BYTES];
    uint32_t count = 0, seen[4], seen_count = 0;
    uint32_t names = (selector & 255) ? 0x2DD8B8 : MEM8(0x33EBC0) ? 0x2DD6E0 : 0;
    if (names) {
        uint32_t i;
        for (i = 0; i < 64; ++i) {
            uint32_t text = MEM32(names + i * 4);
            if (!text) break;
            size_t length = 0;
            while (length < 64 && MEM8(text + (uint32_t)length)) ++length;
            if (length == 64) voice_stop("supplemental native name exceeds budget");
            int written = snprintf(name, sizeof(name), "speech/%s/%.*s",
                (selector & 255) ? "Tutorial" : "Heckles", (int)length, (const char *)XBOX_PTR(text));
            if (written < 0 || written >= (int)sizeof(name)) voice_stop("supplemental stem exceeds budget");
            add_stem(stems, &count, name);
        }
        if (i == 64) voice_stop("unterminated supplemental resource list");
    }
    static const char *categories[3] = {"Character", "Taunts", "Enviro"};
    for (uint32_t slot = 0; slot < 4; ++slot) {
        uint32_t row = 0x3403A4 + slot * 0x64;
        if (MEM32(row) == UINT32_MAX) { MEM8(row + 0x15) = 0; continue; }
        if (s_selected[slot] != UINT32_MAX) MEM32(row + 0x10) = s_selected[slot];
        uint32_t voice = MEM32(row + 0x10);
        if (voice == UINT32_MAX) continue;
        if (voice >= 65535) voice_stop("bank ID exceeds native WORD namespace");
        int found = 0;
        for (uint32_t i = 0; i < seen_count; ++i) if (seen[i] == voice) found = 1;
        if (!found) {
            seen[seen_count++] = voice;
            for (unsigned category = 0; category < 3; ++category) {
                int written = snprintf(name, sizeof(name), "speech/%s/Def_Jam_%sCharacters/%03u",
                    categories[category], voice >= 500 ? "IP_" : "", voice);
                if (written < 0 || written >= (int)sizeof(name)) voice_stop("bank stem exceeds budget");
                add_stem(stems, &count, name);
            }
        }
        MEM8(row + 0x15) = 1;
    }
    uint32_t available = 0;
    for (uint32_t i = 0; i < 256; ++i) if (MEM32(0x332330 + i * 0x88) == UINT32_MAX) ++available;
    if (available < count) voice_stop("native paired-resource cache has insufficient free slots");
    qsort(stems, count, sizeof(stems[0]), compare_stems);
    uint32_t stack = g_esp;
    if (stack < 0x1100) voice_stop("invalid loader stack");
    g_esp -= 0x100;
    uint32_t args[2] = {g_esp, 0x290E24};
    for (uint32_t i = 0; i < count; ++i) {
        memcpy((void *)XBOX_PTR(args[0]), stems[i], strlen(stems[i]) + 1);
        uint32_t result = guest_call(sub_0001C960, g_ecx, 2, args);
        if (result >= 256) voice_stop("native bank registration failed");
    }
    g_esp = stack + 4; g_eax = 0;
    fprintf(stderr, "[FIGHTERS] voice resources loaded: %u banks, IDs %u/%u/%u/%u\n",
        count, MEM32(0x3403B4), MEM32(0x340418), MEM32(0x34047C), MEM32(0x3404E0));
    return 1;
}
void defjam_fighter_voice_observe(uint32_t family, uint32_t voice, uint32_t result) {
    /* The native lookup accepts WORD keys; callers may leave high register
     * bits dirty when forwarding those arguments. Row zero is a valid hit. */
    family &= UINT16_MAX; voice &= UINT16_MAX;
    if (!s_count || voice < 600 || s_observed >= 64) return;
    ++s_observed;
    fprintf(stderr, "[FIGHTERS] voice request family=%u voice=%u bank_row=%u\n", family, voice, result & 65535);
}
