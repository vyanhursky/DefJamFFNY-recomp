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
