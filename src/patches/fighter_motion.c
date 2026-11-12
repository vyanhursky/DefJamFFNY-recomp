/* Owned descriptors retain full-width core identity and borrow one validated
 * native motion resource generation. Retail descriptors are never overwritten.
 * Contracts derived from the player's own executable; see the motion ABI brief.
 */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_motion.h"
#include "fighter_fatal.h"
#include "fighter_runtime.h"
#include "hooks/guest_call.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>
#include <math.h>

#define ORIGINAL_CORES 141u
#define MAX_CORES 16384u
#define MAX_MOTION (64u * 1024u * 1024u)
#define MAX_BINDINGS (56u + 296u * (MAX_CORES - ORIGINAL_CORES))
typedef struct MotionCore { uint32_t parameters, actions, bank; uint64_t pending[3]; } MotionCore;
static MotionCore s_cores[MAX_CORES - ORIGINAL_CORES];
static uint32_t s_count, s_size, s_source, s_generation;
static uint8_t s_digest[32];
static char s_path[2048];
extern void sub_001A3AD0(void);
extern void sub_001A3630(void);
extern void sub_001C60D0(void);
extern void sub_000444E0(void);
extern void sub_00011520(void);
extern void sub_0003E170_gen(void);

static void motion_stop(const char *message) { defjam_fighter_fatal("motion", message); }
static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static uint32_t half(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 8; }
static int ordinary_action(uint32_t id) { return id >= 1 && id < 125 && !(id >= 31 && id <= 41); }
static uint32_t action_owner(const uint8_t *pair, uint32_t local, uint32_t *lower) {
    uint32_t previous = 1;
    *lower = 0;
    for (uint32_t i = 2; i <= 125; ++i) {
        uint32_t boundary = i == 125 ? 1000 : half(pair + 82 + i * 6);
        if (local < boundary) return previous;
        if (boundary > *lower || (boundary == *lower && half(pair + 80 + i * 6) != 65535)) {
            *lower = boundary; previous = i;
        }
    }
    return 130;
}
/* Reconstruct each edited action from its original family. Boundaries and
 * shared tables remain unchanged; arbitrary native records are not admitted. */
static int selected_pair(const uint8_t *pair, const uint8_t *original, const uint8_t *proof,
                         uint32_t moves, uint32_t parameters, const uint8_t *slots) {
    uint32_t count = word(proof), first[130], lengths[130] = {0};
    unsigned changed = 0;
    uint8_t expected[80];
    memcpy(expected, original, sizeof expected);
    if (slots) for (unsigned slot = 0; slot < 4; ++slot) {
        uint32_t choice = word(slots + slot * 4);
        if (choice == UINT32_MAX) continue;
        if (choice >= 82) return 0;
        /* Native 1A3AD0: WPAR fields +D4..E0, MSB-first payload bits
         * 448..479. Reconstruct only the four declared bytes. */
        expected[8 + 56 + slot] = (uint8_t)choice;
    }
    if (count >= 1000 || memcmp(pair, expected, sizeof expected)) return 0;
    for (unsigned i = 0; i < 130; ++i) first[i] = UINT32_MAX;
    for (uint32_t local = 0; local < count; ++local) {
        uint32_t lower, owner = action_owner(original, local, &lower);
        if (owner >= 130 || half(original + 84 + owner * 6) + local - lower >= parameters) return 0;
        if (!lengths[owner]) first[owner] = local;
        ++lengths[owner];
    }
    for (uint32_t target = 0; target < 130; ++target) {
        uint32_t source = half(proof + 4 + target * 2);
        const uint8_t *actual = pair + 80 + target * 6, *before = original + 80 + target * 6;
        if (source == 65535) {
            if (memcmp(actual, before, 6)) return 0;
            continue;
        }
        if (!count || !ordinary_action(target) || !ordinary_action(source) || target == source) return 0;
        const uint8_t *chosen = original + 80 + source * 6;
        uint32_t old = half(before), value = half(chosen);
        if (old == 65535 || value == 65535 || (old & 0xF000) != (value & 0xF000)
            || (value & 0xFFF) >= moves || !lengths[target] || lengths[target] > 2
            || lengths[target] != lengths[source] || first[target] != half(before + 2)
            || first[source] != half(chosen + 2) || half(actual) != value
            || half(actual + 2) != half(before + 2) || half(actual + 4) != half(chosen + 4)) return 0;
        for (unsigned other = 1; other < 130; ++other) {
            uint32_t start = half(original + 82 + other * 6);
            if (other != target && half(original + 80 + other * 6) != 65535
                && start >= first[target] && start - first[target] < lengths[target]) return 0;
        }
        ++changed;
    }
    if ((!changed) != (!count)) return 0;
    for (uint32_t local = 0; local < count; ++local) {
        uint32_t lower, owner = action_owner(original, local, &lower), next_lower;
        uint32_t next = action_owner(pair, local, &next_lower), source = half(proof + 4 + owner * 2);
        if (source == 65535) source = owner;
        if (next != owner || next_lower != lower
            || half(pair + 84 + next * 6) + local - lower
                != half(original + 84 + source * 6) + local - lower) return 0;
    }
    return 1;
}
static int shared_table(const uint8_t *p, uint32_t size, unsigned kind) {
    if (kind == 0) {
        if (size < 12) return 0;
        uint32_t count = word(p + 4), groups = word(p + 8);
        if (word(p) != 32 || !count || count > 65535 || !groups || groups > 4096
            || size != 12u + groups * 4u + count * 32u) return 0;
        uint64_t total = 0;
        for (uint32_t i = 0; i < groups; ++i) total += word(p + 12 + i * 4);
        return total <= count;
    }
    if (kind == 1) {
        if (size < 8) return 0;
        uint32_t count = word(p + 4);
        if (word(p) != 39 || !count || count > 1000000) return 0;
        uint32_t end = 8 + count * 39;
        if (size != ((end + 3u) & ~3u)) return 0;
        for (; end < size; ++end) if (p[end]) return 0;
        return 1;
    }
    if (size < 4) return 0;
    uint32_t count = word(p), pool = 4 + count * 2;
    if (!count || count > 65535 || pool >= size) return 0;
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t offset = p[4 + i * 2] | (uint32_t)p[5 + i * 2] << 8;
        uint32_t at = pool + offset, length = 0;
        if (at >= size || (offset && p[at - 1])) return 0;
        while (at < size && p[at] && length <= 1024) {
            if (p[at] < 32 || p[at] >= 127) return 0;
            ++at; ++length;
        }
        if (at == size || length > 1024) return 0;
    }
    return 1;
}
static uint8_t *read_file(const char *path, size_t limit, size_t *size) {
    FILE *file;
#if defined(_WIN32)
    wchar_t wide[2048];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048)) return NULL;
    file = _wfopen(wide, L"rb");
#else
    file = fopen(path, "rb");
#endif
    if (!file) return NULL;
    uint8_t *data = (uint8_t *)malloc(limit + 1);
    if (!data) { fclose(file); return NULL; }
    *size = fread(data, 1, limit + 1, file);
    int good = !ferror(file) && *size <= limit;
    if (fclose(file)) good = 0;
    if (!good) { free(data); return NULL; }
    return data;
}

int defjam_fighter_motion_start(void) {
    const char *path = getenv("RECOMP_FIGHTER_MOTION");
    const char *bindings = getenv("RECOMP_FIGHTER_MOTION_BINDINGS");
    const char *hash = getenv("RECOMP_FIGHTER_MOTION_SHA256");
    if (!path || !*path) return (!bindings || !*bindings) && (!hash || !*hash);
    if (!defjam_fighter_research_active() || !bindings || !*bindings || s_count || strlen(path) >= sizeof(s_path)
        || !mod_file_matches(path, hash)) return 0;
    size_t size = 0, bytes = 0;
    uint8_t *table = read_file(bindings, MAX_BINDINGS, &size);
    uint8_t *data = read_file(path, MAX_MOTION, &bytes);
    uint32_t stride = 0;
    if (table && size >= 56) {
        if (!memcmp(table, "FMC1", 4) && word(table + 4) == 1) stride = 16;
        if (!memcmp(table, "FMC2", 4) && word(table + 4) == 2) stride = 280;
        if (!memcmp(table, "FMC3", 4) && word(table + 4) == 3) stride = 296;
    }
    int valid = table && data && size >= 56
        && stride
        && word(table + 8) == ORIGINAL_CORES
        && word(table + 12) && word(table + 12) <= MAX_CORES - ORIGINAL_CORES
        && size == 56u + stride * word(table + 12) && bytes == word(table + 16) && !word(table + 20);
    if (!valid) { free(table); free(data); return 0; }
    uint8_t digest[32]; char encoded[65];
    sha256(data, bytes, digest); hex(digest, encoded);
    valid = !memcmp(digest, table + 24, 32) && !strcmp(encoded, hash);
    /* Establish every native chunk before publishing any sidecar entry. */
    uint32_t cursor = 0, original[ORIGINAL_CORES], moves = 0, parameters = 0;
    static const char *tags[6] = {"WAZA", "FZUI", "NAME", "WAZA", "FZUI", "NAME"};
    for (unsigned i = 0; valid && i < 6; ++i) {
        if (cursor > bytes || bytes - cursor < 8 || memcmp(data + cursor, tags[i], 4)
            || word(data + cursor + 4) > bytes - cursor - 8) { valid = 0; break; }
        uint32_t length = word(data + cursor + 4);
        if (!shared_table(data + cursor + 8, length, i % 3)) { valid = 0; break; }
        if (i == 0) moves = word(data + cursor + 12);
        if (i == 1) parameters = word(data + cursor + 12);
        cursor += 8 + length;
    }
    uint32_t count = word(table + 12);
    for (uint32_t i = 0; valid && i < ORIGINAL_CORES + count; ++i) {
        if (cursor > bytes || bytes - cursor < 860 || memcmp(data + cursor, "WPAR", 4)
            || word(data + cursor + 4) != 64 || memcmp(data + cursor + 72, "WWAZ", 4)
            || word(data + cursor + 76) != 780) { valid = 0; break; }
        if (i < ORIGINAL_CORES) original[i] = cursor;
        else {
            const uint8_t *row = table + 56 + (i - ORIGINAL_CORES) * stride;
            uint32_t bank = word(row + 12);
            if (word(row) != i || word(row + 4) != cursor + 8 || word(row + 8) != cursor + 80
                || bank < 3 || bank > ORIGINAL_CORES) {
                valid = 0; break;
            }
            if (stride == 16 ? memcmp(data + cursor, data + original[bank - 1], 860)
                : !selected_pair(data + cursor, data + original[bank - 1], row + 16, moves, parameters,
                                 stride == 296 ? row + 280 : NULL)) {
                valid = 0; break;
            }
            MotionCore *core = &s_cores[i - ORIGINAL_CORES];
            *core = (MotionCore){cursor + 8, cursor + 80, bank, {0, 0, 0}};
            if (stride >= 280) for (unsigned action = 0; action < 130; ++action)
                if (half(row + 20 + action * 2) != 65535) core->pending[action / 64] |= 1ull << (action % 64);
        }
        cursor += 860;
    }
    valid = valid && cursor == bytes;
    if (valid) {
        s_count = count; s_size = (uint32_t)bytes;
        memcpy(s_digest, digest, 32); strcpy(s_path, path);
        fprintf(stderr, "[FIGHTERS] validated %u owned motion cores\n", count);
    }
    free(table); free(data); return valid;
}

const char *defjam_fighter_motion_path(void) { return s_path; }
/* D6EE0 formats inherited AI names before C9110 loads them. K is the motion
 * core; 20270 derives ordinary V=K+1+1000*variant. Correct the K fallback and
 * unvaried V=K+1 case, retaining the native mode/created-profile naming rules.
 * Other configured identities stay intact until their adapter is verified.
 * Explicit authored AI bindings in C9110 still take precedence. */
void defjam_fighter_motion_ai_profiles(uint32_t output, uint32_t input) {
    if (!defjam_fighter_research_active() || !s_count) return;
    for (uint32_t slot = 0; slot < 4; ++slot) {
        uint32_t core = MEM32(input + 0x40 + slot * 4);
        uint32_t identity = MEM32(input + 0x200 + slot * 4);
        if ((int32_t)core < 0 || core < ORIGINAL_CORES || (identity && identity != core + 1)) continue;
        if (core - ORIGINAL_CORES >= s_count) motion_stop("unknown AI template core");
        uint32_t donor = s_cores[core - ORIGINAL_CORES].bank;
        char name[32] = {0};
        if (identity && donor >= 87 && donor <= 141) strcpy(name, "char0001");
        else snprintf(name, sizeof name, identity && MEM32(input) == 2 ? "cha%05u" : "char%04u", donor);
        memcpy((void *)XBOX_PTR(output + 0x24 + slot * 32), name, sizeof name);
        fprintf(stderr, "[FIGHTERS] inherited AI core %u slot %u profile %s\n", core, slot, name);
    }
}
uint32_t defjam_fighter_motion_ai_capture(uint32_t config, char expected[128]) {
    uint32_t mask = 0;
    if (!defjam_fighter_research_active() || !s_count) return 0;
    for (uint32_t slot = 0; slot < 4; ++slot) {
        uint32_t core = MEM32(0x3B90B8 + slot * 4);
        if (core < ORIGINAL_CORES || core - ORIGINAL_CORES >= s_count) continue;
        const char *name = (const char *)XBOX_PTR(config + 0x24 + slot * 32);
        if (!name[0] || !memchr(name, 0, 32)) motion_stop("owned AI profile is empty or unterminated");
        memcpy(expected + slot * 32, name, 32); mask |= 1u << slot;
    }
    return mask;
}
void defjam_fighter_motion_ai_verify(uint32_t config, uint32_t mask, const char expected[128]) {
    for (uint32_t slot = 0; slot < 4; ++slot) if (mask & (1u << slot)) {
        const char *name = (const char *)XBOX_PTR(config + 0x24 + slot * 32);
        if (memcmp(name, expected + slot * 32, 32)) motion_stop("owned AI profile silently fell back");
        fprintf(stderr, "[FIGHTERS] AI profile retained slot %u core %u profile %s\n",
                slot, MEM32(0x3B90B8 + slot * 4), name);
    }
}
int defjam_fighter_motion_audio(uint32_t input) {
    if (!defjam_fighter_research_active() || !s_count || MEM8(0x340540)) return 0;
    uint32_t indices[4]; int changed = 0;
    for (uint32_t slot = 0; slot < 4; ++slot) {
        uint32_t index = MEM32(input + 0x20 + slot * 0x18);
        indices[slot] = index;
        if (index == UINT32_MAX || index <= ORIGINAL_CORES) continue;
        if (index - ORIGINAL_CORES - 1 >= s_count) motion_stop("unknown audio template core");
        indices[slot] = s_cores[index - ORIGINAL_CORES - 1].bank;
        changed = 1;
    }
    if (!changed) return 0;
    /* Audio setup precedes motion-resource registration. Its caller owns an
     * 0x84-byte stack value, read synchronously, with four one-based core keys.
     * Copy that value onto a nested guest frame; neither actors nor the caller's
     * source are rewritten. Native audio rows retain their own template keys. */
    uint32_t stack = g_esp;
    if (stack < 0x1000 + 0x90) motion_stop("invalid audio adapter stack");
    g_esp -= 0x90;
    uint32_t copy = g_esp;
    memcpy((void *)XBOX_PTR(copy), (const void *)XBOX_PTR(input), 0x84);
    for (uint32_t slot = 0; slot < 4; ++slot) MEM32(copy + 0x20 + slot * 0x18) = indices[slot];
    g_eax = guest_call(sub_0003E170_gen, g_ecx, 1, &copy);
    g_esp = stack + 4;
    fprintf(stderr, "[FIGHTERS] inherited audio templates %u/%u/%u/%u\n",
            indices[0], indices[1], indices[2], indices[3]);
    return 1;
}
void defjam_fighter_motion_register(uint32_t source) {
    if (!s_count) return;
    if (s_source) motion_stop("previous motion source was not released");
    if (!source || s_size > UINT32_MAX - source) motion_stop("invalid source range");
    uint8_t digest[32]; sha256((const void *)XBOX_PTR(source), s_size, digest);
    if (memcmp(digest, s_digest, 32)) motion_stop("loaded resource differs from validated receipt");
    s_source = source; ++s_generation;
    fprintf(stderr, "[FIGHTERS] motion generation %u registered: core %u..%u source=%08X\n",
            s_generation, ORIGINAL_CORES, ORIGINAL_CORES + s_count - 1, source);
}
void defjam_fighter_motion_release(uint32_t owner) {
    if (s_source && MEM32(owner) == s_source) {
        fprintf(stderr, "[FIGHTERS] motion generation %u invalidated before source release owner=%08X source=%08X\n",
                s_generation, owner, s_source);
        s_source = 0;
    }
}
static const MotionCore *custom(uint32_t core) {
    if (!defjam_fighter_research_active() || core < ORIGINAL_CORES) return NULL;
    if (core - ORIGINAL_CORES >= s_count || !s_source) motion_stop("unregistered or expired core");
    return &s_cores[core - ORIGINAL_CORES];
}
uint32_t defjam_fighter_motion_bank(uint32_t bank) {
    if (!bank) return bank;
    const MotionCore *row = custom(bank - 1);
    if (row) fprintf(stderr, "[FIGHTERS] core %u uses inherited bank %u\n", bank - 1, row->bank);
    return row ? row->bank : bank;
}
int defjam_fighter_motion_parameters(uint32_t actor) {
    const MotionCore *row = custom(MEM32(actor + 0x2C));
    if (!row) return 0;
    uint32_t slot = MEM32(actor + 0x28), sum = 0;
    if (slot >= 4) motion_stop("invalid parameter participant");
    uint32_t args[2] = {actor + 0xAE4, s_source + row->parameters};
    guest_call(sub_001A3AD0, g_ecx, 2, args);
    for (uint32_t i = 0; i < 7; ++i) sum += MEM32(0x3B9128 + slot * 28 + i * 4);
    MEM32(g_esp + 4) = sum;
    if (sum) for (uint32_t i = 0; i < 7; ++i) MEM32(actor + 0xB34 + i * 4) = MEM32(0x3B9128 + slot * 28 + i * 4);
    g_esp += 4; return 1;
}
static uint32_t action(const MotionCore *row, uint32_t id) {
    if (id >= 130) motion_stop("action exceeds core table");
    return s_source + row->actions + id * 6;
}
static void decode_move(uint32_t output, uint32_t partition, uint32_t id) {
    uint32_t base = partition ? 0x3B8610 : 0x3B85D8;
    if (MEM32(base + 4) != 32 || id >= MEM32(base + 8)) motion_stop("move exceeds shared table");
    uint32_t args[2] = {output + 0xF6C, MEM32(base + 20) + id * 32};
    guest_call(sub_001A3630, g_ecx, 2, args);
}
int defjam_fighter_motion_state(uint32_t output, uint32_t context, uint32_t id) {
    const MotionCore *row = custom(MEM32(context + 0x2C));
    if (!row) return 0;
    if (id > INT32_MAX) motion_stop("negative motion identifier");
    int special = (id >= 31 && id <= 34) || (id >= 38 && id <= 41);
    MEM32(output + 0xFAC) = output; MEM32(output + 0xFB0) = context; MEM32(output + 0xF50) = id;
    MEM32(output + 0xF58) = guest_call(sub_001C60D0, g_ecx, 1, &output);
    MEM8(output + 0xF68) = MEM8(output + 0xF69) = MEM8(output + 0xF6A) = 0;
    MEM32(output + 0xFB4) = 0;
    if (special || id >= 10000) {
        MEM32(output + 0xF54) = UINT32_MAX;
        MEM32(output + 0x1020) = MEM32(output + 0xF5C) = id;
        uint32_t ordinal = id - 10000;
        if (special) {
            uint32_t value = MEM32(output + 0xBB8 + (id - (id >= 38 ? 38 : 31)) * 4);
            if (value > UINT32_MAX - 142) motion_stop("special move overflow");
            ordinal = value + 142;
        }
        decode_move(output, 1, ordinal);
        MEM8(output + 0xF68) = special ? !!(MEM16(action(row, id)) & 0x8000) : !!MEM8(output + 0xF71);
    } else {
        uint32_t at = action(row, id), value = MEM16(at), slot = MEM32(output + 0x28);
        if (value == 0xFFFF || slot >= 4) motion_stop("absent action or invalid output participant");
        MEM32(output + 0xF54) = MEM32(output + 0x1020) = MEM32(output + 0xF5C) = value & 0xFFF;
        MEM8(output + 0xF68) = !!(value & 0x8000);
        decode_move(output, 0, value & 0xFFF);
        MEM32(output + 0xFB4) = MEM16(at + 2) + slot * 1000;
        MotionCore *observed = &s_cores[row - s_cores];
        uint64_t bit = 1ull << (id % 64);
        if ((observed->pending[id / 64] & bit) && MEM32(0x3B8F30) == 1) {
            observed->pending[id / 64] &= ~bit;
            fprintf(stderr, "[FIGHTERS] combat selected action core %u slot %u action %u move %u motion %u actor 0x%08X\n",
                    MEM32(context + 0x2C), slot, id, value & 0xFFF, MEM16(at + 2), output);
        }
    }
    MEM32(output + 0x3C0) = (uint32_t)(int32_t)(int16_t)MEM16(output + 0xF6C);
    MEM8(output + 0x926) = (uint8_t)((MEM8(output + 0x926) & 0xFE) | special);
    g_esp += 4; return 1;
}
int defjam_fighter_motion_present(uint32_t context, uint32_t id) {
    /* Preserve sample0's no-dereference contract, even for null context. */
    if (!id) return 0;
    const MotionCore *row = custom(MEM32(context + 0x2C));
    if (!row) return 0;
    g_eax = MEM16(action(row, id)) != 0xFFFF; g_esp += 4; return 1;
}
int defjam_fighter_motion_frame(uint32_t local) {
    if (!defjam_fighter_research_active()) return 0;
    if (local >= 4000) motion_stop("invalid motion participant encoding");
    uint32_t actor = 0x3B92E0 + (local / 1000) * 0x12E8;
    const MotionCore *row = custom(MEM32(actor + 0x2C));
    if (!row) return 0;
    local %= 1000;
    uint32_t previous = 1, lower = 0, result = 0;
    for (uint32_t i = 2; i <= 125; ++i) {
        uint32_t boundary = i == 125 ? 1000 : MEM16(action(row, i) + 2);
        if (local < boundary) {
            uint32_t delta = local - lower;
            result = MEM16(action(row, previous) + 4) + delta;
            if (delta >= 2 && MEM32(actor + 0x30) == 0x41)
                result = (uint32_t)(int32_t)(int16_t)MEM16(actor + 0xFA6)
                    - (((MEM8(actor + 0x91A) & 4) | 8) >> 2) + delta;
            break;
        }
        if (boundary > lower) { lower = boundary; previous = i; }
        else if (boundary == lower && MEM16(action(row, i)) != 0xFFFF) previous = i;
    }
    if (result >= MEM32(0x3B85F8)) motion_stop("frame exceeds primary parameter table");
    g_eax = result; g_esp += 4; return 1;
}
int defjam_fighter_motion_scale(void) {
    if (!defjam_fighter_research_active()) return 0;
    int any = 0, occupied[4] = {0}, high = 0, normal = 0, low = 0;
    float values[4] = {0};
    double h = MEMF(0x2C9348), n = MEMF(0x289478), l = MEMF(0x2A2C38), epsilon = MEMF(0x292378);
    for (uint32_t slot = 0; slot < 4; ++slot) {
        uint32_t actor = 0x3B92E0 + slot * 0x12E8;
        if (MEM32(actor + 0x28) == UINT32_MAX) continue;
        uint32_t core = MEM32(actor + 0x2C);
        const MotionCore *row = custom(core);
        if (row) { any = 1; core = row->bank - 1; }
        occupied[slot] = 1; values[slot] = MEMF(0x2F0088 + core * 4);
        high += fabs((double)values[slot] - h) < epsilon;
        normal += fabs((double)values[slot] - n) < epsilon;
        low += fabs((double)values[slot] - l) < epsilon;
    }
    if (!any) return 0;
    int adjusted = high && !normal && low;
    int raw = (high && normal) || (!high && normal && low) || (!high && !normal && !low);
    for (uint32_t slot = 0; slot < 4; ++slot) if (occupied[slot]) {
        double value = raw || adjusted ? values[slot] : 1.0;
        if (adjusted) {
            if (fabs(value - l) < epsilon) value = (float)0.95;
            if (fabs(value - h) < epsilon) value = 1.0;
        }
        uint32_t args[4] = {slot, 0x3F800000, 0, 0};
        guest_call(sub_000444E0, g_ecx, 2, args);
        args[0] = adjusted ? 0x2C9308 : raw ? 0x2C9324 : 0x2C92E8;
        args[1] = slot + 1; memcpy(args + 2, &value, 8);
        guest_call(sub_00011520, g_ecx, 4, args);
    }
    g_esp += 4; return 1;
}

/* 1A8180 assumes every core>=86 is profile-owned. Added cores have independent
 * WPAR choices and must not inherit that legacy ordinal classification. */
int defjam_fighter_motion_blazin_mask(void) {
    if (!defjam_fighter_research_active() || !s_count) return 0;
    int any = 0, active[4] = {0}, profile[4] = {0};
    uint32_t choices[4][4] = {{0}};
    uint8_t mask[164] = {0};
    for (uint32_t slot = 0; slot < 4; ++slot) {
        uint32_t actor = 0x3B92E0 + slot * 0x12E8;
        if (MEM32(actor + 0x28) == UINT32_MAX) continue;
        const MotionCore *row = custom(MEM32(actor + 0x2C));
        if (row) any = 1;
        active[slot] = 1;
        profile[slot] = !row && MEM32(actor + 0x2C) >= 86;
    }
    if (!any) return 0;
    for (uint32_t slot = 0; slot < 4; ++slot) if (active[slot]) {
        uint32_t actor = 0x3B92E0 + slot * 0x12E8;
        for (uint32_t choice = 0; choice < 4; ++choice) {
            uint32_t value = MEM32((profile[slot] ? 0x3B9288 + slot * 16 : actor + 0xBB8) + choice * 4);
            if (value >= 82) motion_stop("Blazin selection exceeds inherited paired resources");
            choices[slot][choice] = value;
            mask[value * 2] = mask[value * 2 + 1] = 1;
        }
    }
    /* Publish only after all participant choices passed their bounds checks. */
    memcpy((void *)XBOX_PTR(0x3BE628), mask, sizeof mask);
    for (uint32_t slot = 0; slot < 4; ++slot) if (active[slot]) {
        uint32_t actor = 0x3B92E0 + slot * 0x12E8;
        if (profile[slot]) memcpy((void *)XBOX_PTR(actor + 0xBB8), choices[slot], sizeof choices[slot]);
        if (MEM32(actor + 0x2C) >= ORIGINAL_CORES)
            fprintf(stderr, "[FIGHTERS] Blazin core %u slot %u inherited choices %u,%u,%u,%u\n",
                    MEM32(actor + 0x2C), slot, choices[slot][0], choices[slot][1], choices[slot][2], choices[slot][3]);
    }
    g_esp += 4; return 1;
}
