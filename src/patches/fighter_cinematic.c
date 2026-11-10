/* Independent simple intro/victory bindings, with native resource ownership. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_cinematic.h"
#include "fighter_runtime.h"
#include "fighter_behavior_identity.h"
#include "fighter_film_proof.h"
#include "hooks/mod_sha256.h"
#include "hooks/guest_call.h"
#include <stdlib.h>

#define CIN_CORE_LIMIT 16384u
#define CIN_BINDING_LIMIT (CIN_CORE_LIMIT+CAF_BEHAVIOR_MAX)
#define CIN_TABLE_LIMIT (88u + 24u * CIN_BINDING_LIMIT)
static char s_clips[CIN_BINDING_LIMIT][2][8];
static uint8_t s_full_clips[CIN_BINDING_LIMIT],s_full_blazin[CIN_CORE_LIMIT];
static CafBehaviorBinding s_caf_bindings[CAF_BEHAVIOR_MAX];
static uint32_t s_caf_count;
static uint8_t s_absolute_blazin[CIN_CORE_LIMIT];
static uint32_t s_count;
static char s_blazin[CIN_CORE_LIMIT][4][8];
static uint32_t s_blazin_count;
static char s_archive[2048];
static RECOMP_TLS uint64_t s_context;
static RECOMP_TLS uint32_t s_alloc_manager;
static uint32_t s_cache_manager, s_cache_count, s_cache_descriptors, s_cache_requests;
static unsigned s_cache_allocations, s_cache_constructed;
static uint32_t s_cache_cores[4];
static unsigned s_test_readied;
static struct {uint32_t descriptor,manager,slot,core;char name[8];} s_owners[256];
static unsigned owner_record(uint32_t descriptor) {
    unsigned empty=256;
    for (unsigned i=0;i<256;++i) {
        if (s_owners[i].descriptor==descriptor) return i;
        if (!s_owners[i].descriptor && empty==256) empty=i;
    }
    return empty;
}
extern void sub_001A5190(void);
extern void sub_000A2E20(void);
extern void sub_00087AF0(void);
extern void sub_000A3E80(void);
extern void sub_000A3130(void);
extern void xbox_NoteAnchorEvent(const char *text);

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
static int cin_blazin_start(const char *path, const char *hash) {
    const char *bindings = getenv("RECOMP_FIGHTER_BLAZIN_BINDINGS");
    if (!bindings || !*bindings) return 1;
    if (strlen(bindings) >= 2048) return 0;
    FILE *file = cin_open(bindings);
    if (!file) return 0;
    const size_t limit = 48u + 44u * (CIN_CORE_LIMIT - 141u);
    uint8_t *table = (uint8_t *)malloc(limit + 1);
    if (!table) { fclose(file); return 0; }
    size_t size = fread(table, 1, limit + 1, file);
    int valid = !ferror(file) && size >= 48 && size <= limit;
    if (fclose(file)) valid = 0;
    uint32_t count = valid ? cin_word(table + 8) : 0;
    uint32_t version=valid?cin_word(table+4):0,stride=version==3?44u:version==2?40u:36u;
    char digest[65];
    if (valid) {
        hex(table + 16, digest);
        valid = ((version==1 && !memcmp(table,"FBZ1",4)) || (version==2 && !memcmp(table,"FBZ2",4))
                 || (version==3 && !memcmp(table,"FBZ3",4))) && count
            && count <= CIN_CORE_LIMIT - 141 && size == 48u + stride * count
            && !strcmp(digest, hash) && cin_size(path, cin_word(table + 12));
    }
    uint32_t previous = 140;
    memset(s_blazin, 0, sizeof s_blazin);
    memset(s_full_blazin,0,sizeof s_full_blazin);
    memset(s_absolute_blazin,0,sizeof s_absolute_blazin);
    for (uint32_t i = 0; valid && i < count; ++i) {
        const uint8_t *row = table + 48 + stride * i;
        uint32_t core = cin_word(row);
        if (core <= previous || core >= CIN_CORE_LIMIT || !s_clips[core][0][0]) { valid = 0; break; }
        for (unsigned phase = 0; phase < 4; ++phase) {
            const uint8_t *name = row + 4 + phase * 8;
            if (name[0] != 'B' || name[6] || name[7]) valid = 0;
            for (unsigned j = 1; j < 6; ++j) if (name[j] < '0' || name[j] > '9') valid = 0;
        }
        uint32_t flags=version>=2?cin_word(row+36):0,absolute=version==3?cin_word(row+40):0;
        if ((flags&~15u) || (absolute&~8u) || (absolute&~flags)) valid=0;
        if (valid) { memcpy(s_blazin[core], row + 4, 32);s_full_blazin[core]=(uint8_t)flags;
            s_absolute_blazin[core]=(uint8_t)absolute; previous = core; }
    }
    if (valid) {
        s_blazin_count = count;
        fprintf(stderr, "[FIGHTERS] validated %u independent Blazin activation bindings\n", count);
    }
    free(table); return valid;
}
int defjam_fighter_cinematic_start(void) {
    const char *path = getenv("RECOMP_FIGHTER_CINEMATIC_BANKS");
    const char *bindings = getenv("RECOMP_FIGHTER_CINEMATIC_BINDINGS");
    const char *hash = getenv("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256");
    const char *nis = getenv("RECOMP_FIGHTER_RESEARCH_CINEMATICS");
    const char *nis_hash = getenv("RECOMP_FIGHTER_RESEARCH_CINEMATICS_SHA256");
    const char *blazin = getenv("RECOMP_FIGHTER_BLAZIN_BINDINGS");
    if (!path || !*path) return (!bindings || !*bindings) && (!hash || !*hash) && (!blazin || !*blazin);
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
    uint32_t version=valid?cin_word(table+4):0,stride=version>=2?24u:20u;
    char banks_digest[65], nis_digest[65];
    if (valid) {
        hex(table + 24, banks_digest); hex(table + 56, nis_digest);
        valid = ((version==1 && !memcmp(table,"FIC1",4)) || (version==2 && !memcmp(table,"FIC2",4)) || (version==3 && !memcmp(table,"FIC3",4))) && count
            && count <= (version==3?CIN_BINDING_LIMIT:CIN_CORE_LIMIT-141) && size == 88u + count * stride
            && cin_word(table + 20) == 0 && !strcmp(banks_digest, hash) && !strcmp(nis_digest, nis_hash)
            && cin_size(path, cin_word(table + 12)) && cin_size(nis, cin_word(table + 16));
    }
    uint32_t previous = 140;
    s_caf_count=0;
    memset(s_clips, 0, sizeof s_clips);
    memset(s_full_clips,0,sizeof s_full_clips);
    for (uint32_t i = 0; valid && i < count; ++i) {
        const uint8_t *row = table + 88 + i * stride;
        uint32_t core = cin_word(row);
        int caf=version==3 && caf_behavior_key(core);
        if (core <= previous || (!caf && core >= CIN_CORE_LIMIT) || (caf && s_caf_count>=CAF_BEHAVIOR_MAX)) { valid = 0; break; }
        for (unsigned category = 0; category < 2; ++category) {
            const uint8_t *name = row + 4 + category * 8;
            if (name[0] != 'F' || name[1] != (category ? 'V' : 'I') || name[7]) valid = 0;
            for (unsigned j = 2; j < 7; ++j) if (name[j] < '0' || name[j] > '9') valid = 0;
        }
        uint32_t flags=version>=2?cin_word(row+20):0;
        if ((flags&~3u) || (caf && flags)) valid=0;
        if (valid) {
            previous=core;
            if(caf) {uint32_t index=CIN_CORE_LIMIT+s_caf_count;
                s_caf_bindings[s_caf_count].selection=core&~CAF_BEHAVIOR_BIT;s_caf_bindings[s_caf_count++].index=index;core=index;}
            memcpy(s_clips[core], row + 4, 16);s_full_clips[core]=(uint8_t)flags;
        }
    }
    if (valid) valid = cin_blazin_start(path, hash);
    if (valid) {
        s_count = count; strcpy(s_archive, path);
        fprintf(stderr, "[FIGHTERS] validated %u independent cinematic bindings\n", count);
    }
    free(table); return valid;
}
const char *defjam_fighter_cinematic_path(void) { return s_archive; }
int defjam_fighter_cinematic_proofs(void) {
    for (unsigned core=141;core<CIN_BINDING_LIMIT;++core) {
        for (unsigned role=0;role<2;++role)
            if ((s_full_clips[core]&(1u<<role)) && !defjam_fighter_film_complete(s_clips[core][role],role==0)) return 0;
        for (unsigned phase=0;core<CIN_CORE_LIMIT && phase<4;++phase)
            if ((s_full_blazin[core]&(1u<<phase)) && !defjam_fighter_film_complete(s_blazin[core][phase],0)) return 0;
    }
    return 1;
}
int defjam_fighter_cinematic_absolute(uint32_t descriptor) {
    unsigned owner=owner_record(descriptor);
    if (owner>=256 || s_owners[owner].descriptor!=descriptor) return 0;
    uint32_t core=s_owners[owner].core;
    return core<CIN_CORE_LIMIT && (s_absolute_blazin[core]&8)
        && MEM32(descriptor+0xA4)==2 && MEM32(descriptor+0xD4)==3
        && !strcmp(s_owners[owner].name,s_blazin[core][3]);
}
void defjam_fighter_cinematic_camera(uint32_t descriptor) {
    if (!defjam_fighter_cinematic_absolute(descriptor)) return;
    unsigned owner=owner_record(descriptor);
    if (!(MEM8(descriptor)&8) || !MEM8(descriptor+0x1D)
        || strcmp((const char *)XBOX_PTR(descriptor+0x61),s_owners[owner].name))
        cin_stop("owned absolute camera differs from its phase4 body request");
    memcpy((void *)XBOX_PTR(descriptor+0x1D),s_owners[owner].name,8);
    fprintf(stderr,"[FIGHTERS] owned absolute cinematic camera selected %s\n",s_owners[owner].name);
}

/* Native keeps ten shared activation descriptors. Append four participant
 * groups to both allocations, retaining its logical count during stock load.
 * The same native constructors, asynchronous loaders and destructor own all
 * resources; no live descriptor or loaded bank is copied between fighters. */
void defjam_fighter_cinematic_cache_begin(uint32_t manager) {
    if (!s_blazin_count || !defjam_fighter_research_active()) return;
    if (s_alloc_manager) cin_stop("nested cinematic cache allocation");
    if (MEM32(manager + 0x2D830)) {
        if (s_cache_manager != manager) cin_stop("unowned existing cinematic cache");
        return;
    }
    if (s_cache_manager) cin_stop("previous cinematic cache was not released");
    s_alloc_manager = manager;
    s_cache_allocations = 0;
}
uint32_t defjam_fighter_cinematic_allocation(uint32_t caller, uint32_t bytes) {
    if (!s_alloc_manager) return bytes;
    if (caller == 0x8AE86) {
        if (bytes < 4 || (bytes - 4) % 0x1AC) cin_stop("invalid native descriptor allocation");
        s_cache_count = (bytes - 4) / 0x1AC;
        if (s_cache_count < 12 || s_cache_count > 29 || s_cache_allocations)
            cin_stop("unsupported native cinematic population");
        s_cache_allocations = 1;
        return bytes + 40 * 0x1AC;
    }
    if (caller == 0x8AED9) {
        if (s_cache_allocations != 1 || bytes != s_cache_count * 0x24)
            cin_stop("cinematic request allocation differs");
        s_cache_allocations = 2;
        return bytes + 40 * 0x24;
    }
    return bytes;
}
void defjam_fighter_cinematic_cache_finish(uint32_t manager) {
    if (!s_alloc_manager) return;
    if (s_alloc_manager != manager || s_cache_allocations != 2
        || MEM32(manager + 0x2D868) != s_cache_count)
        cin_stop("incomplete cinematic cache allocation");
    s_alloc_manager = 0;
    s_cache_manager = manager;
    s_cache_descriptors = MEM32(manager + 0x2D830);
    s_cache_requests = MEM32(manager + 0x2D834);
    if (!s_cache_descriptors || !s_cache_requests) cin_stop("cinematic cache allocation failed");
    memset((void *)XBOX_PTR(s_cache_descriptors + s_cache_count * 0x1AC), 0, 40 * 0x1AC);
    memset((void *)XBOX_PTR(s_cache_requests + s_cache_count * 0x24), 0, 40 * 0x24);
    for (unsigned i = 0; i < 40; ++i)
        guest_call(sub_000A2E20, s_cache_descriptors + (s_cache_count + i) * 0x1AC, 0, NULL);
    s_cache_constructed = 40;
    fprintf(stderr, "[FIGHTERS] cinematic cache owned manager=%08X descriptors=%08X requests=%08X native=%u added=%u\n",
            manager, s_cache_descriptors, s_cache_requests, s_cache_count, s_cache_constructed);
    memset(s_cache_cores, 0, sizeof s_cache_cores);
    s_test_readied = 0;
}
static int private_descriptor(uint32_t descriptor) {
    uint32_t first = s_cache_descriptors + s_cache_count * 0x1AC;
    return s_cache_constructed && descriptor >= first && descriptor - first < 40 * 0x1AC
        && (descriptor - first) % 0x1AC == 0;
}
static unsigned cinematic_io_free(void) {
    unsigned available = 0;
    /* Native 1ACA0/1AD30 admit into 32 rows; zero means no free row.
     * The request manager does not reject that token, and 1AB20 can mistake
     * it for a consumed row whose done flag survived with a NULL buffer. */
    for (unsigned i = 0; i < 32; ++i)
        if (!MEM32(0x3319A0 + i * 0x14)) ++available;
    return available;
}
void defjam_fighter_cinematic_cache_poll(uint32_t manager) {
    if (!s_cache_constructed || s_cache_manager != manager) return;
    if (MEM32(manager + 0x2D830) != s_cache_descriptors || MEM32(manager + 0x2D834) != s_cache_requests)
        cin_stop("cinematic cache allocation changed during playback");
    for (unsigned slot = 0; slot < 4; ++slot) {
        uint32_t core = MEM32(0x3B90B8 + slot * 4);
        if (core >= CIN_CORE_LIMIT || !s_blazin[core][0][0]) continue;
        if (s_cache_cores[slot] && s_cache_cores[slot] != core)
            cin_stop("cinematic participant changed without cache teardown");
        s_cache_cores[slot] = core;
        /* Explicit harness-only setup: fill momentum through the native rules.
         * Activation still requires controller input; no pack can request this. */
        const char *test_ready = getenv("RECOMP_FIGHTER_TEST_READY_BLAZIN");
        const char *observations = getenv("RECOMP_TEST_OBSERVATIONS");
        if (defjam_fighter_research_active() && test_ready && !strcmp(test_ready, "1")
            && observations && !strcmp(observations, "1") && MEM32(0x3B8F30) == 1
            && !(s_test_readied & (1u << slot))) {
            uint32_t actor = 0x3B92E0 + slot * 0x12E8;
            if (MEM32(actor + 0x28) != UINT32_MAX && MEM32(actor + 0x2C) == core
                && !(MEM8(actor + 0x933) & 2) && !(MEM8(actor + 0x93E) & 3)) {
                uint32_t args[2] = { actor, 0x447A0000 }; /* IEEE float 1000. */
                guest_call(sub_001A5190, 0, 2, args);
                s_test_readied |= 1u << slot;
                fprintf(stderr, "[FIGHTERS] test momentum readied slot %u core %u\n", slot, core);
            }
        }
        for (unsigned shot = 0; shot < 10; ++shot) {
            uint32_t index = s_cache_count + slot * 10 + shot;
            uint32_t descriptor = s_cache_descriptors + index * 0x1AC;
            uint32_t request = s_cache_requests + index * 0x24;
            uint32_t state = MEM32(request + 0x14);
            if (!state) {
                /* Admit one owned body/camera pair at a time. The original
                 * manager still polls first, so retail requests can finish
                 * while an owned pair waits for capacity. */
                if (cinematic_io_free() < 2) return;
                uint32_t phase = shot == 0 ? 0 : shot < 5 ? 1 : shot < 9 ? 2 : 3;
                MEM32(request) = 4; MEM32(request + 4) = slot; MEM32(request + 8) = UINT32_MAX;
                MEM32(request + 12) = 2; MEM32(request + 16) = 1; MEM32(request + 0x1C) = phase;
                MEM32(descriptor + 0xD8) = shot == 0 || shot == 9 ? 0 : shot < 5 ? shot - 1 : shot - 5;
                uint32_t args[2] = { descriptor, request }, previous = MEM32(manager + 0x2D854);
                guest_call(sub_00087AF0, manager, 2, args);
                MEM32(manager + 0x2D854) = previous;
                MEM32(request + 0x14) = 1;
            }
            if (MEM32(request + 0x14) != 1) continue;
            unsigned needed = MEM32(descriptor + 0x5C) == UINT32_MAX ? 2u
                : (MEM8(descriptor) & 8) && MEM32(descriptor + 0x18) == UINT32_MAX ? 1u : 0u;
            if (cinematic_io_free() < needed) return;
            if (guest_call(sub_000A3E80, descriptor, 0, NULL) & 0xFF) {
                uint32_t zero = 0;
                guest_call(sub_000A3130, descriptor, 1, &zero);
                MEM32(request + 0x14) = 2;
            } else return; /* Poll this pair again before admitting another. */
        }
    }
}
int defjam_fighter_cinematic_cache_ready(uint32_t manager) {
    if (!s_cache_constructed || s_cache_manager != manager) return 1;
    defjam_fighter_cinematic_cache_poll(manager);
    for (unsigned slot = 0; slot < 4; ++slot) {
        uint32_t core = MEM32(0x3B90B8 + slot * 4);
        if (core >= CIN_CORE_LIMIT || !s_blazin[core][0][0]) continue;
        for (unsigned shot = 0; shot < 10; ++shot)
            if (MEM32(s_cache_requests + (s_cache_count + slot * 10 + shot) * 0x24 + 0x14) != 2) return 0;
    }
    return 1;
}
uint32_t defjam_fighter_cinematic_cache_index(uint32_t manager, uint32_t native) {
    if (!s_cache_constructed || s_cache_manager != manager) return native;
    uint32_t slot = MEM32(manager + 0x2D844), base = MEM32(manager + 0x2D838);
    if (slot >= 4) cin_stop("invalid activation participant");
    uint32_t core = MEM32(0x3B90B8 + slot * 4);
    if (core >= CIN_CORE_LIMIT || !s_blazin[core][0][0]) return native;
    if (s_cache_cores[slot] != core || native < base || native - base >= 10)
        cin_stop("activation selection differs from its owned cache");
    uint32_t index = s_cache_count + slot * 10 + native - base;
    if (MEM32(s_cache_requests + index * 0x24 + 0x14) != 2)
        cin_stop("activation selected before its private resources were ready");
    const char *observations = getenv("RECOMP_TEST_OBSERVATIONS");
    if (observations && !strcmp(observations, "1")) {
        /* Playback selection, unlike the earlier asynchronous preload notice.
         * Input probes can wait for this participant's final activation shot. */
        uint32_t shot = native - base;
        unsigned phase = shot == 0 ? 0 : shot <= 4 ? 1 : shot <= 8 ? 2 : 3;
        char event[48];
        snprintf(event, sizeof event, "fighter-blazin-playback:%u:%u", slot, phase);
        xbox_NoteAnchorEvent(event);
    }
    return index;
}
void defjam_fighter_cinematic_cache_release(uint32_t manager) {
    for (unsigned i=0;i<256;++i) if (s_owners[i].manager==manager) memset(&s_owners[i],0,sizeof s_owners[i]);
    if (!s_cache_constructed || s_cache_manager != manager) return;
    if (MEM32(manager + 0x2D868) != s_cache_count) cin_stop("cinematic cleanup count changed");
    fprintf(stderr, "[FIGHTERS] cinematic cache returning to native destructor manager=%08X descriptors=%08X requests=%08X native=%u added=%u\n",
            manager, s_cache_descriptors, s_cache_requests, s_cache_count, s_cache_constructed);
    MEM32(manager + 0x2D868) = s_cache_count + s_cache_constructed;
    s_cache_constructed = s_cache_manager = s_cache_descriptors = s_cache_requests = 0;
}

/* 87AF0's request supplies the actual visual-table participant. Its camera
 * selector is a different field; descriptor allocation order is irrelevant. */
uint64_t defjam_fighter_cinematic_enter(uint32_t manager, uint32_t descriptor, uint32_t request) {
    unsigned owner=owner_record(descriptor);
    if (owner<256 && s_owners[owner].descriptor) memset(&s_owners[owner],0,sizeof s_owners[owner]);
    uint64_t previous = s_context;
    s_context = 0;
    if (!s_count || !defjam_fighter_research_active())
        return previous;
    int blazin = MEM32(request) == 4 && MEM32(request + 12) == 2;
    if (blazin && !private_descriptor(descriptor)) return previous;
    if (!blazin && (MEM32(request) != 1 || MEM32(request + 12) > 1)) return previous;
    uint32_t slot = MEM32(request + 4);
    if (slot >= 4) return previous;
    uint32_t core = MEM32(0x3B90B8 + slot * 4);
    uint32_t actual_core=core;
    if(!blazin) {uint32_t binding=caf_behavior_index(s_caf_bindings,s_caf_count,slot);if(binding!=UINT32_MAX)core=binding;}
    if (core >= CIN_BINDING_LIMIT || !s_clips[core][0][0]) return previous;
    if (blazin && (core >= CIN_CORE_LIMIT || !s_blazin_count || !s_blazin[core][0][0])) return previous;
    uint32_t config = MEM32(manager + 0x2FF5C);
    if (!config || MEM32(config + 0xA8 + slot * 4) != actual_core + 1)
        cin_stop("participant core differs from native cinematic configuration");
    if (!blazin && (MEM32(manager + 0x2B9EC) & 0x02000000u))
        cin_stop("owned simple sequence cannot use the two-actor cinematic path");
    s_context = ((uint64_t)descriptor << 32) | core | (blazin ? 0x80000000u : 0u);
    if (owner>=256) cin_stop("cinematic descriptor ownership population exceeds bound");
    s_owners[owner].descriptor=descriptor;s_owners[owner].manager=manager;
    s_owners[owner].slot=slot;s_owners[owner].core=core;
    return previous;
}
void defjam_fighter_cinematic_leave(uint64_t previous, uint32_t request) {
    if (s_context && MEM32(request + 0x20) != 1)
        cin_stop("owned simple sequence has unexpected actor ownership");
    s_context = previous;
}
void defjam_fighter_cinematic_name(uint32_t descriptor) {
    if (!s_context || (uint32_t)(s_context >> 32) != descriptor || !defjam_fighter_research_active()) return;
    char label[14]; /* Enough for any uint32; the admitted native token is eight bytes. */
    int length=snprintf(label, sizeof label, "fm%c%05u", ((uint32_t)s_context & 0x80000000u) ? 'b' : 'c',
                        (uint32_t)s_context & 0x7FFFFFFFu);
    if (length!=8) {cin_stop("owned cinematic descriptor token exceeds native width");return;}
    memcpy((void *)XBOX_PTR(descriptor + 0xA8), label, 9);
}
void defjam_fighter_cinematic_selected(uint32_t descriptor, uint32_t name) {
    if (!s_count || !defjam_fighter_research_active()) return;
    const uint8_t *label = (const uint8_t *)XBOX_PTR(descriptor + 0xA8);
    if (memcmp(label, "fm", 2) || (label[2] != 'c' && label[2] != 'b') || label[8]) return;
    uint32_t core = 0;
    for (unsigned i = 3; i < 8; ++i) {
        if (label[i] < '0' || label[i] > '9') return;
        core = core * 10 + label[i] - '0';
    }
    if (core >= CIN_BINDING_LIMIT || !s_clips[core][0][0]) return;
    uint32_t category = MEM32(descriptor + 0xA4);
    if (label[2] == 'b') {
        if(core>=CIN_CORE_LIMIT)cin_stop("CAF cinematic binding cannot supply Blazin choreography");
        uint32_t phase = MEM32(descriptor + 0xD4);
        if (!s_blazin_count || !s_blazin[core][0][0] || MEM32(descriptor + 0x19C) != 4
            || category != 2 || phase >= 4 || MEM32(descriptor + 0xD0) != 4 || name != descriptor + 0x61)
            cin_stop("owned Blazin activation differs from its four-shot contract");
        /* Persistent body name is used by the asynchronous loader. The optional
         * absolute camera is finalized after native A3B60's venue-name write. */
        memcpy((void *)XBOX_PTR(name), s_blazin[core][phase], 7);
        unsigned owner=owner_record(descriptor);
        if (owner>=256 || s_owners[owner].descriptor!=descriptor) cin_stop("missing cinematic request owner");
        memcpy(s_owners[owner].name,s_blazin[core][phase],8);
        fprintf(stderr, "[FIGHTERS] Blazin core %u phase %u selected %s\n", core, phase, s_blazin[core][phase]);
        char event[40];
        snprintf(event, sizeof event, "fighter-blazin:%s", s_blazin[core][phase]);
        xbox_NoteAnchorEvent(event);
        return;
    }
    if (MEM32(descriptor + 0x19C) != 1 || category > 1
        || memcmp((const void *)XBOX_PTR(name), s_clips[core][category], 8))
        cin_stop("native XML selected a different owned cinematic");
    fprintf(stderr, "[FIGHTERS] cinematic core %u category %u selected %s\n", core, category, s_clips[core][category]);
    unsigned owner=owner_record(descriptor);
    if (owner>=256 || s_owners[owner].descriptor!=descriptor) cin_stop("missing cinematic request owner");
    memcpy(s_owners[owner].name,s_clips[core][category],8);
    char event[40];
    snprintf(event, sizeof event, "fighter-cinematic:%s", s_clips[core][category]);
    xbox_NoteAnchorEvent(event);
}
void defjam_fighter_cinematic_bind(uint32_t descriptor) {
    unsigned owner=owner_record(descriptor);
    if (owner>=256 || s_owners[owner].descriptor!=descriptor || !s_owners[owner].name[0]
        || !defjam_fighter_film_known(s_owners[owner].name)) return;
    uint32_t manager=s_owners[owner].manager,slot=s_owners[owner].slot,core=s_owners[owner].core;
    uint32_t entry=MEM32(descriptor+0x90),config=MEM32(manager+0x2FF5C);
    if (slot>=4 || !entry || MEM32(descriptor+0x94)!=1 || MEM32(0x3B90B8+4*slot)!=core
        || !config || MEM32(config+0xA8+4*slot)!=core+1
        || memcmp((const void *)XBOX_PTR(entry),s_owners[owner].name,strlen(s_owners[owner].name)+1))
        cin_stop("full cinematic actor differs from its immutable request owner");
    uint32_t visual=MEM32(manager+0x2B9C0+4*slot);
    if (!visual || MEM32(entry+0x44)!=visual || !defjam_fighter_film_bind(s_owners[owner].name,entry,visual,descriptor))
        cin_stop("full cinematic banks or actual output context differ from their proofs");
    fprintf(stderr,"[FIGHTERS] full cinematic context verified name=%s slot=%u core=%u visual=%08X\n",
            s_owners[owner].name,slot,core,visual);
}
