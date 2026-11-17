/*
 * Merge two BIG archives (.viv).
 *
 * Header: "BIGF" or "BIG4", archive size (little endian), entry count and header end (big
 * endian); then entries of (offset, size, both big endian; NUL-terminated name), then a short
 * footer ("L231..." / "L253...") up to the header end, then payloads. The game searches the
 * directory by name; the retail directories are not sorted, so new entries simply follow.
 */
#define _CRT_SECURE_NO_WARNINGS
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pc_big.h"

#define BIG_MAX (512u << 20)
#define BIG_ENTRIES 100000u

static char g_error[256];
static int fail(const char *what)
{
    snprintf(g_error, sizeof g_error, "%s", what);
    return -1;
}
const char *pc_big_error(void) { return g_error; }

static uint32_t be32(const uint8_t *p) { return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3]; }
static void wbe32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v; }
static void wle32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }

typedef struct {
    uint32_t count, header_end, dir_end, first;
    uint32_t *offset, *size, *name;   /* name = byte position of the entry's name */
} Dir;

static void dir_free(Dir *d)
{
    free(d->offset);
    free(d->size);
    free(d->name);
    memset(d, 0, sizeof *d);
}

static int dir_read(const uint8_t *p, size_t n, Dir *d)
{
    memset(d, 0, sizeof *d);
    if (n < 16 || n > BIG_MAX || (memcmp(p, "BIGF", 4) && memcmp(p, "BIG4", 4))) return fail("not a BIG archive");
    d->count = be32(p + 8);
    d->header_end = be32(p + 12);
    if (!d->count || d->count > BIG_ENTRIES || d->header_end < 16 || d->header_end > n) return fail("bad BIG header");
    d->offset = (uint32_t *)malloc(d->count * sizeof(uint32_t));
    d->size = (uint32_t *)malloc(d->count * sizeof(uint32_t));
    d->name = (uint32_t *)malloc(d->count * sizeof(uint32_t));
    if (!d->offset || !d->size || !d->name) return fail("out of memory");
    uint32_t at = 16;
    d->first = (uint32_t)n;
    for (uint32_t i = 0; i < d->count; i++) {
        if (at + 9 > d->header_end) return fail("truncated BIG directory");
        d->offset[i] = be32(p + at);
        d->size[i] = be32(p + at + 4);
        d->name[i] = at + 8;
        const uint8_t *end = (const uint8_t *)memchr(p + at + 8, 0, d->header_end - (at + 8));
        if (!end || end == p + at + 8 || end - (p + at + 8) > 512) return fail("bad BIG entry name");
        if (d->offset[i] < d->header_end || d->size[i] > n || d->offset[i] > n - d->size[i]) return fail("BIG entry out of bounds");
        if (d->offset[i] < d->first) d->first = d->offset[i];
        at = (uint32_t)(end - p) + 1;
    }
    d->dir_end = at;
    return 0;
}

static int same_name(const char *a, const char *b)
{
    for (; *a && *b; a++, b++)
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
    return *a == *b;
}

static int listed(const char *name, const char *const *names)
{
    for (; names && *names; names++) if (same_name(name, *names)) return 1;
    return 0;
}

int pc_big_append(const uint8_t *base, size_t base_n, const uint8_t *add, size_t add_n,
                  const char *const *replaceable, uint8_t **out, size_t *out_n)
{
    Dir b, a;
    int result = -1;
    int32_t *replaces = NULL;     /* per add member: the base entry it replaces, or -1 */
    uint32_t *placed = NULL;      /* per add member: its payload offset in the output */
    *out = NULL;
    *out_n = 0;
    g_error[0] = 0;
    if (dir_read(base, base_n, &b) < 0 || dir_read(add, add_n, &a) < 0) goto done;
    if (b.count + a.count > BIG_ENTRIES) { fail("too many BIG entries"); goto done; }
    replaces = (int32_t *)malloc(a.count * sizeof *replaces);
    placed = (uint32_t *)malloc(a.count * sizeof *placed);
    if (!replaces || !placed) { fail("out of memory"); goto done; }
    uint32_t appended = 0;
    for (uint32_t i = 0; i < a.count; i++) {
        replaces[i] = -1;
        for (uint32_t j = 0; j < b.count && replaces[i] < 0; j++)
            if (same_name((const char *)add + a.name[i], (const char *)base + b.name[j])) {
                if (!listed((const char *)add + a.name[i], replaceable)) {
                    snprintf(g_error, sizeof g_error, "the game already has %s", (const char *)add + a.name[i]);
                    goto done;
                }
                replaces[i] = (int32_t)j;
            }
        for (uint32_t k = 0; k < i; k++)
            if (same_name((const char *)add + a.name[i], (const char *)add + a.name[k])) { fail("duplicate added file"); goto done; }
        if (replaces[i] < 0) appended++;
    }
    size_t added_dir = 0, added_data = 0;
    for (uint32_t i = 0; i < a.count; i++) {
        if (replaces[i] < 0) added_dir += 9 + strlen((const char *)add + a.name[i]);
        added_data += a.size[i] + 2048;
    }
    uint32_t footer = b.header_end - b.dir_end;
    uint32_t new_header_end = b.dir_end + (uint32_t)added_dir + footer;
    uint32_t shift = 0;
    while (b.first + shift < new_header_end) shift += 4096;
    size_t total = base_n + shift + added_data;
    if (total > BIG_MAX) { fail("merged archive too large"); goto done; }
    uint8_t *o = (uint8_t *)calloc(1, total);
    if (!o) { fail("out of memory"); goto done; }
    memcpy(o, base, 16);
    /* The base's bytes from its first payload on, unchanged, at their new place; then the
     * added payloads. */
    memcpy(o + b.first + shift, base + b.first, base_n - b.first);
    size_t data = base_n + shift;
    for (uint32_t i = 0; i < a.count; i++) {
        data += (2048 - data % 2048) % 2048;
        placed[i] = (uint32_t)data;
        memcpy(o + data, add + a.offset[i], a.size[i]);
        data += a.size[i];
    }
    size_t at = 16;
    for (uint32_t j = 0; j < b.count; j++) {
        size_t len = strlen((const char *)base + b.name[j]) + 1;
        uint32_t offset = b.offset[j] + shift, size = b.size[j];
        for (uint32_t i = 0; i < a.count; i++)
            if (replaces[i] == (int32_t)j) { offset = placed[i]; size = a.size[i]; }
        wbe32(o + at, offset);
        wbe32(o + at + 4, size);
        memcpy(o + at + 8, base + b.name[j], len);
        at += 8 + len;
    }
    for (uint32_t i = 0; i < a.count; i++) {
        if (replaces[i] >= 0) continue;
        size_t len = strlen((const char *)add + a.name[i]) + 1;
        wbe32(o + at, placed[i]);
        wbe32(o + at + 4, a.size[i]);
        memcpy(o + at + 8, add + a.name[i], len);
        at += 8 + len;
    }
    memcpy(o + at, base + b.dir_end, footer);
    wbe32(o + 8, b.count + appended);
    wbe32(o + 12, new_header_end);
    wle32(o + 4, (uint32_t)data);
    *out = o;
    *out_n = data;
    result = (int)a.count;
done:
    free(replaces);
    free(placed);
    dir_free(&b);
    dir_free(&a);
    return result;
}

/* ---- members, building, RefPack ------------------------------------------------------------------ */

int pc_big_members(const uint8_t *p, size_t n, PcBigMember **out)
{
    Dir d;
    *out = NULL;
    g_error[0] = 0;
    if (dir_read(p, n, &d) < 0) { dir_free(&d); return -1; }
    PcBigMember *m = (PcBigMember *)calloc(d.count, sizeof *m);
    if (!m) { dir_free(&d); return fail("out of memory"); }
    for (uint32_t i = 0; i < d.count; i++) {
        snprintf(m[i].name, sizeof m[i].name, "%s", (const char *)p + d.name[i]);
        m[i].data = p + d.offset[i];
        m[i].size = d.size[i];
    }
    int count = (int)d.count;
    dir_free(&d);
    *out = m;
    return count;
}

const PcBigMember *pc_big_find(const PcBigMember *m, int count, const char *name)
{
    for (int i = 0; i < count; i++) if (same_name(m[i].name, name)) return &m[i];
    return NULL;
}

/* Like build_archive in setup/clothing_pack.py: BIGF, entries in the given order, an L231 footer,
 * 128-byte aligned payloads. */
int pc_big_build(const PcBigMember *m, int count, uint8_t **out, size_t *out_n)
{
    size_t directory = 16, total;
    *out = NULL;
    *out_n = 0;
    if (count <= 0 || (uint32_t)count > BIG_ENTRIES) return fail("bad member count");
    for (int i = 0; i < count; i++) directory += 9 + strlen(m[i].name);
    size_t first = directory + 8;
    first += (128 - first % 128) % 128;
    total = first;
    for (int i = 0; i < count; i++) { total += m[i].size; total += (128 - total % 128) % 128; }
    if (total > BIG_MAX) return fail("archive too large");
    uint8_t *o = (uint8_t *)calloc(1, total);
    if (!o) return fail("out of memory");
    memcpy(o, "BIGF", 4);
    wle32(o + 4, (uint32_t)total);
    wbe32(o + 8, (uint32_t)count);
    wbe32(o + 12, (uint32_t)(directory + 8));
    size_t at = 16, data = first;
    for (int i = 0; i < count; i++) {
        size_t len = strlen(m[i].name) + 1;
        wbe32(o + at, (uint32_t)data);
        wbe32(o + at + 4, (uint32_t)m[i].size);
        memcpy(o + at + 8, m[i].name, len);
        at += 8 + len;
        if (m[i].size) memcpy(o + data, m[i].data, m[i].size);
        data += m[i].size;
        data += (128 - data % 128) % 128;
    }
    memcpy(o + at, "L231\0\0\0\1", 8);
    *out = o;
    *out_n = total;
    return count;
}

int pc_refpack_is(const uint8_t *p, size_t n)
{
    return n >= 5 && ((p[0] << 8 | p[1]) & 0x3EFF) == 0x10FB;
}

/* The game's RefPack (the same decoder as src/hooks/pc_language.c). */
int pc_refpack_decode(const uint8_t *src, size_t n, uint8_t **out, size_t *out_n)
{
    unsigned sig = (unsigned)(src[0] << 8 | src[1]);
    size_t pos = 2, step = (sig & 0x8000) ? 4 : 3, size = 0, have = 0;
    *out = NULL;
    *out_n = 0;
    if (!pc_refpack_is(src, n)) return fail("not RefPack") + 1;
    if (sig & 0x0100) pos += step;
    if (pos + step > n) return fail("truncated RefPack header") + 1;
    for (size_t i = 0; i < step; i++) size = size << 8 | src[pos + i];
    pos += step;
    if (size > (64u << 20)) return fail("RefPack entry too large") + 1;
    uint8_t *o = (uint8_t *)malloc(size + 4);
    if (!o) return fail("out of memory") + 1;
    while (pos < n) {
        unsigned b0 = src[pos++], b1, b2, b3;
        size_t run, length = 0, dist = 0;
        if (b0 < 0x80) {
            if (pos + 1 > n) break;
            b1 = src[pos++];
            run = b0 & 3; length = ((b0 & 0x1C) >> 2) + 3; dist = ((b0 & 0x60) << 3) + b1 + 1;
        } else if (b0 < 0xC0) {
            if (pos + 2 > n) break;
            b1 = src[pos]; b2 = src[pos + 1]; pos += 2;
            run = (b1 >> 6) & 3; length = (b0 & 0x3F) + 4; dist = ((b1 & 0x3F) << 8) + b2 + 1;
        } else if (b0 < 0xE0) {
            if (pos + 3 > n) break;
            b1 = src[pos]; b2 = src[pos + 1]; b3 = src[pos + 2]; pos += 3;
            run = b0 & 3; length = ((b0 & 0x0C) << 6) + b3 + 5; dist = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1;
        } else if (b0 < 0xFC) {
            run = ((b0 & 0x1F) << 2) + 4;
        } else {
            run = b0 & 3;
        }
        if (pos + run > n || have + run + length > size + 3 || dist > have + run) { free(o); return fail("corrupt RefPack stream") + 1; }
        memcpy(o + have, src + pos, run);
        have += run;
        pos += run;
        for (size_t i = 0; i < length; i++, have++) o[have] = o[have - dist];
        if (b0 >= 0xFC) break;
    }
    if (have < size) { free(o); return fail("short RefPack stream") + 1; }
    *out = o;
    *out_n = size;
    return 1;
}

/* Literal-only RefPack, as setup/fighter_archive.py store(). */
int pc_refpack_store(const uint8_t *data, size_t n, uint8_t **out, size_t *out_n)
{
    size_t cap = n + n / 112 + 16, at = 0, pos = 0;
    uint8_t *o = (uint8_t *)malloc(cap);
    *out = NULL;
    *out_n = 0;
    if (!o || n == 0 || n >= (1u << 24)) { free(o); return fail("cannot store this entry") + 1; }
    o[at++] = 0x10; o[at++] = 0xFB; o[at++] = (uint8_t)(n >> 16); o[at++] = (uint8_t)(n >> 8); o[at++] = (uint8_t)n;
    while (n - pos >= 4) {
        size_t run = n - pos >= 112 ? 112 : (n - pos) & ~(size_t)3;
        o[at++] = (uint8_t)(0xE0 + ((run - 4) >> 2));
        memcpy(o + at, data + pos, run);
        at += run;
        pos += run;
    }
    o[at++] = (uint8_t)(0xFC + (n - pos));
    memcpy(o + at, data + pos, n - pos);
    at += n - pos;
    *out = o;
    *out_n = at;
    return 1;
}
