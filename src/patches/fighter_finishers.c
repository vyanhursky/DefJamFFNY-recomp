/* Independently owned paired combat motions retain verified donor behavior.
 * The native external provider owns the banks; we own its bounded mask/name
 * pool until provider teardown. No WPAR byte or adjacent static table grows. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_config.h"
#include "fighter_finishers.h"
#include "fighter_fatal.h"
#include "fighter_runtime.h"
#include "fighter_cpu_pool.h"
#include "fighter_graph_proof.h"
#include "fighter_events.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>

#define FIN_CORES 16384u
#define FIN_EXTRA 8192u
#define FIN_BASE 709u
#define FIN_RETAIL 164u
#define FIN_ROWS (4u * (FIN_CORES - 141u))
#define FIN_BYTES (52u + FIN_ROWS * 36u)
#define FIN_ACTORS 0x3B92E0u
#define FIN_STRIDE 0x12E8u
typedef struct Finisher { uint32_t choice, ordinal, slot; } Finisher;
static Finisher s_bindings[FIN_CORES][4];
static uint8_t s_counts[FIN_CORES];
static char s_names[FIN_EXTRA][8], s_archive[2048];
static uint32_t s_parameter_donors[FIN_EXTRA];
static uint8_t s_parameter_observed[FIN_EXTRA];
static uint8_t s_timelines[FIN_EXTRA];
static uint32_t s_timeline_names;
static uint32_t s_rows, s_motion_count, s_storage, s_names_offset, s_provider;
static unsigned s_logs;
static RECOMP_TLS FighterFinisherScope s_scope;
extern void sub_00029680(void);
extern void sub_00029760(void);
extern void xbox_NoteAnchorEvent(const char *text);
extern uint32_t xbox_HeapAlloc(uint32_t size,uint32_t alignment);

static uint32_t fin_word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static void fin_stop(const char *message) {
    defjam_fighter_fatal("finisher", message);
}
static FILE *fin_open(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048)) return NULL;
    return _wfopen(wide, L"rb");
#else
    return fopen(path, "rb");
#endif
}
int defjam_fighter_finishers_start(void) {
    const char *path = defjam_fighter_env("RECOMP_FIGHTER_FINISHERS");
    const char *binding = defjam_fighter_env("RECOMP_FIGHTER_FINISHER_BINDINGS");
    const char *hash = defjam_fighter_env("RECOMP_FIGHTER_FINISHERS_SHA256");
    if (!path || !*path) return (!binding || !*binding) && (!hash || !*hash);
    if (!defjam_fighter_research_active() || s_rows || !binding || !*binding
        || strlen(path) >= sizeof s_archive || strlen(binding) >= 2048 || !defjam_fighter_file_matches(path, hash)) return 0;
    FILE *file = fin_open(binding);
    if (!file) return 0;
    int sized=!fseek(file,0,SEEK_END);
    long table_size=sized?ftell(file):-1;
    if (table_size<52 || (uint64_t)table_size>FIN_BYTES+(64u<<20) || fseek(file,0,SEEK_SET)) { fclose(file);return 0; }
    uint8_t *table = (uint8_t *)malloc((size_t)table_size + 1);
    if (!table) { fclose(file); return 0; }
    size_t bytes = fread(table, 1, (size_t)table_size + 1, file);
    int valid = !ferror(file) && bytes == (size_t)table_size;
    if (fclose(file)) valid = 0;
    uint32_t rows = valid ? fin_word(table + 8) : 0;
    uint32_t count = valid ? fin_word(table + 12) : 0;
    int timed=valid && !memcmp(table,"FBP4",4) && fin_word(table+4)==4;
    int graph=timed || (valid && !memcmp(table,"FBP3",4) && fin_word(table+4)==3);
    uint32_t stride=timed?36:graph || (valid && !memcmp(table,"FBP2",4) && fin_word(table+4)==2)?32:28;
    char digest[65];
    if (valid) {
        hex(table + 20, digest);
        valid = (stride >= 32 || (!memcmp(table, "FBP1", 4) && fin_word(table + 4) == 1)) && rows && rows <= FIN_ROWS
            && (graph ? bytes > 52u+rows*stride : bytes == 52u+rows*stride)
            && count > FIN_RETAIL && count <= FIN_RETAIL + FIN_EXTRA
            && !(count & 1) && !strcmp(digest, hash);
        if (valid && graph) valid=defjam_fighter_graph_start(table+52+rows*stride,bytes-52-rows*stride,count);
    }
    if (valid) {
        file = fin_open(path);
        if (!file) valid = 0;
        else {
            valid = !fseek(file, 0, SEEK_END);
            long size = valid ? ftell(file) : -1;
            valid = valid && size >= 16 && (uint64_t)size <= (512ull << 20)
                && (uint32_t)size == fin_word(table + 16);
            if (fclose(file)) valid = 0;
        }
    }
    memset(s_counts, 0, sizeof s_counts); memset(s_names, 0, sizeof s_names);
    memset(s_timelines,0,sizeof s_timelines);
    memset(s_parameter_donors, 0xFF, sizeof s_parameter_donors);
    uint32_t previous_core = 140, previous_choice = 0;
    for (uint32_t i = 0; valid && i < rows; ++i) {
        const uint8_t *row = table + 52 + i * stride;
        uint32_t core = fin_word(row), selection = fin_word(row + 4);
        uint32_t slot = stride >= 32 ? selection : UINT32_MAX;
        uint32_t choice=fin_word(row+(stride==28?4:8)),ordinal=fin_word(row+(stride==28?8:12));
        uint32_t flags=timed?fin_word(row+16):0;
        const uint8_t *names = row + stride - 16;
        if (core < 141 || core >= FIN_CORES || core < previous_core || choice >= 82
            || (stride >= 32 && slot >= 4) || flags>1
            || (core == previous_core && selection <= previous_choice) || s_counts[core] == 4
            || ordinal < 873 || ordinal >= FIN_BASE + count - 1 || ((ordinal - 873) & 1)) { valid = 0; break; }
        for (unsigned role = 0; role < 2; ++role) {
            const uint8_t *name = names + role * 8;
            if (name[0] != 'P' || name[5] != '_' || name[6] != (role ? 'B' : 'A') || name[7]) valid = 0;
            for (unsigned j = 1; j < 5; ++j) if (name[j] < '0' || name[j] > '9') valid = 0;
            char *destination = s_names[ordinal - 873 + role];
            if (destination[0] && (memcmp(destination, name, 8) || s_timelines[ordinal-873+role]!=flags)) valid = 0;
            if (flags && (!defjam_fighter_graph_has(ordinal+role)
                || !defjam_fighter_events_has((const char *)name,role?1:3))) valid=0;
            if (!flags && defjam_fighter_events_has((const char *)name,0)) valid=0;
            uint32_t donor = FIN_BASE + 2 * choice + role;
            uint32_t *parameter = &s_parameter_donors[ordinal - 873 + role];
            if (*parameter != UINT32_MAX && *parameter != donor) valid = 0;
            if (valid) { memcpy(destination, name, 8); *parameter = donor;s_timelines[ordinal-873+role]=(uint8_t)flags; }
            if (valid && graph && !defjam_fighter_graph_known(ordinal+role,destination)) valid=0;
        }
        if (memcmp(names, names + 8, 6)) valid = 0;
        if (valid) {
            Finisher *entry = &s_bindings[core][s_counts[core]++];
            entry->choice = choice; entry->ordinal = ordinal; entry->slot = slot;
            previous_core = core; previous_choice = selection;
        }
    }
    if (valid && graph) valid=defjam_fighter_graph_complete();
    if (valid) {
        s_rows = rows; s_motion_count = count; strcpy(s_archive, path);
        fprintf(stderr, "[FIGHTERS] validated %u independent paired finisher bindings (%u motion slots)\n", rows, count);
    }
    free(table); return valid;
}
const char *defjam_fighter_finishers_path(void) { return s_archive; }
int defjam_fighter_finisher_cpu_file(const char *path) {
    if (!s_rows || !s_storage || s_provider || !defjam_fighter_research_active()
        || strncmp(path, "motion/blazin.viv|", 18)) return 0;
    for (uint32_t i = 0; i < s_motion_count - FIN_RETAIL; ++i) {
        if (!s_names[i][0] || !MEM8(s_storage + FIN_RETAIL + i)) continue;
        char expected[64];
        snprintf(expected, sizeof expected, "motion/blazin.viv|%s.ord", s_names[i]);
        if (!strcmp(path, expected)) return 1;
    }
    return 0;
}
static int fin_actor(uint32_t actor) {
    return actor >= FIN_ACTORS && actor - FIN_ACTORS < 4 * FIN_STRIDE
        && (actor - FIN_ACTORS) % FIN_STRIDE == 0 && MEM32(actor + 0x28) != UINT32_MAX;
}
void defjam_fighter_finishers_mask(uint32_t base, uint32_t count, uint32_t mask) {
    if (!s_rows || !defjam_fighter_research_active()) return;
    if (MEM32(base) != FIN_BASE || MEM32(count) != FIN_RETAIL || MEM32(mask) != 0x3BE628 || s_storage)
        fin_stop("unexpected external motion registration");
    s_names_offset = (s_motion_count + 3u) & ~3u;
    uint32_t size = s_names_offset + (s_motion_count - FIN_RETAIL) * 8;
    uint32_t args[3] = { size, 0x29D4B4, 0 };
    s_storage = guest_call(sub_00029680, 0, 3, args);
    if (!s_storage || s_storage > UINT32_MAX - size) fin_stop("external motion metadata allocation failed");
    memset((void *)XBOX_PTR(s_storage), 0, size);
    memcpy((void *)XBOX_PTR(s_storage), (const void *)XBOX_PTR(0x3BE628), FIN_RETAIL);
    memcpy((void *)XBOX_PTR(s_storage + s_names_offset), s_names, (s_motion_count - FIN_RETAIL) * 8);
    if (!s_timeline_names) {
        int needed=0;for (uint32_t i=0;i<s_motion_count-FIN_RETAIL;++i) if (s_timelines[i]) needed=1;
        if (needed) {
            uint32_t bytes=(s_motion_count-FIN_RETAIL)*8;
            s_timeline_names=xbox_HeapAlloc(bytes,16);
            if (!s_timeline_names || s_timeline_names>UINT32_MAX-bytes) fin_stop("timeline name allocation failed");
            memcpy((void *)XBOX_PTR(s_timeline_names),s_names,bytes);
            fprintf(stderr,"[FIGHTERS] immutable snapshot timeline names retained bytes=%u\n",bytes);
        }
    }
    for (unsigned slot = 0; slot < 4; ++slot) {
        uint32_t actor = FIN_ACTORS + slot * FIN_STRIDE, core = MEM32(actor + 0x2C);
        if (!fin_actor(actor) || core >= FIN_CORES) continue;
        for (unsigned i = 0; i < s_counts[core]; ++i) {
            const Finisher *entry = &s_bindings[core][i];
            int selected = 0;
            for (unsigned j = 0; j < 4; ++j)
                if ((entry->slot == UINT32_MAX || entry->slot == j)
                    && MEM32(actor + 0xBB8 + j * 4) == entry->choice) selected = 1;
            if (!selected) fin_stop("paired animation differs from the retained WPAR choice");
            MEM8(s_storage + entry->ordinal - FIN_BASE) = 1;
            MEM8(s_storage + entry->ordinal + 1 - FIN_BASE) = 1;
        }
    }
    MEM32(count) = s_motion_count; MEM32(mask) = s_storage;
}
void defjam_fighter_finishers_loaded(uint32_t provider) {
    if (!s_rows || !defjam_fighter_research_active()) return;
    if (!s_storage || s_provider || MEM32(provider + 0x2C) != s_motion_count
        || MEM32(provider + 0x30) != FIN_BASE || MEM32(provider + 0x34) != s_storage)
        fin_stop("external provider differs from admitted generation");
    uint32_t map = MEM32(provider + 0x14), records = MEM32(provider + 0x18), loaders = MEM32(provider + 0x28);
    uint32_t loaded = MEM32(provider + 0x38), expected = 0;
    uint8_t seen[FIN_RETAIL + FIN_EXTRA] = {0};
    for (uint32_t i = 0; i < s_motion_count; ++i) if (MEM8(s_storage + i)) ++expected;
    if (!map || !records || !loaders || loaded != expected || loaded > s_motion_count)
        fin_stop("external provider omitted active motions");
    for (uint32_t i = 0; i < loaded; ++i) {
        uint32_t ordinal = MEM32(map + i * 24);
        if (ordinal < FIN_BASE || ordinal - FIN_BASE >= s_motion_count || seen[ordinal - FIN_BASE]
            || !MEM8(s_storage + ordinal - FIN_BASE)) fin_stop("external provider has unexpected or duplicate keys");
        seen[ordinal - FIN_BASE] = 1;
        if (ordinal < 873) continue;
        if (memcmp((const void *)XBOX_PTR(map + i * 24 + 8), s_names[ordinal - 873], 8)
            || MEM32(map + i * 24 + 4) != i) fin_stop("external key resolves to the wrong named bank");
        uint32_t bank = MEM32(loaders + i * 12 + 4);
        if (!defjam_fighter_cpu_contains(bank)) fin_stop("owned animation escaped CPU storage");
        if (!defjam_fighter_graph_bound(ordinal,bank)) fin_stop("owned graph missed its preconstructor seal");
        uint32_t skeletal = MEM32(records + i * 16 + 8), root = MEM32(records + i * 16 + 4);
        int full_graph=defjam_fighter_graph_has(ordinal);
        if (full_graph && !defjam_fighter_graph_bank(ordinal,bank,skeletal,root))
            fin_stop("full graph differs from its relocated compiler proof");
        if (!bank || !MEM32(bank + 16) || !MEM32(bank + 20) || !MEM32(bank + 4) || MEM32(bank + 4) > 65535)
            fin_stop("external bank has invalid indexed records");
        if (skeletal >= MEM32(bank + 4) || root >= MEM32(bank + 4)) fin_stop("external bank omitted paired records");
        uint32_t name = MEM32(MEM32(bank + 20) + skeletal * 4);
        char expected_name[12]; snprintf(expected_name, sizeof expected_name, "%s_s", s_names[ordinal - 873]);
        if (!name || memcmp((const void *)XBOX_PTR(name), expected_name, 10)) fin_stop("external skeletal lookup silently fell back");
        if (full_graph) continue;
        uint32_t parent = MEM32(MEM32(bank + 16) + skeletal * 4);
        if (!parent || MEM8(parent) != 15 || MEM8(parent + 1) || MEM8(parent + 8) != 1 || MEM8(parent + 9))
            fin_stop("external authored body has an unexpected parent");
        uint32_t child = MEM32(parent + 12);
        if (!child || MEM8(child) != 11 || MEM8(child + 1)) fin_stop("external authored body has no typed quaternion child");
    }
    s_provider = provider; s_logs = 0; memset(s_parameter_observed, 0, sizeof s_parameter_observed);
    fprintf(stderr, "[FIGHTERS] paired finisher provider verified %u active motions provider=%08X storage=%08X\n",
            loaded, s_provider, s_storage);
}
void defjam_fighter_finishers_release(uint32_t manager) {
    if (!s_storage || (s_provider && s_provider != manager + 0x438)) return;
    uint32_t address = s_storage;
    fprintf(stderr, "[FIGHTERS] paired finisher metadata released after native destructor manager=%08X provider=%08X storage=%08X\n",
            manager, s_provider, s_storage);
    s_storage = s_provider = 0;
    defjam_fighter_graph_release();
    guest_call(sub_00029760, 0, 1, &address);
    defjam_fighter_cpu_released();
}
uint32_t defjam_fighter_finisher_name(uint32_t mode, uint32_t ordinal, uint32_t caller) {
    if (!s_rows || !s_storage || mode == 1 || ordinal < 873 || ordinal >= FIN_BASE + s_motion_count
        || !s_names[ordinal - 873][0] || !defjam_fighter_research_active()) return 0;
    /* The snapshot label selects BOTH camera and animation-tag timelines.
     * FBP4 admits both together. Keep its name in process-generation storage:
     * native audio/camera snapshots can outlive the external provider mask. */
    if (caller == 0x1A3ECF) {
        if (s_timelines[ordinal-873]) {
            if (!s_timeline_names) fin_stop("owned snapshot timeline has no retained identity");
            return s_timeline_names+(ordinal-873)*8;
        }
        uint32_t donor = s_parameter_donors[ordinal - 873];
        if (donor >= 873 || !MEM32(0x2EC1C8 + donor * 4)) fin_stop("missing inherited camera identity");
        return MEM32(0x2EC1C8 + donor * 4);
    }
    return s_storage + s_names_offset + (ordinal - 873) * 8;
}
FighterFinisherScope defjam_fighter_finisher_enter(uint32_t actor) {
    FighterFinisherScope previous = s_scope;
    memset(&s_scope, 0, sizeof s_scope);
    if (s_rows && defjam_fighter_research_active() && fin_actor(actor)) {
        uint32_t core = MEM32(actor + 0x2C);
        if (core < FIN_CORES && s_counts[core]) { s_scope.subject = actor; s_scope.counterpart = MEM32(actor); s_scope.core = core; }
    }
    return previous;
}
void defjam_fighter_finisher_leave(FighterFinisherScope previous) { s_scope = previous; }
uint32_t defjam_fighter_finisher_parameters(uint32_t output, uint32_t source, uint32_t caller) {
    /* Animation ordinals and packed FZUI behavior rows are separate domains.
     * 1A85A0 computes this unchecked pointer before calling the sole decoder.
     * Preserve all 39 donor bytes (timing, reaction and event semantics), while
     * actor+88/+8C retain the independently owned animation and its name. */
    if (!s_rows || !defjam_fighter_research_active() || caller != 0x1A867E || output < 0x2BC) return source;
    uint32_t actor = output - 0x2BC;
    if (!fin_actor(actor) || MEM32(actor + 0x84) != 0) return source;
    uint32_t ordinal = MEM32(actor + 0x8C);
    if (ordinal < 873) return source;
    uint32_t base = MEM32(0x3B8634), stride = MEM32(0x3B862C);
    if (!s_provider || ordinal >= FIN_BASE + s_motion_count || MEM32(actor + 0x88) != ordinal
        || s_parameter_donors[ordinal - 873] == UINT32_MAX || !MEM8(s_storage + ordinal - FIN_BASE)
        || !base || stride != 39 || MEM32(0x3B8630) != 873
        || base > UINT32_MAX - (FIN_BASE + s_motion_count) * 39 || source != base + ordinal * 39)
        fin_stop("external animation has no verified inherited parameter row");
    if (!s_parameter_observed[ordinal - 873]) {
        s_parameter_observed[ordinal - 873] = 1;
        fprintf(stderr, "[FIGHTERS] finisher parameters ordinal %u inherited %u\n", ordinal, s_parameter_donors[ordinal - 873]);
    }
    return base + s_parameter_donors[ordinal - 873] * 39;
}
uint32_t defjam_fighter_finisher_motion(uint32_t actor, uint32_t motion, uint32_t mode, uint32_t caller) {
    if (!s_scope.subject || (caller != 0x1D3BA0 && caller != 0x1D3BAA)) return motion;
    uint32_t subject = s_scope.subject, action = MEM32(subject + 0xF50), role = caller == 0x1D3BAA;
    if (!(MEM8(subject + 0x926) & 1)) return motion;
    if (!((action >= 31 && action <= 34) || (action >= 38 && action <= 41))) fin_stop("unexpected paired action slot");
    uint32_t slot = action >= 38 ? action - 38 : action - 31;
    uint32_t choice = MEM32(subject + 0xBB8 + 4 * slot);
    for (unsigned i = 0; i < s_counts[s_scope.core]; ++i) {
        const Finisher *entry = &s_bindings[s_scope.core][i];
        if (entry->slot != UINT32_MAX && entry->slot != slot) continue;
        if (entry->choice != choice) {
            if (entry->slot != UINT32_MAX) fin_stop("paired action changed its verified slot choice");
            continue;
        }
        if (!s_provider || !fin_actor(actor) || actor != (role ? s_scope.counterpart : subject)
            || MEM32(subject + 0x2C) != s_scope.core || mode != 6 || motion != 10709 + 2 * choice + role)
            fin_stop("paired execution differs from its subject/counterpart binding");
        if (defjam_fighter_graph_has(entry->ordinal+role)
            && !defjam_fighter_graph_actor(entry->ordinal+role,actor))
            fin_stop("full graph actual body/face/hand context was not admitted");
        if (++s_logs <= 128) fprintf(stderr, "[FIGHTERS] finisher core %u subject %u counterpart %u role %u ordinal %u name %s\n",
            s_scope.core, (subject - FIN_ACTORS) / FIN_STRIDE, (s_scope.counterpart - FIN_ACTORS) / FIN_STRIDE,
            role, entry->ordinal + role, s_names[entry->ordinal - 873 + role]);
        if (!role) {
            char anchor[64];snprintf(anchor,sizeof anchor,"fighter-finisher:%s",s_names[entry->ordinal-873]);
            xbox_NoteAnchorEvent(anchor);
        }
        return 10000 + entry->ordinal + role;
    }
    return motion;
}
