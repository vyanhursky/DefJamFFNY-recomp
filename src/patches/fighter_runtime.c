#define _CRT_SECURE_NO_WARNINGS
#include "fighter_config.h"
#include "fighter_runtime.h"
#include "fighter_fatal.h"
#include "fighter_caf.h"
#include "fighter_motion.h"
#include "fighter_voice.h"
#include "fighter_animation.h"
#include "fighter_ai.h"
#include "fighter_cinematic.h"
#include "fighter_finishers.h"
#include "fighter_events.h"
#include "fighter_film_proof.h"
#include "hooks/fighter_names.h"
#include "hooks/fighter_roster.h"
#include "hooks/fighter_bindings.h"
#include "hooks/fighter_unlocks.h"
#include "hooks/fighter_window.h"
#include "hooks/guest_call.h"
#include "hooks/pc_language.h"
#include "host.h"
#include "hooks/mod_sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#if defined(_WIN32)
#include <io.h>
#include <direct.h>
#else
#include <unistd.h>
#include <sys/stat.h>
#endif
#if !defined(_WIN32)
#include <sched.h>
#endif

extern void sub_00029680(void);
extern void sub_00045180(void);
extern void sub_000BE760(void);
extern void sub_000BE760_gen(void);
extern void sub_0001E310(void);
/* Toolkit allocator counters; diagnostic observations, not asset ownership. */
extern uint32_t xbox_HeapLiveBytes(void);
extern uint32_t xbox_ContiguousLiveBytes(void);
static FighterNames s_names;
static FighterBindings s_bindings;
static FighterWindow s_window;
static uint8_t *s_window_bytes;
static uint8_t *s_bytes;
static uint8_t *s_binding_bytes;
static uint32_t s_validated_database;
static uint8_t s_bank_records[FIGHTER_WINDOW_BANKS][104];
static uint8_t *s_template_records;
static int s_immutable_reuse;
static RECOMP_TLS unsigned s_record_traces;
static uint32_t s_guest_text;
static uint32_t s_settings;
static volatile int s_lock;
static RECOMP_TLS unsigned s_trace_count;
static int s_trace;
static int s_probe, s_probed;
static char s_research_sod[2048];
static char s_research_screens[2048];
int defjam_fighter_research_active(void) { return s_probe && s_research_sod[0]; }
static char s_research_assets[3][2048];
static const char *s_asset_targets[3] = { "assets/v2ip.viv", "assets/entity.xml", "assets/nis.viv" };
static const char *s_asset_env[3] = { "RECOMP_FIGHTER_RESEARCH_MODELS", "RECOMP_FIGHTER_RESEARCH_ENTITIES", "RECOMP_FIGHTER_RESEARCH_CINEMATICS" };
/* Custom unlocks live in <state>/unlocks.ini, a sidecar the game writes itself
 * before each Options save. Saves stay in save/; the Options file there is
 * always a retail one. */
static char s_state_dir[2048];
static uint8_t s_live_settings[FIGHTER_SETTINGS_SIZE];
static int s_projecting_settings;
static uint32_t s_custom_count;
static int s_custom_dirty;
static int s_test_save_stop;
static uint8_t *s_identity_bytes;
static uint32_t s_identity_count;
static uint32_t s_identity_handles[FIGHTER_BINDINGS_MAX_COUNT];
static const char *s_identity_names[FIGHTER_BINDINGS_MAX_COUNT];
static char *s_unknown_lines;
static size_t s_unknown_size;
static uint32_t s_custom_keys[FIGHTER_BINDINGS_MAX_COUNT], s_custom_metadata[FIGHTER_BINDINGS_MAX_COUNT];
static uint32_t read_word(const uint8_t *p);
static int remember_custom(uint32_t mark);
#if defined(_WIN32)
typedef WCHAR fighter_host_char;
#else
typedef char fighter_host_char;
#endif
extern BOOL (*g_xbox_game_file_redirect)(const char *, fighter_host_char *, DWORD);
static BOOL (*s_previous_redirect)(const char *, fighter_host_char *, DWORD);

static FILE *open_utf8(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];
    return MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048) ? _wfopen(wide, L"rb") : NULL;
#else
    return fopen(path, "rb");
#endif
}

static void fighter_stop(const char *message) {
    /* A disposable harness run has no interactive approval/error dialog; the research
     * entry point turns the dialog off in defjam_fighter_runtime_start. */
    defjam_fighter_fatal(NULL, message);
}

static int file_name(const char *name, const char *expected) {
    for (; *name && *expected; ++name, ++expected) {
        unsigned c = (unsigned char)*name;
        if (c == '\\') c = '/';
        if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
        if (c != (unsigned char)*expected) return 0;
    }
    return !*name && !*expected;
}

static BOOL research_redirect(const char *relative, fighter_host_char *host_path, DWORD size) {
    const char *replacement = file_name(relative, "assets/djv2.sod") ? s_research_sod
        : file_name(relative, "screens/screens.viv") ? s_research_screens
        : file_name(relative, "motion/main_all.dat") ? defjam_fighter_motion_path()
        : file_name(relative, "audio/speech2.viv") ? defjam_fighter_voice_path()
        : file_name(relative, "assets/ai/ai.viv") ? defjam_fighter_ai_path()
        : file_name(relative, "assets/v2ta.viv") ? defjam_fighter_cinematic_path()
        : file_name(relative, "motion/blazin.viv") ? defjam_fighter_finishers_path()
        : file_name(relative, "audio/animtags.dat") ? defjam_fighter_events_tags_path()
        : file_name(relative, "motion/camera.xml") ? defjam_fighter_events_cameras_path()
        : file_name(relative, "motion/wres_all.viv") ? defjam_fighter_animation_path() : NULL;
    for (unsigned i = 0; i < 3; ++i)
        if (file_name(relative, s_asset_targets[i])) replacement = s_research_assets[i];
    if (replacement && *replacement) {
        /* Fail a shared-file conflict instead of depending on callback order. */
        if (s_previous_redirect && s_previous_redirect(relative, host_path, size)) {
            fighter_stop("Fighter research and another mod both replace the same game file.");
        }
#if defined(_WIN32)
        if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, replacement, -1, host_path, (int)size)) {
#else
        if (snprintf(host_path, size, "%s", replacement) >= (int)size) {
#endif
            fighter_stop("Fighter research cache path cannot be represented.");
        }
        fprintf(stderr, "[FIGHTERS] serving research file %s\n", relative);
        return TRUE;
    }
    return s_previous_redirect ? s_previous_redirect(relative, host_path, size) : FALSE;
}

#define FIGHTER_SIDECAR_MAX (1u << 20)

static uint8_t *read_small_file(const char *path, size_t limit, size_t *size) {
    FILE *file = open_utf8(path);
    uint8_t *bytes;
    if (!file) return NULL;
    bytes = (uint8_t *)malloc(limit + 1);
    if (!bytes) { fclose(file); return NULL; }
    *size = fread(bytes, 1, limit + 1, file);
    if (ferror(file) || *size > limit) { fclose(file); free(bytes); return NULL; }
    fclose(file);
    bytes[*size] = 0;
    return bytes;
}

/* A pack/fighter name from the binding ledger: printable, one slash, no '=' or spaces. */
static int sidecar_name(const char *name) {
    unsigned slashes = 0, length = 0;
    for (; name[length]; ++length) {
        unsigned char c = (unsigned char)name[length];
        if (c <= 32 || c > 126 || c == '=' || c == '[' || c == '#' || c == ';') return 0;
        slashes += c == '/';
    }
    return length && length <= 161 && slashes == 1;
}

/* RECOMP_FIGHTER_IDENTITIES: "HHHHHHHH pack/fighter" per custom ledger entry. */
static int load_identities(const char *path) {
    size_t size = 0;
    char *line, *next;
    s_identity_bytes = path && *path ? read_small_file(path, FIGHTER_SIDECAR_MAX, &size) : NULL;
    if (!s_identity_bytes) {
        fprintf(stderr, "[FIGHTERS] fighter identity names are missing; launch refused\n");
        return 0;
    }
    for (line = (char *)s_identity_bytes; line && *line; line = next) {
        char *end;
        unsigned long handle;
        FighterBinding binding;
        next = strchr(line, '\n');
        if (next) *next++ = 0;
        if (*line && line[strlen(line) - 1] == '\r') line[strlen(line) - 1] = 0;
        if (!*line || *line == '#') continue;
        handle = strtoul(line, &end, 16);
        if (end != line + 8 || *end != ' ' || !sidecar_name(end + 1) || s_identity_count >= FIGHTER_BINDINGS_MAX_COUNT
            || !fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, (uint32_t)handle, &binding) || !(binding.flags & 1)) {
            fprintf(stderr, "[FIGHTERS] fighter identity names do not match the bindings; launch refused\n");
            return 0;
        }
        s_identity_handles[s_identity_count] = (uint32_t)handle;
        s_identity_names[s_identity_count++] = end + 1;
    }
    for (uint32_t i = 0; i < s_bindings.count; ++i) {
        FighterBinding binding;
        int named = 0;
        fighter_bindings_at(&s_bindings, i, &binding);
        if (!(binding.flags & 1)) continue;
        for (uint32_t j = 0; j < s_identity_count && !named; ++j) named = s_identity_handles[j] == binding.stable_handle;
        if (!named) {
            fprintf(stderr, "[FIGHTERS] custom fighter %08X has no name in the identity file; launch refused\n", binding.stable_handle);
            return 0;
        }
    }
    return 1;
}

static const char *identity_name(uint32_t handle) {
    for (uint32_t i = 0; i < s_identity_count; ++i) if (s_identity_handles[i] == handle) return s_identity_names[i];
    return NULL;
}

static int identity_handle(const char *name, uint32_t *handle) {
    for (uint32_t i = 0; i < s_identity_count; ++i)
        if (!strcmp(s_identity_names[i], name)) { *handle = s_identity_handles[i]; return 1; }
    return 0;
}

static void sidecar_path(char *out, size_t size, const char *leaf) {
    snprintf(out, size, "%s/%s", s_state_dir, leaf);
}

static FILE *open_write_utf8(const char *path);
static int write_sidecar(void);

/* Keep a damaged unlock file beside the new one and tell the player once, through
 * the launcher's notice (src/hooks/pc_mods.cpp). The file is renamed, not copied,
 * so the next write starts a clean one and nothing is ever lost. */
static int set_aside(const char *path, unsigned skipped, int newer) {
    char aside[2200], notice[2112], when[32];
    time_t now = time(NULL);
    struct tm local;
    FILE *file;
    int moved;
#if defined(_WIN32)
    localtime_s(&local, &now);
#else
    localtime_r(&now, &local);
#endif
    strftime(when, sizeof when, "%Y%m%d-%H%M%S", &local);
    snprintf(aside, sizeof aside, "%s.bad-%s", path, when);
#if defined(_WIN32)
    {
        wchar_t from[2112], to[2200];
        moved = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, from, 2112)
            && MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, aside, -1, to, 2200)
            && MoveFileExW(from, to, MOVEFILE_WRITE_THROUGH);
    }
#else
    moved = !rename(path, aside);
#endif
    if (!moved) return 0;
    fprintf(stderr, "[FIGHTERS] custom unlock file kept as %s (%s)\n", aside,
            newer ? "written by a newer version" : "damaged lines skipped");
    sidecar_path(notice, sizeof notice, "notice.txt");
    file = open_write_utf8(notice);
    if (file) {
        if (newer)
            fprintf(file, "The custom fighter unlock file was written by a newer version of the game, so this version "
                          "starts with no custom unlocks. The file was kept as %s.\n", aside);
        else
            fprintf(file, "%u line(s) of the custom fighter unlock file could not be read and were left out. "
                          "The original file was kept as %s.\n", skipped, aside);
        fclose(file);
    }
    return 1;
}

/* Read <state>/unlocks.ini. A missing file means no custom unlock yet. Names
 * of packs that are not installed are kept, untouched, for the next write.
 * A damaged file never turns fighter packs off: its readable lines are used,
 * the rest are skipped, and the original is kept beside it (set_aside). */
static int load_sidecar(void) {
    char path[2112];
    size_t size = 0;
    uint8_t *bytes;
    char *line, *next;
    int section = 0, newer = 0;
    unsigned skipped = 0;
    sidecar_path(path, sizeof path, "unlocks.ini");
    {
        FILE *probe = open_utf8(path);
        if (!probe) { fprintf(stderr, "[FIGHTERS] no custom unlocks saved yet\n"); return 1; }
        fclose(probe);
    }
    bytes = read_small_file(path, FIGHTER_SIDECAR_MAX, &size);
    s_unknown_lines = (char *)malloc(FIGHTER_SIDECAR_MAX + 1);
    if (!s_unknown_lines) { free(bytes); return 0; }
    if (!bytes) {
        /* Unreadable or over 1 MiB. Without its contents a later write would replace
         * unlocks we never saw, so move it aside first, or else leave packs off. */
        if (!set_aside(path, 0, 0)) {
            fprintf(stderr, "[FIGHTERS] cannot read or move the custom unlock file %s; fighter packs left off, file kept\n", path);
            return 0;
        }
        return 1;
    }
    for (line = (char *)bytes; line && *line; line = next) {
        char *equals, *value;
        uint32_t handle;
        next = strchr(line, '\n');
        if (next) *next++ = 0;
        if (*line && line[strlen(line) - 1] == '\r') line[strlen(line) - 1] = 0;
        if (!*line || *line == '#' || *line == ';') continue;
        if (!strcmp(line, "[fighter-unlocks]")) { section = 1; continue; }
        equals = strchr(line, '=');
        if (!section || !equals) { ++skipped; continue; }
        *equals = 0; value = equals + 1;
        if (!strcmp(line, "schema")) { if (strcmp(value, "1")) { newer = 1; break; } continue; }
        if (!sidecar_name(line) || (strcmp(value, "0") && strcmp(value, "1"))) { ++skipped; continue; }
        if (identity_handle(line, &handle)) {
            remember_custom(handle | (*value == '1' ? FIGHTER_UNLOCK_METADATA : 0));
        } else {
            int written = snprintf(s_unknown_lines + s_unknown_size, FIGHTER_SIDECAR_MAX + 1 - s_unknown_size, "%s=%s\n", line, value);
            if (written < 0 || (size_t)written > FIGHTER_SIDECAR_MAX - s_unknown_size) { ++skipped; continue; }
            s_unknown_size += (size_t)written;
        }
    }
    free(bytes);
    if (newer) { s_custom_count = 0; s_unknown_size = 0; }
    if (newer || skipped) {
        if (!set_aside(path, skipped, newer)) {
            fprintf(stderr, "[FIGHTERS] custom unlock file %s is damaged and could not be moved aside; fighter packs left off, file kept\n", path);
            return 0;
        }
        /* Write the clean file now: the good lines must survive even if this
         * session ends before the game saves. A failure stays pending. */
        s_custom_dirty = 1;
        write_sidecar();
    } else {
        s_custom_dirty = 0;
    }
    fprintf(stderr, "[FIGHTERS] restored %u custom unlocks from %s (%zu bytes kept for packs not installed, %u lines skipped)\n",
            s_custom_count, path, s_unknown_size, skipped);
    return 1;
}

static FILE *open_write_utf8(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2112];
    return MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2112) ? _wfopen(wide, L"wb") : NULL;
#else
    return fopen(path, "wb");
#endif
}

static void make_state_dir(void) {
#if defined(_WIN32)
    wchar_t wide[2112];
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s_state_dir, -1, wide, 2112)) _wmkdir(wide);
#else
    mkdir(s_state_dir, 0777);
#endif
}

/* Temporary file, flush to disk, then a replacing rename: a crash leaves
 * either the previous sidecar or the new one, never a torn file. A failure is
 * logged and retried at the next save; it never stops the game. */
static int write_sidecar(void) {
    char path[2112], temporary[2112];
    size_t capacity = 256 + (size_t)s_custom_count * 176 + s_unknown_size, size = 0;
    char *text = (char *)malloc(capacity);
    FILE *file;
    int ok, unnamed = 0;
    if (!text) return 0;
    size += (size_t)snprintf(text, capacity, "%s",
        "# Custom fighter unlocks. Written by the game; keys are pack/fighter names.\n"
        "# 1 = the unlock carries the game's extra flag bit. Unknown names are kept.\n"
        "[fighter-unlocks]\nschema=1\n");
    for (uint32_t i = 0; i < s_custom_count; ++i) {
        const char *name = identity_name(s_custom_keys[i]);
        if (!name) {
            fprintf(stderr, "[FIGHTERS] custom unlock %08X has no name; kept for the next save\n", s_custom_keys[i]);
            unnamed = 1;
            continue;
        }
        size += (size_t)snprintf(text + size, capacity - size, "%s=%d\n", name, s_custom_metadata[i] ? 1 : 0);
    }
    if (s_unknown_size) { memcpy(text + size, s_unknown_lines, s_unknown_size); size += s_unknown_size; }
    make_state_dir();
    sidecar_path(path, sizeof path, "unlocks.ini");
    sidecar_path(temporary, sizeof temporary, "unlocks.ini.tmp");
    file = open_write_utf8(temporary);
    ok = file && fwrite(text, 1, size, file) == size && !fflush(file);
#if defined(_WIN32)
    ok = ok && !_commit(_fileno(file));
#else
    ok = ok && !fsync(fileno(file));
#endif
    if (file && fclose(file)) ok = 0;
    if (ok) {
#if defined(_WIN32)
        wchar_t from[2112], to[2112];
        ok = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, temporary, -1, from, 2112)
            && MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, to, 2112)
            && MoveFileExW(from, to, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH);
#else
        ok = !rename(temporary, path);
#endif
    }
    free(text);
    if (!ok) { fprintf(stderr, "[FIGHTERS] could not write custom unlocks to %s; will retry at the next save\n", path); return 0; }
    s_custom_dirty = unnamed; /* an unlock that could not be named stays pending, never dropped */
    fprintf(stderr, "[FIGHTERS] custom unlocks written: %u (%s)\n", s_custom_count, path);
    return 1;
}

static void test_save_stop(int point) {
    if (s_test_save_stop != point) return;
    fprintf(stderr, "[FIGHTERS-TEST] interrupted native save: point=%s exit=86\n", point == 1 ? "sidecar" : "options");
    fflush(stderr);
    _Exit(86); /* Test control only (RECOMP_FIGHTER_TEST_SAVE_STOP): bypass all cleanup, like a crash. */
}

static int research_start(void) {
    if (!defjam_fighter_caf_start()) return 0;
    const char *sod = defjam_fighter_env("RECOMP_FIGHTER_RESEARCH_SOD");
    const char *screens = defjam_fighter_env("RECOMP_FIGHTER_RESEARCH_SCREENS");
    const char *language_base = defjam_fighter_env("RECOMP_FIGHTER_RESEARCH_LANGUAGE_BASE");
    const char *screens_hash = defjam_fighter_env("RECOMP_FIGHTER_RESEARCH_SCREENS_SHA256");
    const char *bindings = defjam_fighter_env("RECOMP_FIGHTER_BINDINGS");
    const char *data = getenv("DEFJAM_DATA"), *settings = getenv("RECOMP_SETTINGS"), *leaf;
    const int managed = defjam_fighter_managed();
    unsigned assets = 0;
    for (unsigned i = 0; i < 3; ++i) {
        const char *path = defjam_fighter_env(s_asset_env[i]);
        char hash_env[96];
        const char *hash;
        snprintf(hash_env, sizeof hash_env, "%s_SHA256", s_asset_env[i]);
        hash = defjam_fighter_env(hash_env);
        if (path && *path) {
            if (!sod || !*sod || !defjam_fighter_file_matches(path, hash)) {
                fprintf(stderr, "[FIGHTERS] appearance cache failed its receipt; launch refused\n");
                return 0;
            }
            strcpy(s_research_assets[i], path);
            ++assets;
        } else if (hash && *hash) return 0;
    }
    if (assets && assets != 3) {
        fprintf(stderr, "[FIGHTERS] incomplete appearance cache; launch refused\n");
        return 0;
    }
    if (!sod || !*sod) return (!screens || !*screens) && (!language_base || !*language_base)
        && (!screens_hash || !*screens_hash) && defjam_fighter_motion_start()
        && defjam_fighter_voice_start() && defjam_fighter_animation_start() && defjam_fighter_ai_start()
        && defjam_fighter_cinematic_start() && defjam_fighter_events_start() && defjam_fighter_film_start() && defjam_fighter_finishers_start();
    /* Normal Play reads the launcher's manifest and saves into the player's own
     * save/. Without a manifest this is the research entry point, which still
     * needs the probe driver's disposable data root and no player settings. */
    leaf = data ? data + strlen(data) : NULL;
    while (leaf && leaf > data && leaf[-1] != '/' && leaf[-1] != '\\') --leaf;
    if ((!managed && (!leaf || strcmp(leaf, "fighter-runtime-probe") || !settings || strcmp(settings, "none")))
        || !s_names.bytes || strlen(sod) >= sizeof s_research_sod
        || (screens && strlen(screens) >= sizeof s_research_screens)) {
        fprintf(stderr, "[FIGHTERS] research roster requires the isolated probe driver; launch refused\n");
        return 0;
    }
    {
        FILE *file = bindings && *bindings ? open_utf8(bindings) : NULL;
        size_t count;
        if (!file) { fprintf(stderr, "[FIGHTERS] research roster requires identity bindings\n"); return 0; }
        s_binding_bytes = (uint8_t *)malloc(FIGHTER_BINDINGS_MAX_FILE + 1);
        if (!s_binding_bytes) { fclose(file); return 0; }
        count = fread(s_binding_bytes, 1, FIGHTER_BINDINGS_MAX_FILE + 1, file);
        if (ferror(file) || !fighter_bindings_decode(&s_bindings, s_binding_bytes, count)) {
            fclose(file); free(s_binding_bytes); s_binding_bytes = NULL;
            fprintf(stderr, "[FIGHTERS] invalid identity bindings; launch refused\n"); return 0;
        }
        fclose(file);
    }
    {
        const char *path = defjam_fighter_env("RECOMP_FIGHTER_WINDOW");
        if (path && *path) {
            FILE *file = open_utf8(path);
            size_t count;
            if (!file) return 0;
            s_window_bytes = (uint8_t *)malloc(FIGHTER_WINDOW_MAX_FILE + 1);
            if (!s_window_bytes) { fclose(file); return 0; }
            count = fread(s_window_bytes, 1, FIGHTER_WINDOW_MAX_FILE + 1, file);
            if (ferror(file) || !fighter_window_decode(&s_window, s_window_bytes, count)
                || s_window.table != s_bindings.table) {
                fclose(file); fprintf(stderr, "[FIGHTERS] invalid participant binding window\n"); return 0;
            }
            fclose(file);
            for (uint32_t i = 0; i < s_window.count; ++i) {
                FighterWindowRow row; FighterBinding binding;
                fighter_window_at(&s_window, i, &row);
                if (!fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, row.stable_handle, &binding)
                    || binding.flags != 1 || binding.selection_key != row.selection_key || binding.symbol_hash != row.symbol_hash)
                    return 0;
            }
            for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i) {
                FighterBinding binding;
                if (fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, s_window.banks[i].private_handle, &binding)
                    || fighter_bindings_find(&s_bindings, FIGHTER_BINDING_NATIVE, s_window.banks[i].native_handle, &binding)) return 0;
            }
            fprintf(stderr, "[FIGHTERS] participant window: %u logical fighters, %u native banks\n", s_window.count, FIGHTER_WINDOW_BANKS);
            path = defjam_fighter_env("RECOMP_FIGHTER_IMMUTABLE_REUSE");
            if (path && strcmp(path, "0") && strcmp(path, "1")) return 0;
            s_immutable_reuse = path && !strcmp(path, "1");
        }
        /* Custom unlocks outlive the active roster: a disabled pack's marks stay
         * in the sidecar under its name and come back when it is enabled again. */
        if (s_window.bytes) {
            path = defjam_fighter_env("RECOMP_FIGHTER_STATE");
            if (!path || !*path || strlen(path) >= sizeof s_state_dir - 64) {
                fprintf(stderr, "[FIGHTERS] no custom unlock folder; launch refused\n"); return 0;
            }
            strcpy(s_state_dir, path);
            path = defjam_fighter_env("RECOMP_FIGHTER_TEST_SAVE_STOP");
            if (path && *path) {
                if (!strcmp(path, "sidecar")) s_test_save_stop = 1;
                else if (!strcmp(path, "options")) s_test_save_stop = 2;
                else return 0;
            }
            if (!load_identities(defjam_fighter_env("RECOMP_FIGHTER_IDENTITIES")) || !load_sidecar()) return 0;
        }
    }
    strcpy(s_research_sod, sod);
    defjam_fighter_fatal_dialog(0);
    if (!defjam_fighter_motion_start() || !defjam_fighter_voice_start() || !defjam_fighter_animation_start() || !defjam_fighter_ai_start()
        || !defjam_fighter_cinematic_start() || !defjam_fighter_events_start() || !defjam_fighter_film_start() || !defjam_fighter_finishers_start()) {
        fprintf(stderr, "[FIGHTERS] invalid motion research receipt; launch refused\n");
        return 0;
    }
    if (screens) strcpy(s_research_screens, screens);
    if (language_base && *language_base) {
        if (!screens || !*screens || pc_language_adopt_composed_file("screens/screens.viv",
                language_base, screens, screens_hash) != 1) {
            fprintf(stderr, "[FIGHTERS] language screens composition did not verify; launch refused\n");
            return 0;
        }
        s_research_screens[0] = 0; /* The language redirect owns the single final composed file. */
        fprintf(stderr, "[FIGHTERS] verified language screens base and adopted fighter presentation\n");
    } else if (screens_hash && *screens_hash) {
        fprintf(stderr, "[FIGHTERS] incomplete language composition receipt; launch refused\n");
        return 0;
    }
    s_previous_redirect = g_xbox_game_file_redirect;
    g_xbox_game_file_redirect = research_redirect;
    fprintf(stderr, managed ? "[FIGHTERS] fighter packs enabled; saves stay in save/\n"
                            : "[FIGHTERS] research roster enabled in the disposable probe namespace\n");
    return 1;
}

int defjam_fighter_runtime_start(void) {
    const char *path = defjam_fighter_env("RECOMP_FIGHTER_NAMES");
    const char *trace = getenv("RECOMP_TRACE_FIGHTER_NAMES");
    const char *probe = defjam_fighter_env("RECOMP_FIGHTER_NAMES_PROBE");
    FILE *file = NULL;
    size_t count;
    s_trace = trace && *trace && strcmp(trace, "0");
    s_probe = probe && *probe && strcmp(probe, "0");
    if (!path || !*path) return research_start();
    file = open_utf8(path);
    if (!file) { fprintf(stderr, "[FIGHTERS] cannot open name bindings\n"); return 0; }
    s_bytes = (uint8_t *)malloc(FIGHTER_NAMES_MAX_FILE + 1);
    if (!s_bytes) { fclose(file); return 0; }
    count = fread(s_bytes, 1, FIGHTER_NAMES_MAX_FILE + 1, file);
    if (ferror(file) || !fighter_names_decode(&s_names, s_bytes, count)) {
        fclose(file); free(s_bytes); s_bytes = NULL;
        fprintf(stderr, "[FIGHTERS] invalid or oversized FML1 name bindings; launch refused\n"); return 0;
    }
    fclose(file);
    fprintf(stderr, "[FIGHTERS] registered %u local research names (%u UTF-16 bytes)\n", s_names.count, s_names.text_size);
    return research_start();
}

static void lock_names(void) {
#if defined(_WIN32)
    while (InterlockedCompareExchange((volatile LONG *)&s_lock, 1, 0)) Sleep(0);
#else
    while (__sync_lock_test_and_set(&s_lock, 1)) sched_yield();
#endif
}
static void unlock_names(void) {
#if defined(_WIN32)
    InterlockedExchange((volatile LONG *)&s_lock, 0);
#else
    __sync_lock_release(&s_lock);
#endif
}

uint32_t defjam_fighter_native_handle(uint32_t handle) {
    FighterBinding binding;
    uint32_t window_handle = fighter_window_native(&s_window, handle);
    if (window_handle != UINT32_MAX) return window_handle;
    if (!s_bindings.bytes || handle == UINT32_MAX || handle >> 24 != s_bindings.table) return handle;
    /* A dormant/unknown identity resolves to the native absent tuple. Never
     * reinterpret its stable rank as whichever current row occupies it. */
    return fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, handle, &binding)
        ? binding.native_handle : UINT32_MAX;
}

static void validate_database(uint32_t database) {
    GuestRegs saved;
    uint32_t base, table_header, output;
    if (s_validated_database == database) return;
    base = MEM32(database);
    if (MEM32(base) != 0x42444f53u) fighter_stop("Fighter bindings received a different database format.");
    table_header = MEM32(MEM32(database + 0x14) + MEM32(database + 8) * s_bindings.table * 4);
    if (MEM32(base + table_header) != 0x4ce5b1b2u || MEM32(base + table_header + 12)
        != s_bindings.active_count + (s_window.bytes ? FIGHTER_WINDOW_BANKS : 0))
        fighter_stop("Fighter binding roster count does not match the loaded database.");
    guest_regs_save(&saved);
    g_esp -= 16; output = g_esp;
    for (uint32_t i = 0; i < s_bindings.count; ++i) {
        FighterBinding binding;
        uint32_t row, sid, args[3];
        fighter_bindings_at(&s_bindings, i, &binding);
        if (!(binding.flags & 2)) continue;
        args[0] = output; args[1] = binding.native_handle; args[2] = 0;
        guest_call(sub_000BE760_gen, database, 3, args);
        row = MEM32(output); sid = row ? MEM32(row) : UINT32_MAX;
        if (!row || sid >= MEM32(database + 0x44)
            || MEM32(MEM32(database + 0x48) + sid * 8) != binding.symbol_hash
            || MEM32(row + 32) != binding.selection_key || MEM32(row + 40) != binding.core_id)
            fighter_stop("Fighter identity bindings do not match the loaded database rows.");
    }
    if (s_window.bytes) {
        for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i) {
            FighterWindowBank *bank = &s_window.banks[i];
            uint32_t args[3] = {output, bank->native_handle, 0};
            guest_call(sub_000BE760_gen, database, 3, args);
            if (MEM32(output) != base + bank->record_offset || MEM32(MEM32(database + 0x48) + MEM32(base + bank->record_offset) * 8) != bank->symbol_hash
                || MEM32(base + bank->record_offset + 32) != bank->selection_key || MEM32(base + bank->record_offset + 40) != bank->core_id)
                fighter_stop("Native participant bank does not match its generated binding.");
            memcpy(s_bank_records[i], (const void *)XBOX_PTR(base + bank->record_offset), 104);
        }
        s_template_records = (uint8_t *)malloc((size_t)s_window.count * 104);
        if (!s_template_records) fighter_stop("Could not retain immutable fighter validation records.");
        for (uint32_t i = 0; i < s_window.count; ++i) {
            FighterWindowRow row; uint32_t sid;
            fighter_window_at(&s_window, i, &row);
            sid = MEM32(base + row.record_offset);
            if (sid >= MEM32(database + 0x44) || MEM32(MEM32(database + 0x48) + sid * 8) != row.symbol_hash
                || MEM32(base + row.record_offset + 32) != row.selection_key || MEM32(base + row.record_offset + 40) != row.core_id)
                fighter_stop("Logical fighter template does not match its generated binding.");
            memcpy(s_template_records + (size_t)i * 104, (const void *)XBOX_PTR(base + row.record_offset), 104);
        }
    }
    guest_regs_restore(&saved);
    s_validated_database = database;
    fprintf(stderr, "[FIGHTERS] native identity bindings verified: %u active, %u dormant\n",
            s_bindings.active_count, s_bindings.count - s_bindings.active_count);
}

static void validate_immutable_banks(void) {
    uint32_t base;
    if (!s_window.bytes || !s_validated_database) fighter_stop("Immutable fighter records have no verified database.");
    base = MEM32(s_validated_database);
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i)
        if (memcmp(s_bank_records[i], (const void *)XBOX_PTR(base + s_window.banks[i].record_offset), 104))
            fighter_stop("An indexed fighter bank changed after immutable-record validation.");
    for (uint32_t i = 0; i < s_window.count; ++i) {
        FighterWindowRow row;
        fighter_window_at(&s_window, i, &row);
        if (!s_template_records || memcmp(s_template_records + (size_t)i * 104,
                                         (const void *)XBOX_PTR(base + row.record_offset), 104))
            fighter_stop("An immutable fighter template changed during its native lifetime.");
    }
}

static int installed_record(uint32_t stable, FighterWindowRow *row) {
    FighterBinding binding;
    if (!s_window.bytes || !fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, stable, &binding)
        || !(binding.flags & 1) || !fighter_window_find(&s_window, binding.selection_key, NULL, row)) return 0;
    if (row->stable_handle != stable) fighter_stop("Immutable fighter identity differs from its historical binding.");
    return 1;
}

int defjam_fighter_native_record(uint32_t database, uint32_t output, uint32_t stable) {
    FighterWindowRow row;
    uint32_t type;
    if (!installed_record(stable, &row)) return 0;
    if (database != s_validated_database) fighter_stop("Immutable fighter lookup received a different database owner.");
    type = MEM32(MEM32(database + 0x10) + s_window.table * 4);
    if (type != 0x4ce5b1b2u) fighter_stop("Immutable fighter record has an unreviewed native type.");
    /* Original BE760's typed result, with process-lifetime immutable storage.
     * A retained stable handle never resolves through a later participant slot. */
    MEM32(output) = MEM32(database) + row.record_offset;
    MEM32(output + 4) = database;
    MEM32(output + 8) = type;
    if (s_record_traces++ < 32)
        fprintf(stderr, "[FIGHTERS] immutable record stable=%08X logical=%u core=%u offset=%u caller=%08X\n",
                stable, row.selection_key, row.core_id, row.record_offset, MEM32(g_esp));
    return 1;
}

void defjam_fighter_match_setup(uint32_t self, uint32_t fighters) {
    defjam_fighter_caf_begin_match();
    defjam_fighter_caf_story(self,fighters);
    if (!s_window.bytes) return;
    validate_immutable_banks();
    fprintf(stderr, "[FIGHTERS] resource observation phase=match_setup heap=%u contiguous=%u\n",
            xbox_HeapLiveBytes(), xbox_ContiguousLiveBytes());
    for (uint32_t i = 0; i < FIGHTER_WINDOW_BANKS; ++i) {
        FighterWindowRow row;
        uint32_t stable = MEM32(fighters + i * 4);
        if (!installed_record(stable, &row)) continue;
        if (MEM32(self + 0x168 + i * 4) != row.core_id)
            fighter_stop("Native match setup did not materialize the immutable fighter core.");
        fprintf(stderr, "[FIGHTERS] materialized participant=%u stable=%08X logical=%u core=%u immutable=1\n",
                i, stable, row.selection_key, row.core_id);
        defjam_fighter_caf_participant(self,i,row.selection_key);
    }
}

static void finish_selection(const char *boundary) {
    if (!s_window.bytes || !s_window.frozen || !s_immutable_reuse) return;
    validate_immutable_banks();
    if (!fighter_window_finish(&s_window)) fighter_stop("Could not finish native fighter selection ownership.");
    fprintf(stderr, "[FIGHTERS] selection ownership finished after native %s; immutable records retained\n", boundary);
    fprintf(stderr, "[FIGHTERS] resource observation phase=match_finished heap=%u contiguous=%u\n",
            xbox_HeapLiveBytes(), xbox_ContiguousLiveBytes());
}

void defjam_fighter_match_finished(void) {
    defjam_fighter_caf_clear(); finish_selection("Game.Quit"); }
void defjam_fighter_match_unloaded(void) { defjam_fighter_caf_clear(); finish_selection("match teardown"); }

void defjam_fighter_handle_produced(uint32_t database, uint32_t table, uint32_t output) {
    FighterBinding binding;
    uint32_t handle;
    if (!s_bindings.bytes || table != 0x4ce5b1b2u) return;
    handle = MEM32(output);
    if (handle == UINT32_MAX) return;
    lock_names();
    validate_database(database);
    unlock_names();
    {
        uint32_t stable = fighter_window_stable(&s_window, handle);
        if (stable != UINT32_MAX) { MEM32(output) = stable; return; }
    }
    if (!fighter_bindings_find(&s_bindings, FIGHTER_BINDING_NATIVE, handle, &binding))
        fighter_stop("Native fighter handle has no stable identity binding.");
    MEM32(output) = binding.stable_handle;
}

void defjam_fighter_settings_bound(uint32_t self) {
    if (!s_bindings.bytes) return;
    if (MEM32(self + 0x1C) != FIGHTER_UNLOCK_CAPACITY || MEM32(self + 0x24) != self + 0x1264
        || MEM32(self + 0x28) != self + 0x12E0)
        fighter_stop("Native Character unlock container has a different layout.");
    s_settings = self;
    fprintf(stderr, "[FIGHTERS] native Options container bound: capacity=%u\n", FIGHTER_UNLOCK_CAPACITY);
}

void defjam_fighter_settings_validate(uint32_t self, uint32_t payload) {
    uint32_t count;
    FighterBinding binding;
    const uint8_t *bytes;
    if (!s_bindings.bytes) return;
    if (!s_settings || self != s_settings) fighter_stop("Unregistered native fighter settings owner.");
    bytes = (const uint8_t *)XBOX_PTR(payload);
    if (!fighter_unlocks_decode(bytes, FIGHTER_SETTINGS_SIZE, &count))
        fighter_stop("Native fighter unlock settings are malformed or exceed their fixed capacity.");
    for (uint32_t i = 0; i < count; ++i)
        if (!fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE,
                fighter_unlocks_at(bytes, i) & ~FIGHTER_UNLOCK_METADATA, &binding)
            && fighter_window_native(&s_window, fighter_unlocks_at(bytes, i) & ~FIGHTER_UNLOCK_METADATA) == UINT32_MAX)
            fighter_stop("Saved fighter unlock has no historical identity binding.");
    fprintf(stderr, "[FIGHTERS] native Options unlock payload verified: %u marks\n", count);
}

static int remember_custom(uint32_t mark) {
    FighterBinding binding;
    uint32_t identity = mark & ~FIGHTER_UNLOCK_METADATA;
    if (!fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, identity, &binding) || !(binding.flags & 1)) return 0;
    for (uint32_t i = 0; i < s_custom_count; ++i) if (s_custom_keys[i] == identity) {
        uint32_t metadata = mark & FIGHTER_UNLOCK_METADATA;
        int changed = s_custom_metadata[i] != metadata;
        s_custom_metadata[i] = metadata; if (changed) s_custom_dirty = 1; return changed;
    }
    if (s_custom_count >= FIGHTER_BINDINGS_MAX_COUNT) fighter_stop("Historical custom unlock journal is full.");
    s_custom_keys[s_custom_count] = identity; s_custom_metadata[s_custom_count++] = mark & FIGHTER_UNLOCK_METADATA;
    s_custom_dirty = 1;
    return 1;
}

static void custom_progress_changed(void) {
    uint32_t owner = MEM32(0x002FB148u + 0x18u * 4u), changed = 1;
    if (!owner || MEM32(owner + 4) + 4 != s_settings)
        fighter_stop("Custom progress has no verified native Options owner.");
    /* The native purchase path calls this same dirty setter after insertion.
     * Merely editing live Options would be lost when SaveGame skips D2300.
     * Restoring historical FUM1 state deliberately does not call this. */
    guest_call(sub_0001E310, owner, 1, &changed);
    fprintf(stderr, "[FIGHTERS] custom progress changed; native Options save requested\n");
}

void defjam_fighter_settings_saving(void) {
    if (!s_bindings.bytes) return;
    if (!s_settings || MEM32(s_settings + 0x20) != MEM32(s_settings + 0x1264))
        fighter_stop("Native fighter unlock counts disagree before save staging.");
    defjam_fighter_settings_validate(s_settings, s_settings + 0x4C);
    if (s_state_dir[0]) {
        uint32_t count = MEM32(s_settings + 0x20), kept = 0;
        if (s_projecting_settings) fighter_stop("Reentrant native Options projection.");
        memcpy(s_live_settings, (const void *)XBOX_PTR(s_settings + 0x4C), FIGHTER_SETTINGS_SIZE);
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t mark = MEM32(s_settings + 0x12E0 + i * 4);
            FighterBinding binding;
            remember_custom(mark);
            if (fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, mark & ~FIGHTER_UNLOCK_METADATA, &binding) && !(binding.flags & 1))
                MEM32(s_settings + 0x12E0 + kept++ * 4) = mark;
        }
        /* The Options file the game is about to write holds retail marks only,
         * so any build (or v1.1.1) reads it. Custom marks go to the sidecar
         * first: a crash between the two writes keeps an unlock rather than
         * losing one. */
        MEM32(s_settings + 0x1264) = kept;
        for (uint32_t i = kept; i < FIGHTER_UNLOCK_CAPACITY; ++i) MEM32(s_settings + 0x12E0 + i * 4) = UINT32_MAX;
        if (s_custom_dirty) write_sidecar();
        test_save_stop(1);
        s_projecting_settings = 1;
        fprintf(stderr, "[FIGHTERS] saving retail-only Options: %u marks, %u custom unlocks in the sidecar\n", kept, s_custom_count);
    }
}

void defjam_fighter_settings_saved(void) {
    if (!s_projecting_settings) return;
    memcpy((void *)XBOX_PTR(s_settings + 0x4C), s_live_settings, FIGHTER_SETTINGS_SIZE);
    s_projecting_settings = 0;
    test_save_stop(2);
}

static uint32_t outfit_progress_handle(uint32_t handle) {
    for(uint32_t i=0;i<s_window.count;++i) {
        FighterWindowRow row;FighterBinding parent;
        if(!fighter_window_at(&s_window,i,&row))break;
        if(row.stable_handle==handle && row.retail_selection_plus_one) {
            if(!fighter_bindings_find(&s_bindings,FIGHTER_BINDING_SELECTION,row.retail_selection_plus_one-1,&parent) || (parent.flags&1u))
                fighter_stop("Retail outfit has no canonical progress owner.");
            return parent.stable_handle;
        }
    }
    return handle;
}
void defjam_fighter_unlock_inserting(uint32_t self) {
    if (!s_bindings.bytes || !s_settings || self != s_settings + 0x1C) return;
    /* A larger live array also requires the save extension. Until it is wired,
     * reject the next insertion before the original unchecked write occurs. */
    if (MEM32(self + 4) >= MEM32(self) || MEM32(self) != FIGHTER_UNLOCK_CAPACITY)
        fighter_stop("Native Character unlock storage is full; expanded persistence is required.");
    uint32_t argument=MEM32(g_esp+4),mark=MEM32(argument);
    MEM32(argument)=outfit_progress_handle(mark&~FIGHTER_UNLOCK_METADATA)|(mark&FIGHTER_UNLOCK_METADATA);
    if (s_state_dir[0]) remember_custom(MEM32(argument));
}

void defjam_fighter_selection_gate(uint32_t selection) {
    FighterBinding binding;
    if (!s_bindings.bytes || selection < 100 || selection > 0x7fffffffu) return;
    if (selection >= 128 || !fighter_bindings_find(&s_bindings, FIGHTER_BINDING_SELECTION, selection, &binding)
        || !(binding.flags & 2))
        fighter_stop("Logical fighter selection has no safe native binding; confirmation is blocked.");
}

static void prune_participant_unlocks(void) {
    uint32_t count, kept = 0;
    if (!s_window.bytes || !s_settings) return;
    count = MEM32(s_settings + 0x20);
    if (count > FIGHTER_UNLOCK_CAPACITY)
        fighter_stop("Native unlock storage is malformed before selection cleanup.");
    /* Selection clearing must retire its live unlock projection too. Otherwise
     * unlock-all can insert the four bank placeholders beside stale custom
     * marks and overflow the native 80-entry set on a later retail selection.
     * Historical custom marks/metadata remain in the managed extension. */
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t mark = MEM32(s_settings + 0x12E0 + i * 4), identity = mark & ~FIGHTER_UNLOCK_METADATA;
        FighterBinding binding;
        int retain = fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, identity, &binding) && !(binding.flags & 1);
        for (uint32_t slot = 0; slot < FIGHTER_WINDOW_BANKS; ++slot) {
            FighterWindowRow selected;
            if (s_window.selected[slot] && fighter_window_at(&s_window, s_window.selected[slot] - 1, &selected)
                && selected.stable_handle == identity) retain = 1;
        }
        if (retain) MEM32(s_settings + 0x12E0 + kept++ * 4) = mark;
    }
    for (uint32_t i = kept; i < FIGHTER_UNLOCK_CAPACITY; ++i) MEM32(s_settings + 0x12E0 + i * 4) = 0;
    MEM32(s_settings + 0x20) = MEM32(s_settings + 0x1264) = kept;
}

static int submission_integer(uint32_t pointer, int32_t *value) {
    char text[40]; uint32_t i;
    if (!pointer) return 0;
    for (i = 0; i < sizeof text; ++i) {
        text[i] = (char)MEM8(pointer + i);
        if (!text[i]) return fighter_window_integer(text, value);
    }
    return 0;
}

uint32_t defjam_fighter_controller_submission(uint32_t arguments) {
    int32_t values[4];
    FighterWindowRow row;
    if (!s_bindings.bytes) return UINT32_MAX;
    for (uint32_t i = 0; i < 4; ++i)
        if (!submission_integer(MEM32(arguments + i * 4), &values[i]))
            fighter_stop("Invalid native controller setup arguments.");
    if (s_window.bytes && (values[0] < 0 || values[2] < 100)) {
        uint32_t participant = values[0] < 0 ? UINT32_MAX : (uint32_t)values[0];
        if (!fighter_window_clear(&s_window, participant))
            fighter_stop("Cannot clear participant ownership before verified match teardown.");
        defjam_fighter_caf_menu_clear(participant);
        prune_participant_unlocks();
        fprintf(stderr, "[FIGHTERS] cleared pre-match participant ownership: %d\n", values[0]);
    }
    if (values[0] < 0 || values[2] < 100) return UINT32_MAX;
    if (!s_window.bytes) { defjam_fighter_selection_gate((uint32_t)values[2]); return UINT32_MAX; }
    /* The original selector passes nConID as its fourth argument (0..3),
     * independently of clothing. Keep this native controller/color routing. */
    if (values[0] > 3 || !s_validated_database || values[3] < 0 || values[3] > 3
        || !fighter_window_bind(&s_window, (uint32_t)values[0], (uint32_t)values[2], &row))
        fighter_stop("Logical fighter cannot bind to this participant or the match is still active.");
    if (s_window.frozen) return s_window.banks[values[0]].selection_key;
    defjam_fighter_caf_menu_clear((uint32_t)values[0]);
    {
        FighterWindowBank *bank = &s_window.banks[values[0]];
        uint32_t count, kept = 0, keys[FIGHTER_UNLOCK_CAPACITY];
        validate_immutable_banks();
        if (!s_settings) fighter_stop("Participant binding has no native Options owner.");
        count = MEM32(s_settings + 0x20);
        if (count > FIGHTER_UNLOCK_CAPACITY) fighter_stop("Native unlock storage is malformed before participant binding.");
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t mark = MEM32(s_settings + 0x12E0 + i * 4), identity = mark & ~FIGHTER_UNLOCK_METADATA;
            FighterBinding binding;
            /* Retain retail marks and the other currently bound custom keys.
             * Private bank placeholders and old custom bindings never escape
             * this live set. Historical custom progress belongs to extension. */
            int retain = fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, identity, &binding) && !(binding.flags & 1);
            for (uint32_t j = 0; j < FIGHTER_WINDOW_BANKS; ++j) {
                FighterWindowRow selected;
                if (j != (uint32_t)values[0] && s_window.selected[j]
                    && fighter_window_at(&s_window, s_window.selected[j] - 1, &selected) && selected.stable_handle == identity) retain = 1;
            }
            if (retain) keys[kept++] = mark;
        }
        if (kept >= FIGHTER_UNLOCK_CAPACITY) fighter_stop("Participant unlock projection exceeds native capacity.");
        {
            uint32_t mark = outfit_progress_handle(row.stable_handle);
            /* A costume shares the retail parent's progress. Historical
             * standalone marks for its logical key stay in the extension,
             * never become a duplicate or change the parent on selection. */
            if (!row.retail_selection_plus_one)
                for (uint32_t i = 0; i < s_custom_count; ++i)
                    if (s_custom_keys[i] == row.stable_handle) mark |= s_custom_metadata[i];
            int present=0;
            if(row.retail_selection_plus_one)for(uint32_t i=0;i<kept;++i)if((keys[i]&~FIGHTER_UNLOCK_METADATA)==mark)present=1;
            if(!present)keys[kept++] = mark;
            if (remember_custom(mark)) custom_progress_changed();
        }
        for (uint32_t i = 1; i < kept; ++i) {
            uint32_t mark = keys[i], j = i;
            while (j && (keys[j - 1] & ~FIGHTER_UNLOCK_METADATA) > (mark & ~FIGHTER_UNLOCK_METADATA)) { keys[j] = keys[j - 1]; --j; }
            keys[j] = mark;
        }
        for (uint32_t i = 0; i < FIGHTER_UNLOCK_CAPACITY; ++i) MEM32(s_settings + 0x12E0 + i * 4) = i < kept ? keys[i] : 0;
        MEM32(s_settings + 0x20) = MEM32(s_settings + 0x1264) = kept;
        fprintf(stderr, "[FIGHTERS] participant=%d logical=%d stable=%08X native=%u core=%u unlocks=%u\n",
                values[0], values[2], row.stable_handle, bank->selection_key, row.core_id, kept);
        return bank->selection_key;
    }
}

/* The prefix length is the literal's own, so it can never drift from its text. */
#define STARTS_WITH(text, literal) (!strncmp((text), (literal), sizeof(literal) - 1))

int defjam_fighter_ui_command(uint32_t command) {
    static const char prefix[] = "Fighters.";
    char text[64]; uint32_t i;
    if (!s_window.bytes || !command) return 0;
    for (i = 0; i < sizeof prefix - 1; ++i)
        if (MEM8(command + i) != (uint8_t)prefix[i]) return 0;
    for (i = 0; i < sizeof text; ++i) {
        text[i] = (char)MEM8(command + i);
        if (!text[i]) break;
    }
    /* Unknown commands in this namespace keep passing through to the game, however long they are.
     * Only the two commands owned here may exceed the budget fatally. */
    if (i == sizeof text) {
        if (STARTS_WITH(text, "Fighters.Outfit") || STARTS_WITH(text, "Fighters.KeepReady"))
            fighter_stop("Native fighter UI command exceeds its budget.");
        return 0;
    }
    if (STARTS_WITH(text, "Fighters.Outfit")) {
        unsigned participant,selection,outfit;int end=0;char canonical[64];FighterWindowRow row;
        if(sscanf(text,"Fighters.Outfit(%u,%u,%u)%n",&participant,&selection,&outfit,&end)!=3 || !end || text[end]
            || participant>=4 || selection<100 || selection>0x7FFFFFFEu || outfit>2 || s_window.frozen)
            fighter_stop("Invalid native outfit confirmation.");
        snprintf(canonical,sizeof canonical,"Fighters.Outfit(%u,%u,%u)",participant,selection,outfit);
        if(strcmp(canonical,text)) fighter_stop("Noncanonical native outfit confirmation.");
        /* Browsing grids may also be snapshotted by the owned movie. Only a
         * confirmed, matching participant can change its appearance state. */
        if(!s_window.selected[participant] || !fighter_window_at(&s_window,s_window.selected[participant]-1,&row)
            || row.selection_key!=selection) return 1;
        if(!defjam_fighter_caf_outfit(participant,selection,outfit)) fighter_stop("Undeclared CAF outfit confirmation.");
        return 1;
    }
    if (!STARTS_WITH(text, "Fighters.KeepReady")) return 0;
    if (fighter_window_command(&s_window, text) != 1)
        fighter_stop("Native ready ownership differs from the participant bindings, or the match is still active.");
    for(i=0;i<4;++i) if(!s_window.selected[i]) defjam_fighter_caf_menu_clear(i);
    prune_participant_unlocks();
    fprintf(stderr, "[FIGHTERS] synchronized pre-match ready ownership: %s\n", text);
    return 1;
}

void defjam_fighter_menu_event(const char *text) {
    if (s_window.bytes && !strncmp(text, "Game.StartGame(", 15)) {
        validate_immutable_banks();
        s_window.frozen = 1;
        fprintf(stderr, "[FIGHTERS] participant window frozen for active match\n");
    }
}

uint32_t defjam_fighter_result_identity(uint32_t participant, uint32_t native) {
    FighterWindowRow row;
    if (!s_window.bytes || participant >= FIGHTER_WINDOW_BANKS || !s_window.selected[participant]) return native;
    if (!s_window.frozen || native != s_window.banks[participant].selection_key
        || !fighter_window_at(&s_window, s_window.selected[participant] - 1, &row))
        fighter_stop("Result identity does not match its frozen participant binding.");
    fprintf(stderr, "[FIGHTERS] result participant=%u native=%u logical=%u stable=%08X\n",
            participant, native, row.selection_key, row.stable_handle);
    return row.retail_selection_plus_one?row.retail_selection_plus_one-1:defjam_fighter_caf_presentation(participant,row.selection_key);
}

uint32_t defjam_fighter_loading_identity(uint32_t native) {
    FighterWindowRow row;
    /* FWR1 reserves100..103 for participant0..3. Derive ownership from that
     * verified bank domain, not a caller's locally lifted EBP loop counter. */
    uint32_t participant = native - 100u;
    if (!s_window.bytes || participant >= FIGHTER_WINDOW_BANKS || !s_window.selected[participant]) return native;
    /* GetMatchInfo is also queried before StartGame freezes the selection.
     * Only its presentation response changes; native participants keep banks. */
    if (native != s_window.banks[participant].selection_key
        || !fighter_window_at(&s_window, s_window.selected[participant] - 1, &row))
        fighter_stop("Loading identity does not match its participant binding.");
    fprintf(stderr, "[FIGHTERS] loading participant=%u native=%u logical=%u stable=%08X\n",
            participant, native, row.selection_key, row.stable_handle);
    return row.retail_selection_plus_one?row.retail_selection_plus_one-1:defjam_fighter_caf_presentation(participant,row.selection_key);
}

static uint32_t read_word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

uint32_t defjam_fighter_filter_banks(uint32_t entries, uint32_t count) {
    uint32_t kept = 0;
    if (!s_window.bytes) return count;
    if (count > 128) fighter_stop("Native bank roster exceeds the audited fixed-list boundary.");
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t handle = MEM32(entries + i * 4);
        FighterBinding binding;
        if (!fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, handle, &binding) || (binding.flags & 1)) continue;
        MEM32(entries + kept++ * 4) = handle;
    }
    for (uint32_t i = kept; i < count; ++i) MEM32(entries + i * 4) = UINT32_MAX;
    fprintf(stderr, "[FIGHTERS] private bank roster filtered: %u -> %u\n", count, kept);
    return kept;
}

void defjam_fighter_order(uint32_t database, uint32_t entries, uint32_t count, const char *source) {
    uint32_t *scratch, *keys, custom, descriptor;
    GuestRegs saved;
    if (!s_research_sod[0]) return;
    if (count > FIGHTER_NAMES_MAX_COUNT + 256 || !entries || entries > UINT32_MAX - count * 4) {
        fighter_stop("Fighter roster exceeds the audited research list budget.");
    }
    scratch = (uint32_t *)malloc((count ? count : 1) * sizeof *scratch * 2);
    if (!scratch) fighter_stop("Fighter roster ordering allocation failed.");
    keys = scratch + count;
    guest_regs_save(&saved);
    g_esp -= 16; descriptor = g_esp;
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t args[3] = {descriptor, MEM32(entries + i * 4), 0};
        uint32_t row, sid = UINT32_MAX;
        guest_call(sub_000BE760, database, 3, args);
        row = MEM32(descriptor);
        if (!row || (sid = MEM32(row)) >= MEM32(database + 0x44)) {
            fprintf(stderr, "[FIGHTERS] list=%s i=%u token=%08X db=%08X row=%08X sid=%u strings=%u\n",
                    source, i, args[1], database, row, sid, MEM32(database + 0x44));
            fighter_stop("Fighter roster contains an unresolved native handle.");
        }
        keys[i] = MEM32(MEM32(database + 0x48) + sid * 8);
    }
    guest_regs_restore(&saved);
    custom = fighter_roster_partition((uint32_t *)XBOX_PTR(entries), keys, count, scratch, &s_names);
    free(scratch);
    fprintf(stderr, "[FIGHTERS] native list %s: %u entries, %u custom appended\n", source, count, custom);
}

void defjam_fighter_materialized(uint32_t self, uint32_t handle) {
    char model[97];
    uint32_t pointer;
    if (!s_research_sod[0]) return;
    pointer = MEM32(self + 0x164);
    model[0] = 0;
    if ((pointer >= 0x10000 && pointer < 0x04000000) || (pointer >= 0x80000000 && pointer < 0x84000000)) {
        unsigned i;
        for (i = 0; i < sizeof model - 1; ++i) {
            unsigned c = MEM8(pointer + i);
            if (!c || c < 32 || c > 126) break;
            model[i] = (char)c;
        }
        model[i] = 0;
    }
    fprintf(stderr, "[FIGHTERS] materialized handle=%08X selection=%u model=%08X:%s speech=%u\n",
            handle, MEM32(self + 0x3B4), pointer, model, MEM32(self + 0x1EC));
}

void defjam_fighter_model_input(uint32_t object) {
    static unsigned traced;
    uint32_t bytes;
    if (!s_research_sod[0] || traced++ >= 512) return;
    bytes = MEM32(object + 0x10);
    fprintf(stderr, "[FIGHTERS] model input=%08X header=%08X/%08X sections=%08X/%u\n",
            bytes, MEM32(bytes), MEM32(bytes + 4), MEM32(bytes + 32), (unsigned)MEM16(bytes + 48));
}

uint32_t defjam_fighter_localized(uint32_t key, uint32_t native_value, uint32_t localizer) {
    uint32_t offset, length, result;
    if (s_trace && s_trace_count++ < 256)
        fprintf(stderr, "[FIGHTER-NAME] key=%08X native=%08X\n", key, native_value);
    if (s_probe && native_value && s_names.count) {
        int probe_now;
        lock_names(); probe_now = !s_probed; s_probed = 1; unlock_names();
        if (probe_now) {
            for (uint32_t i = 0; i < s_names.count; ++i) {
                const uint8_t *row = s_names.bytes + 16 + i * 12;
                uint32_t asked = read_word(row), args[1] = {asked};
                uint32_t pointer = guest_call(sub_00045180, localizer, 1, args);
                offset = read_word(row + 4); length = read_word(row + 8);
                int equal = pointer != 0;
                for (uint32_t at = 0; equal && at < length; at += 2) {
                    const uint8_t *expected = s_names.bytes + s_names.text_offset + offset + at;
                    uint16_t unit = MEM16(pointer + at);
                    equal = unit == ((uint16_t)expected[0] | (uint16_t)expected[1] << 8);
                    if (!unit) { equal = equal && at + 2 == length; break; }
                }
                if (!equal) {
                    fighter_stop("Fighter name lookup probe failed or conflicts with native localization.");
                }
            }
            fprintf(stderr, "[FIGHTERS] native localization probe accepted all %u names, exact UTF-16 match\n", s_names.count);
        }
    }
    /* Native translations always retain priority; helper-side composition
     * must reject conflicts before custom roster activation. */
    if (native_value || !fighter_names_find(&s_names, key, &offset, &length)) return native_value;
    lock_names();
    if (!s_guest_text) {
        uint32_t args[3] = {s_names.text_size, 0x0029D4B4u, 0};
        s_guest_text = guest_call(sub_00029680, 0, 3, args);
        if (!s_guest_text || s_guest_text > UINT32_MAX - s_names.text_size) {
            unlock_names(); fighter_stop("Fighter name allocation failed; launch stopped.");
        }
        memcpy((void *)XBOX_PTR(s_guest_text), s_names.bytes + s_names.text_offset, s_names.text_size);
        fprintf(stderr, "[FIGHTERS] name pool allocated at %08X (%u bytes)\n", s_guest_text, s_names.text_size);
    }
    result = s_guest_text + offset;
    unlock_names();
    return result;
}
