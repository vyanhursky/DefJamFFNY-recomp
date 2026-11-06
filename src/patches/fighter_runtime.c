#define _CRT_SECURE_NO_WARNINGS
#include "fighter_runtime.h"
#include "fighter_motion.h"
#include "fighter_voice.h"
#include "fighter_animation.h"
#include "fighter_ai.h"
#include "fighter_cinematic.h"
#include "fighter_finishers.h"
#include "hooks/fighter_names.h"
#include "hooks/fighter_roster.h"
#include "hooks/fighter_bindings.h"
#include "hooks/fighter_unlocks.h"
#include "hooks/fighter_window.h"
#include "hooks/fighter_save_io.h"
#include "hooks/guest_call.h"
#include "hooks/pc_language.h"
#include "host.h"
#include "hooks/mod_sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(_WIN32)
#include <io.h>
#else
#include <unistd.h>
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
static char s_journal[2048];
static uint8_t s_live_settings[FIGHTER_SETTINGS_SIZE];
static int s_projecting_settings;
typedef struct FighterPendingSave { char name[32]; uint32_t name_size, size; uint8_t identity[64], payload[0x5904]; } FighterPendingSave;
static FighterPendingSave s_pending[16];
typedef struct FighterExpectedSave { FighterPendingSave save; uint32_t batch, index; int active; } FighterExpectedSave;
static FighterExpectedSave s_expected[16];
static FighterSaveIO s_save_io;
static uint32_t s_pending_count, s_batch_number, s_custom_count;
static int s_test_save_stop;
static void await_save_commit(void);
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
    fprintf(stderr, "[FIGHTERS] stopped: %s\n", message);
    fflush(stderr);
    /* A disposable harness run has no interactive approval/error dialog. */
    if (!s_research_sod[0]) host_fatal(message);
    exit(1);
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

static int research_start(void) {
    const char *sod = getenv("RECOMP_FIGHTER_RESEARCH_SOD");
    const char *screens = getenv("RECOMP_FIGHTER_RESEARCH_SCREENS");
    const char *language_base = getenv("RECOMP_FIGHTER_RESEARCH_LANGUAGE_BASE");
    const char *screens_hash = getenv("RECOMP_FIGHTER_RESEARCH_SCREENS_SHA256");
    const char *bindings = getenv("RECOMP_FIGHTER_BINDINGS");
    const char *data = getenv("DEFJAM_DATA"), *settings = getenv("RECOMP_SETTINGS"), *leaf;
    unsigned assets = 0;
    for (unsigned i = 0; i < 3; ++i) {
        const char *path = getenv(s_asset_env[i]);
        char hash_env[96];
        const char *hash;
        snprintf(hash_env, sizeof hash_env, "%s_SHA256", s_asset_env[i]);
        hash = getenv(hash_env);
        if (path && *path) {
            if (!sod || !*sod || !mod_file_matches(path, hash)) {
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
        && defjam_fighter_cinematic_start() && defjam_fighter_finishers_start();
    /* This development entry point cannot use the normal profile namespace or
     * player settings. The probe driver owns this disposable data root and the
     * harness guards its complete save directory. No runtime capability is
     * advertised until persistence, menus and authored assets are accepted. */
    leaf = data ? data + strlen(data) : NULL;
    while (leaf && leaf > data && leaf[-1] != '/' && leaf[-1] != '\\') --leaf;
    if (!leaf || strcmp(leaf, "fighter-runtime-probe") || !settings || strcmp(settings, "none")
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
        const char *path = getenv("RECOMP_FIGHTER_WINDOW");
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
            path = getenv("RECOMP_FIGHTER_IMMUTABLE_REUSE");
            if (path && strcmp(path, "0") && strcmp(path, "1")) return 0;
            s_immutable_reuse = path && !strcmp(path, "1");
        }
        /* Profile transactions outlive the active roster. Removing the final
         * pack must still save retail progress and retain dormant identities. */
        path = getenv("RECOMP_FIGHTER_SAVE_JOURNAL");
        if (s_window.bytes || (path && *path)) {
            if (!path || !*path || strlen(path) >= sizeof s_journal - 64) return 0;
            strcpy(s_journal, path);
            path = getenv("RECOMP_FIGHTER_TEST_SAVE_STOP");
            if (path && *path) {
                if (!strcmp(path, "intent")) s_test_save_stop = 1;
                else if (!strcmp(path, "options-header")) s_test_save_stop = 2;
                else if (!strcmp(path, "profile-header")) s_test_save_stop = 3;
                else return 0;
            }
            path = getenv("RECOMP_FIGHTER_UNLOCKS");
            if (!path || !*path) return 0;
            {
                uint8_t *bytes = (uint8_t *)malloc(17 + FIGHTER_BINDINGS_MAX_COUNT * 8);
                FILE *file = open_utf8(path);
                size_t size;
                uint32_t total, previous = 0;
                if (!bytes || !file) { free(bytes); if (file) fclose(file); return 0; }
                size = fread(bytes, 1, 17 + FIGHTER_BINDINGS_MAX_COUNT * 8, file);
                if (ferror(file) || size < 16 || memcmp(bytes, "FUM1", 4) || read_word(bytes + 4) != 1 || read_word(bytes + 12)) {
                    fclose(file); free(bytes); return 0;
                }
                fclose(file); total = read_word(bytes + 8);
                if (total > FIGHTER_BINDINGS_MAX_COUNT || size != 16u + total * 8u) { free(bytes); return 0; }
                for (uint32_t i = 0; i < total; ++i) {
                    uint32_t handle = read_word(bytes + 16 + i * 8), metadata = read_word(bytes + 20 + i * 8);
                    FighterBinding binding;
                    if ((i && handle <= previous) || (metadata != 0 && metadata != FIGHTER_UNLOCK_METADATA)
                        || !fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, handle, &binding) || !(binding.flags & 1)) {
                        free(bytes); return 0;
                    }
                    remember_custom(handle | metadata); previous = handle;
                }
                free(bytes);
                fprintf(stderr, "[FIGHTERS] restored %u historical custom unlock marks\n", s_custom_count);
            }
        }
    }
    strcpy(s_research_sod, sod);
    if (!defjam_fighter_motion_start() || !defjam_fighter_voice_start() || !defjam_fighter_animation_start() || !defjam_fighter_ai_start()
        || !defjam_fighter_cinematic_start() || !defjam_fighter_finishers_start()) {
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
    fprintf(stderr, "[FIGHTERS] experimental roster enabled in disposable probe namespace only\n");
    return 1;
}

int defjam_fighter_runtime_start(void) {
    const char *path = getenv("RECOMP_FIGHTER_NAMES");
    const char *trace = getenv("RECOMP_TRACE_FIGHTER_NAMES");
    const char *probe = getenv("RECOMP_FIGHTER_NAMES_PROBE");
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
    }
}

void defjam_fighter_match_finished(void) {
    if (!s_window.bytes || !s_window.frozen || !s_immutable_reuse) return;
    validate_immutable_banks();
    if (!fighter_window_finish(&s_window)) fighter_stop("Could not finish native fighter selection ownership.");
    fprintf(stderr, "[FIGHTERS] selection ownership finished after native Game.Quit; immutable records retained\n");
    fprintf(stderr, "[FIGHTERS] resource observation phase=match_finished heap=%u contiguous=%u\n",
            xbox_HeapLiveBytes(), xbox_ContiguousLiveBytes());
}

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
        s_custom_metadata[i] = metadata; return changed;
    }
    if (s_custom_count >= FIGHTER_BINDINGS_MAX_COUNT) fighter_stop("Historical custom unlock journal is full.");
    s_custom_keys[s_custom_count] = identity; s_custom_metadata[s_custom_count++] = mark & FIGHTER_UNLOCK_METADATA;
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

static FighterPendingSave *pending_save(void) {
    if (s_pending_count >= 16) fighter_stop("Native fighter save batch exceeds its reviewed record budget.");
    return &s_pending[s_pending_count++];
}

static void expect_save(const FighterPendingSave *save) {
    lock_names();
    for (uint32_t i = 0; i < 16; ++i) if (!s_expected[i].active) {
        s_expected[i].save = *save;
        s_expected[i].batch = s_batch_number + 1;
        s_expected[i].index = s_pending_count - 1;
        s_expected[i].active = 1;
        unlock_names(); return;
    }
    unlock_names(); fighter_stop("Too many native fighter saves await file-close acknowledgement.");
}

void defjam_fighter_settings_saving(void) {
    if (!s_bindings.bytes) return;
    if (s_journal[0]) await_save_commit();
    if (!s_settings || MEM32(s_settings + 0x20) != MEM32(s_settings + 0x1264))
        fighter_stop("Native fighter unlock counts disagree before save staging.");
    defjam_fighter_settings_validate(s_settings, s_settings + 0x4C);
    if (s_journal[0]) {
        uint32_t count = MEM32(s_settings + 0x20), kept = 0;
        FighterPendingSave *save = pending_save();
        if (s_projecting_settings) fighter_stop("Reentrant native Options projection.");
        memcpy(s_live_settings, (const void *)XBOX_PTR(s_settings + 0x4C), FIGHTER_SETTINGS_SIZE);
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t mark = MEM32(s_settings + 0x12E0 + i * 4);
            FighterBinding binding;
            remember_custom(mark);
            if (fighter_bindings_find(&s_bindings, FIGHTER_BINDING_STABLE, mark & ~FIGHTER_UNLOCK_METADATA, &binding) && !(binding.flags & 1))
                MEM32(s_settings + 0x12E0 + kept++ * 4) = mark;
        }
        MEM32(s_settings + 0x1264) = kept;
        for (uint32_t i = kept; i < FIGHTER_UNLOCK_CAPACITY; ++i) MEM32(s_settings + 0x12E0 + i * 4) = UINT32_MAX;
        memset(save, 0, sizeof *save); memcpy(save->name, "Options", 7); save->name_size = 7; save->size = FIGHTER_SETTINGS_SIZE;
        memcpy(save->identity, (const void *)XBOX_PTR(s_settings + 0x1738), 64);
        memcpy(save->payload, (const void *)XBOX_PTR(s_settings + 0x4C), FIGHTER_SETTINGS_SIZE);
        expect_save(save);
        s_projecting_settings = 1;
        fprintf(stderr, "[FIGHTERS] staged retail-only Options: %u marks, %u historical custom marks\n", kept, s_custom_count);
    }
}

void defjam_fighter_settings_saved(void) {
    if (!s_projecting_settings) return;
    memcpy((void *)XBOX_PTR(s_settings + 0x4C), s_live_settings, FIGHTER_SETTINGS_SIZE);
    s_projecting_settings = 0;
}

void defjam_fighter_profile_staging(uint32_t name, uint32_t payload) {
    FighterPendingSave *save;
    if (!s_journal[0]) return;
    await_save_commit();
    save = pending_save(); memset(save, 0, sizeof *save);
    while (save->name_size < 32 && MEM8(name + save->name_size)) {
        uint8_t c = MEM8(name + save->name_size);
        if (c < 32 || c > 126 || strchr("\\/:*?\"<>|", c)) fighter_stop("Unsafe native profile staging name.");
        save->name[save->name_size++] = (char)c;
    }
    if (!save->name_size || MEM8(name + save->name_size)) fighter_stop("Native profile staging name exceeds its budget.");
    save->size = 0x5904;
    memcpy(save->identity, (const void *)XBOX_PTR(s_settings + 0x16F8), 64);
    memcpy(save->payload, (const void *)XBOX_PTR(payload), save->size);
    expect_save(save);
}

static void journal_word(FILE *file, uint32_t value) {
    uint8_t bytes[4] = {(uint8_t)value, (uint8_t)(value >> 8), (uint8_t)(value >> 16), (uint8_t)(value >> 24)};
    if (fwrite(bytes, 1, 4, file) != 4) fighter_stop("Could not stage fighter save journal.");
}

static FILE *open_journal(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2112];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2112)) fighter_stop("Invalid fighter journal path.");
    return _wfopen(wide, L"wbx");
#else
    return fopen(path, "wbx");
#endif
}

static void finish_journal(FILE *file, const char *temporary, const char *destination) {
    if (ferror(file) || fflush(file)) fighter_stop("Could not flush fighter save journal.");
#if defined(_WIN32)
    if (_commit(_fileno(file))) fighter_stop("Could not sync fighter save journal.");
    if (fclose(file)) fighter_stop("Could not close fighter save journal.");
    {
        wchar_t from[2112], to[2112];
        if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, temporary, -1, from, 2112)
            || !MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, destination, -1, to, 2112)
            || !MoveFileExW(from, to, MOVEFILE_WRITE_THROUGH)) fighter_stop("Could not publish fighter save journal.");
    }
#else
    if (fsync(fileno(file))) fighter_stop("Could not sync fighter save journal.");
    if (fclose(file)) fighter_stop("Could not close fighter save journal.");
    if (rename(temporary, destination)) fighter_stop("Could not publish fighter save journal.");
#endif
}

/* Do not let a subsequent operation overwrite files still being verified.
 * Waiting here (before staging/deleting), not on the first CloseHandle, lets
 * the previous native worker finish every file and its companion metadata. */
static void await_save_commit(void) {
    char path[2048];
    if (!s_batch_number) return;
    snprintf(path, sizeof path, "%s/%06u.committed", s_journal, s_batch_number);
    for (unsigned attempt = 0; attempt < 1000; ++attempt) {
        FILE *file = open_utf8(path);
        if (file) {
            uint8_t bytes[9];
            size_t size = fread(bytes, 1, sizeof bytes, file);
            int failed = ferror(file);
            fclose(file);
            if (failed || size != 8 || memcmp(bytes, "FSC1", 4) || read_word(bytes + 4) != s_batch_number)
                fighter_stop("Invalid fighter save publication acknowledgement.");
            return;
        }
#if defined(_WIN32)
        Sleep(10);
#else
        usleep(10000);
#endif
    }
    fighter_stop("Previous fighter save was not committed; reload the last verified profile.");
}

static void test_save_stop(int point) {
    if (s_test_save_stop != point) return;
    fprintf(stderr, "[FIGHTERS-TEST] interrupted native save: point=%d batch=%u exit=86\n", point, s_batch_number);
    fflush(stderr);
    _Exit(86); /* Internal isolated research only; bypass all native cleanup. */
}

int defjam_fighter_profile_delete_begin(uint32_t root, uint32_t name, char snapshot[33]) {
    unsigned length = 0;
    if (!s_journal[0]) return 0;
    if (!root || !name || (MEM8(root) != 'U' && MEM8(root) != 'u')
        || MEM8(root + 1) != ':' || MEM8(root + 2) != '\\' || MEM8(root + 3))
        fighter_stop("Unreviewed native profile deletion namespace.");
    await_save_commit();
    if (s_pending_count) fighter_stop("Native deletion crossed an unsealed save operation.");
    memset(snapshot, 0, 33);
    while (length < 32 && MEM16(name + length * 2)) {
        uint16_t c = MEM16(name + length * 2);
        if (c < 32 || c > 126 || strchr("\\/:*?\"<>|", (char)c))
            fighter_stop("Unsafe native profile deletion name.");
        snapshot[length++] = (char)c;
    }
    if (!length || MEM16(name + length * 2) || !strcmp(snapshot, "Options"))
        fighter_stop("Unreviewed native profile deletion identity.");
    return 1;
}

void defjam_fighter_profile_delete_end(const char *name, int success) {
    FILE *file;
    char temporary[2112], destination[2112];
    if (!success) {
        fprintf(stderr, "[FIGHTERS] native profile deletion failed: %s; committed profile retained\n", name);
        return;
    }
    if (++s_batch_number > 10000) fighter_stop("Too many native profile operations.");
    snprintf(temporary, sizeof temporary, "%s/%06u.pending", s_journal, s_batch_number);
    snprintf(destination, sizeof destination, "%s/%06u.batch", s_journal, s_batch_number);
    file = open_journal(temporary);
    if (!file) fighter_stop("Could not create native profile deletion receipt.");
    fwrite("FSD1", 1, 4, file); journal_word(file, 1); journal_word(file, s_batch_number);
    journal_word(file, (uint32_t)strlen(name)); journal_word(file, 0); fwrite(name, 1, 32, file);
    finish_journal(file, temporary, destination);
    fprintf(stderr, "[FIGHTERS] native profile deletion completed: batch=%u name=%s; awaiting verified absence\n", s_batch_number, name);
    await_save_commit();
    fprintf(stderr, "[FIGHTERS] native profile deletion committed: batch=%u name=%s\n", s_batch_number, name);
}

void defjam_fighter_save_write(uint32_t handle, uint32_t buffer, uint32_t size, uint32_t written, int success, int asynchronous) {
    int result;
    if (!s_journal[0]) return;
    lock_names();
    result = fighter_save_io_write(&s_save_io, handle, (const uint8_t *)XBOX_PTR(buffer), size, written ? MEM32(written) : 0, success && !asynchronous);
    unlock_names();
    if (result < 0) fighter_stop("A native fighter save write was incomplete or used an unreviewed IO path.");
    if (result) fprintf(stderr, "[FIGHTERS] completed native save write: handle=%08X bytes=%u\n", handle, size);
    if (result && size == 0x4C && !memcmp((const void *)XBOX_PTR(buffer), "20CM", 4))
        test_save_stop(MEM32(buffer + 12) == 0x1490 ? 2 : 3);
}

void defjam_fighter_save_seek(uint32_t handle) {
    if (!s_journal[0]) return;
    lock_names(); fighter_save_io_seek(&s_save_io, handle); unlock_names();
}

void defjam_fighter_save_close(uint32_t handle, int success) {
    const uint8_t *bytes = NULL;
    uint32_t size = 0, matches = 0, match = 0;
    int result;
    if (!s_journal[0]) return;
    lock_names();
    result = fighter_save_io_close(&s_save_io, handle, success, &bytes, &size);
    if (!result) { unlock_names(); return; }
    if (result < 0) { unlock_names(); fighter_stop("Native fighter save did not finish and close successfully."); return; }
    for (uint32_t i = 0; i < 16; ++i) {
        FighterExpectedSave *expected = &s_expected[i];
        if (expected->active && size == expected->save.size + 0x8C
            && !memcmp(bytes + 0x4C, expected->save.identity, 64)
            && !memcmp(bytes + 0x8C, expected->save.payload, expected->save.size)) { ++matches; match = i; }
    }
    if (matches != 1) { unlock_names(); fighter_stop("Native closed save has no unique staged fighter record."); return; }
    {
        FighterExpectedSave *expected = &s_expected[match];
        char temporary[2112], destination[2112];
        FILE *file;
        snprintf(temporary, sizeof temporary, "%s/%06u-%02u.pending", s_journal, expected->batch, expected->index);
        snprintf(destination, sizeof destination, "%s/%06u-%02u.closed", s_journal, expected->batch, expected->index);
        file = open_journal(temporary);
        if (!file) { unlock_names(); fighter_stop("Could not create native fighter save receipt."); return; }
        fwrite("FSA1", 1, 4, file); journal_word(file, 1); journal_word(file, expected->batch);
        journal_word(file, expected->index); journal_word(file, size); fwrite(bytes, 1, size, file);
        finish_journal(file, temporary, destination);
        fprintf(stderr, "[FIGHTERS] native save closed: batch=%u record=%u name=%.*s bytes=%u\n",
                expected->batch, expected->index, expected->save.name_size, expected->save.name, size);
        expected->active = 0;
    }
    unlock_names();
}

void defjam_fighter_save_batch(void) {
    FILE *file;
    char temporary[2112], destination[2112];
    if (!s_journal[0] || !s_pending_count) return;
    if (s_projecting_settings || ++s_batch_number > 10000) fighter_stop("Invalid fighter save batch lifecycle.");
    snprintf(temporary, sizeof temporary, "%s/%06u.pending", s_journal, s_batch_number);
    snprintf(destination, sizeof destination, "%s/%06u.batch", s_journal, s_batch_number);
    file = open_journal(temporary);
    if (!file) fighter_stop("Could not create fighter save journal.");
    fwrite("FSB1", 1, 4, file); journal_word(file, 1); journal_word(file, s_batch_number);
    journal_word(file, s_pending_count); journal_word(file, s_custom_count); journal_word(file, 0);
    for (uint32_t i = 0; i < s_pending_count; ++i) {
        FighterPendingSave *save = &s_pending[i];
        journal_word(file, save->name_size); journal_word(file, save->size);
        fwrite(save->identity, 1, 64, file); fwrite(save->name, 1, 32, file); fwrite(save->payload, 1, save->size, file);
    }
    for (uint32_t i = 0; i < s_custom_count; ++i) { journal_word(file, s_custom_keys[i]); journal_word(file, s_custom_metadata[i]); }
    finish_journal(file, temporary, destination);
    fprintf(stderr, "[FIGHTERS] save batch %u sealed: %u records; awaiting independently verified native files\n", s_batch_number, s_pending_count);
    s_pending_count = 0;
    test_save_stop(1);
}

void defjam_fighter_unlock_inserting(uint32_t self) {
    if (!s_bindings.bytes || !s_settings || self != s_settings + 0x1C) return;
    /* A larger live array also requires the save extension. Until it is wired,
     * reject the next insertion before the original unchecked write occurs. */
    if (MEM32(self + 4) >= MEM32(self) || MEM32(self) != FIGHTER_UNLOCK_CAPACITY)
        fighter_stop("Native Character unlock storage is full; expanded persistence is required.");
    if (s_journal[0]) remember_custom(MEM32(MEM32(g_esp + 4)));
}

void defjam_fighter_selection_gate(uint32_t selection) {
    FighterBinding binding;
    if (!s_bindings.bytes || selection < 100 || selection > 0x7fffffffu) return;
    if (selection >= 128 || !fighter_bindings_find(&s_bindings, FIGHTER_BINDING_SELECTION, selection, &binding)
        || !(binding.flags & 2))
        fighter_stop("Logical fighter selection has no safe native binding; confirmation is blocked.");
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
            uint32_t mark = row.stable_handle;
            for (uint32_t i = 0; i < s_custom_count; ++i)
                if (s_custom_keys[i] == row.stable_handle) mark |= s_custom_metadata[i];
            keys[kept++] = mark;
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

int defjam_fighter_ui_command(uint32_t command) {
    static const char prefix[] = "Fighters.KeepReady";
    char text[40]; uint32_t i;
    if (!s_window.bytes || !command) return 0;
    for (i = 0; i < sizeof prefix - 1; ++i)
        if (MEM8(command + i) != (uint8_t)prefix[i]) return 0;
    for (i = 0; i < sizeof text; ++i) {
        text[i] = (char)MEM8(command + i);
        if (!text[i]) break;
    }
    if (i == sizeof text || fighter_window_command(&s_window, text) != 1)
        fighter_stop("Native ready ownership differs from the participant bindings, or the match is still active.");
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
    return row.selection_key;
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
