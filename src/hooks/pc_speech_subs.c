/*
 * Speech subtitles for in-game voices (fighter intros/extros, career player
 * voices, shops, taunts, tutorial, front-end, voicemail).
 *
 * File format (<mod_dir>/speech_subtitles.tsv, UTF-8):
 *   clip_key \t viv_id \t offset \t start_sec \t end_sec \t text_ptbr
 *
 * Multiple consecutive rows with the same (viv_id, offset) or clip_key form
 * timed segments of the same voice clip.
 */

#define _CRT_SECURE_NO_WARNINGS
#include "host.h"
#include "pc_speech_subs.h"
#include "recomp_settings.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
static uint64_t now_ms(void) { return (uint64_t)GetTickCount64(); }
#else
#include <time.h>
#ifndef _stricmp
#define _stricmp strcasecmp
#endif
static uint64_t now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000ull + (uint64_t)(ts.tv_nsec / 1000000ull);
}
#endif

typedef struct {
    char     clip_key[64];
    int      viv_id;
    uint32_t offset;
    uint32_t start_ms;
    uint32_t end_ms;
    char     text[256];
} SpeechSubRow;

static SpeechSubRow *g_rows = NULL;
static size_t        g_row_count = 0;
static size_t        g_row_cap = 0;
static int           g_loaded = 0;

/* Open handles to speech1.viv, speech2.viv, speech3.viv */
typedef struct {
    void *handle;
    int   viv_id;
} VivHandle;

#define MAX_VIV_HANDLES 16
static VivHandle g_viv_handles[MAX_VIV_HANDLES];

/* Currently playing clip state */
static int      g_active_viv = 0;
static uint32_t g_active_off = 0;
static char     g_active_key[64] = "";
static uint64_t g_active_start_ms = 0;

static void trigger_by_key(const char *clip_key);

static char g_intro_keys[4][64];
static int  g_intro_count = 0;
static char g_extro_keys[4][64];
static int  g_extro_count = 0;

void pc_speech_subs_clear_match(void)
{
    memset(g_intro_keys, 0, sizeof g_intro_keys);
    g_intro_count = 0;
    memset(g_extro_keys, 0, sizeof g_extro_keys);
    g_extro_count = 0;
}

void pc_speech_subs_reset(void)
{
    g_active_viv = 0;
    g_active_off = 0;
    g_active_key[0] = 0;
    g_active_start_ms = 0;
}

void pc_speech_subs_register_intro(const char *key)
{
    if (!key || !*key)
        return;
    for (int i = 0; i < g_intro_count && i < 4; i++) {
        if (!_stricmp(g_intro_keys[i], key))
            return;
    }
    if (g_intro_count < 4) {
        snprintf(g_intro_keys[g_intro_count++], sizeof g_intro_keys[0], "%s", key);
        fprintf(stderr, "[SUBS] registered match intro[%d]: %s\n", g_intro_count - 1, key);
    }
}

void pc_speech_subs_register_extro(const char *key)
{
    if (!key || !*key)
        return;
    for (int i = 0; i < g_extro_count && i < 4; i++) {
        if (!_stricmp(g_extro_keys[i], key))
            return;
    }
    if (g_extro_count < 4) {
        snprintf(g_extro_keys[g_extro_count++], sizeof g_extro_keys[0], "%s", key);
        fprintf(stderr, "[SUBS] registered match extro[%d]: %s\n", g_extro_count - 1, key);
    }
}

void pc_speech_subs_play_intro(uint32_t fighter_idx)
{
    if (fighter_idx < 4 && g_intro_keys[fighter_idx][0]) {
        fprintf(stderr, "[SUBS] playing fighter %u intro subtitle: %s\n", fighter_idx, g_intro_keys[fighter_idx]);
        trigger_by_key(g_intro_keys[fighter_idx]);
        g_intro_keys[fighter_idx][0] = '\0';
        return;
    }
    for (int i = 0; i < g_intro_count && i < 4; i++) {
        if (g_intro_keys[i][0]) {
            fprintf(stderr, "[SUBS] playing fallback[%d] intro subtitle for fighter %u: %s\n", i, fighter_idx, g_intro_keys[i]);
            trigger_by_key(g_intro_keys[i]);
            g_intro_keys[i][0] = '\0';
            return;
        }
    }
}

void pc_speech_subs_play_extro(uint32_t fighter_idx)
{
    if (fighter_idx < 4 && g_extro_keys[fighter_idx][0]) {
        fprintf(stderr, "[SUBS] playing fighter %u extro subtitle: %s\n", fighter_idx, g_extro_keys[fighter_idx]);
        trigger_by_key(g_extro_keys[fighter_idx]);
        g_extro_keys[fighter_idx][0] = '\0';
        return;
    }
    for (int i = 0; i < g_extro_count && i < 4; i++) {
        if (g_extro_keys[i][0]) {
            fprintf(stderr, "[SUBS] playing fallback[%d] extro subtitle for fighter %u: %s\n", i, fighter_idx, g_extro_keys[i]);
            trigger_by_key(g_extro_keys[i]);
            g_extro_keys[i][0] = '\0';
            return;
        }
    }
}

void pc_speech_subs_trigger_direct(const char *clip_key)
{
    trigger_by_key(clip_key);
}

static char *trim_ws(char *s)
{
    while (*s && (*s == ' ' || *s == '\r' || *s == '\n')) s++;
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\r' || s[n - 1] == '\n')) s[--n] = 0;
    return s;
}

void pc_speech_subs_load(const char *mod_dir)
{
    char path[1024], line[1024];
    FILE *f;

    g_row_count = 0;
    g_loaded = 0;
    g_active_viv = 0;
    g_active_off = 0;
    g_active_key[0] = 0;
    pc_speech_subs_clear_match();
    if (!mod_dir || !*mod_dir)
        return;

    snprintf(path, sizeof path, "%s" HOST_SEP "speech_subtitles.txt", mod_dir);
    f = fopen(path, "rb");
    if (!f) {
        snprintf(path, sizeof path, "%s" HOST_SEP "speech_subtitles.tsv", mod_dir);
        f = fopen(path, "rb");
    }
    if (!f)
        return;

    while (fgets(line, sizeof line, f)) {
        char *p = trim_ws(line);
        if (!*p || *p == '#')
            continue;
        /* Parse 6 tab-separated columns: clip_key, viv_id, offset, start_sec, end_sec, text */
        char *cols[6] = {0};
        int c = 0;
        cols[c++] = p;
        for (char *q = p; *q && c < 6; q++) {
            if (*q == '\t') {
                *q = 0;
                cols[c++] = q + 1;
            }
        }
        if (c < 6)
            continue;
        /* Strip UTF-8 BOM if on first row */
        if (!memcmp(cols[0], "\xEF\xBB\xBF", 3))
            cols[0] += 3;

        if (g_row_count >= g_row_cap) {
            size_t ncap = g_row_cap ? g_row_cap * 2 : 512;
            SpeechSubRow *nrow = (SpeechSubRow *)realloc(g_rows, ncap * sizeof(SpeechSubRow));
            if (!nrow) break;
            g_rows = nrow;
            g_row_cap = ncap;
        }
        SpeechSubRow *r = &g_rows[g_row_count++];
        snprintf(r->clip_key, sizeof r->clip_key, "%s", cols[0]);
        for (char *k = r->clip_key; *k; k++) {
            if (*k == '\\') *k = '/';
            else *k = (char)tolower((unsigned char)*k);
        }
        r->viv_id = atoi(cols[1]);
        r->offset = (uint32_t)strtoul(cols[2], NULL, 10);
        double st = atof(cols[3]);
        double en = atof(cols[4]);
        r->start_ms = st > 0.0 ? (uint32_t)(st * 1000.0 + 0.5) : 0u;
        r->end_ms   = en > 0.0 ? (uint32_t)(en * 1000.0 + 0.5) : 2500u;
        snprintf(r->text, sizeof r->text, "%s", trim_ws(cols[5]));
    }
    fclose(f);
    if (g_row_count > 0) {
        g_loaded = 1;
        fprintf(stderr, "[LANG] loaded %zu voice subtitle segment(s) from %s\n", g_row_count, path);
        fflush(stderr);
    }
}

int pc_speech_subs_enabled(void)
{
    if (!g_loaded || g_row_count == 0)
        return 0;
    /* [language] voice_subtitles: 0 = auto (on when pack has speech_subtitles.tsv), 1 = on, 2 = off */
    int choice = recomp_settings_get("language", "voice_subtitles", 0);
    if (choice == 2)
        return 0;
    return 1;
}

static void trigger_by_offset(int viv_id, uint32_t offset)
{
    if (!g_loaded || !viv_id || !offset)
        return;
    uint64_t t = now_ms();
    /* Debounce identical re-reads within 250 ms */
    if (g_active_viv == viv_id && g_active_off == offset && t - g_active_start_ms < 250)
        return;
    for (size_t i = 0; i < g_row_count; i++) {
        if (g_rows[i].viv_id == viv_id && g_rows[i].offset == offset) {
            /* Intro and extro clips are preloaded at match setup; skip SCHl read triggers
             * so they only display at the exact moment the fighter speaks in the cutscene. */
            if (!_strnicmp(g_rows[i].clip_key, "intro/", 6) || !_strnicmp(g_rows[i].clip_key, "extro/", 6))
                return;
            g_active_viv = viv_id;
            g_active_off = offset;
            snprintf(g_active_key, sizeof g_active_key, "%s", g_rows[i].clip_key);
            g_active_start_ms = t;
            fprintf(stderr, "[SUBS] voice clip triggered: %s (viv=%d off=%u)\n",
                    g_rows[i].clip_key, viv_id, offset);
            return;
        }
    }
}

static void trigger_by_key(const char *clip_key)
{
    if (!g_loaded || !clip_key || !*clip_key)
        return;
    uint64_t t = now_ms();
    if (!_stricmp(g_active_key, clip_key) && t - g_active_start_ms < 250)
        return;
    for (size_t i = 0; i < g_row_count; i++) {
        if (!_stricmp(g_rows[i].clip_key, clip_key)) {
            g_active_viv = g_rows[i].viv_id;
            g_active_off = g_rows[i].offset;
            snprintf(g_active_key, sizeof g_active_key, "%s", g_rows[i].clip_key);
            g_active_start_ms = t;
            fprintf(stderr, "[SUBS] voice clip triggered by path: %s\n", g_rows[i].clip_key);
            return;
        }
    }
}

/* Detect if an Xbox path is AUDIO\SPEECH1.VIV, SPEECH2.VIV, or SPEECH3.VIV */
static int match_speech_viv(const char *xbox_path)
{
    if (!xbox_path) return 0;
    const char *base = strrchr(xbox_path, '\\');
    const char *fwd  = strrchr(xbox_path, '/');
    if (fwd && (!base || fwd > base)) base = fwd;
    base = base ? base + 1 : xbox_path;
    if (!_stricmp(base, "speech1.viv")) return 1;
    if (!_stricmp(base, "speech2.viv")) return 2;
    if (!_stricmp(base, "speech3.viv")) return 3;
    return 0;
}

void xbox_speech_notify_open(const char *xbox_path, void *handle)
{
    int viv_id = match_speech_viv(xbox_path);
    if (!viv_id || !handle)
        return;
    for (int i = 0; i < MAX_VIV_HANDLES; i++) {
        if (g_viv_handles[i].handle == handle || !g_viv_handles[i].handle) {
            g_viv_handles[i].handle = handle;
            g_viv_handles[i].viv_id = viv_id;
            fprintf(stderr, "[SUBS] tracking speech%d.viv handle=%p\n", viv_id, handle);
            return;
        }
    }
    g_viv_handles[0].handle = handle;
    g_viv_handles[0].viv_id = viv_id;
}

void xbox_speech_notify_close(void *handle)
{
    if (!handle) return;
    for (int i = 0; i < MAX_VIV_HANDLES; i++) {
        if (g_viv_handles[i].handle == handle) {
            g_viv_handles[i].handle = NULL;
            g_viv_handles[i].viv_id = 0;
        }
    }
}

void xbox_speech_notify_read(void *handle, uint64_t offset, const void *buf, uint32_t len)
{
    if (!g_loaded || !handle || !buf || len < 4)
        return;
    const uint8_t *b = (const uint8_t *)buf;
    /* Every EA stream / bank clip starts with "SCHl" (0x53 0x43 0x48 0x6C) */
    if (b[0] != 'S' || b[1] != 'C' || b[2] != 'H' || b[3] != 'l')
        return;
    int viv_id = 0;
    for (int i = 0; i < MAX_VIV_HANDLES; i++) {
        if (g_viv_handles[i].handle == handle) {
            viv_id = g_viv_handles[i].viv_id;
            break;
        }
    }
    if (!viv_id)
        return;
    trigger_by_offset(viv_id, (uint32_t)offset);
}

void xbox_speech_notify_path(const char *xbox_path)
{
    if (!g_loaded || !xbox_path)
        return;
    /* Normalize path to lowercase with forward slashes and look for "speech/streams/" */
    char norm[256];
    size_t j = 0;
    for (size_t i = 0; xbox_path[i] && j + 1 < sizeof norm; i++) {
        char c = xbox_path[i];
        norm[j++] = (c == '\\') ? '/' : (char)tolower((unsigned char)c);
    }
    norm[j] = 0;
    const char *s = strstr(norm, "speech/streams/");
    if (!s)
        return;
    s += strlen("speech/streams/");
    char key[64];
    snprintf(key, sizeof key, "%s", s);
    char *dot = strrchr(key, '.');
    if (dot) *dot = 0;

    /* Intro and extro streams are preloaded during match setup. Register them
     * for this match and wait for the cutscene to actually trigger playback. */
    if (!_strnicmp(key, "intro/", 6)) {
        pc_speech_subs_register_intro(key);
        return;
    }
    if (!_strnicmp(key, "extro/", 6)) {
        pc_speech_subs_register_extro(key);
        return;
    }

    trigger_by_key(key);
}

int pc_speech_subs_current(char *out, size_t cap)
{
    if (!out || !cap)
        return 0;
    out[0] = 0;
    if (!pc_speech_subs_enabled())
        return 0;
    if (!g_active_viv && !g_active_key[0])
        return 0;

    uint64_t elapsed = now_ms() - g_active_start_ms;
    if (elapsed > 20000ull) {
        g_active_viv = 0;
        g_active_off = 0;
        g_active_key[0] = 0;
        return 0;
    }

    int any_future = 0;
    for (size_t i = 0; i < g_row_count; i++) {
        const SpeechSubRow *r = &g_rows[i];
        int match = (g_active_viv && g_active_off && r->viv_id == g_active_viv && r->offset == g_active_off)
                 || (g_active_key[0] && !strcmp(r->clip_key, g_active_key));
        if (!match)
            continue;
        if (elapsed <= (uint64_t)r->end_ms + 250ull)
            any_future = 1;
        if (elapsed >= (uint64_t)r->start_ms && elapsed <= (uint64_t)r->end_ms + 250ull) {
            snprintf(out, cap, "%s", r->text);
            return 1;
        }
    }
    if (!any_future) {
        g_active_viv = 0;
        g_active_off = 0;
        g_active_key[0] = 0;
    }
    return 0;
}
