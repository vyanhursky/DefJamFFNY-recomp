#define _CRT_SECURE_NO_WARNINGS
#include "fighter_runtime.h"
#include "hooks/fighter_names.h"
#include "hooks/fighter_roster.h"
#include "hooks/fighter_bindings.h"
#include "hooks/guest_call.h"
#include "host.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if !defined(_WIN32)
#include <sched.h>
#endif

extern void sub_00029680(void);
extern void sub_00045180(void);
extern void sub_000BE760(void);
extern void sub_000BE760_gen(void);
static FighterNames s_names;
static FighterBindings s_bindings;
static uint8_t *s_bytes;
static uint8_t *s_binding_bytes;
static uint32_t s_validated_database;
static uint32_t s_guest_text;
static volatile int s_lock;
static RECOMP_TLS unsigned s_trace_count;
static int s_trace;
static int s_probe, s_probed;
static char s_research_sod[2048];
static char s_research_screens[2048];
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
        : file_name(relative, "screens/screens.viv") ? s_research_screens : NULL;
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
    const char *bindings = getenv("RECOMP_FIGHTER_BINDINGS");
    const char *data = getenv("DEFJAM_DATA"), *settings = getenv("RECOMP_SETTINGS"), *leaf;
    if (!sod || !*sod) return !screens || !*screens;
    /* This development entry point cannot use the normal profile namespace or
     * player settings. The probe driver owns this disposable data root and the
     * harness guards its complete save directory. No runtime capability is
     * advertised until persistence, menus and authored assets are accepted. */
    leaf = data ? data + strlen(data) : NULL;
    while (leaf && leaf > data && leaf[-1] != '/' && leaf[-1] != '\\') --leaf;
    if (!leaf || strcmp(leaf, "fighter-runtime-probe") || !settings || strcmp(settings, "none")
        || !s_names.count || strlen(sod) >= sizeof s_research_sod
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
    strcpy(s_research_sod, sod);
    if (screens) strcpy(s_research_screens, screens);
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
    if (MEM32(base + table_header) != 0x4ce5b1b2u || MEM32(base + table_header + 12) != s_bindings.active_count)
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
    guest_regs_restore(&saved);
    s_validated_database = database;
    fprintf(stderr, "[FIGHTERS] native identity bindings verified: %u active, %u dormant\n",
            s_bindings.active_count, s_bindings.count - s_bindings.active_count);
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
    if (!fighter_bindings_find(&s_bindings, FIGHTER_BINDING_NATIVE, handle, &binding))
        fighter_stop("Native fighter handle has no stable identity binding.");
    MEM32(output) = binding.stable_handle;
}

static uint32_t read_word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
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
