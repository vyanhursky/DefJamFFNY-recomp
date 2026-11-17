/*
 * Append rows to one table of a SODB database (assets/djv2.sod).
 *
 * The same layout and rules as the song list's adder (src/hooks/pc_songs.c, which keeps its
 * own copy): records are appended, existing records keep their offsets and bytes, each index
 * of the table is re-emitted with the new records, and the string table is re-emitted with the
 * new strings. A new record starts as a byte copy of a chosen template row, so fields that are
 * lists (offsets of the template's own lists) are shared with the template.
 *
 * Layout (setup-side reader with the same checks: setup/fighter_sod.py):
 *   0 "SODB", 4 version 2, 8 schema fingerprint, 12 schema, 16 tables, 20 strings (offsets).
 *   index: [tag] count stride; with stride != 0, count keys, then count values of max(stride,1) words.
 *   schema: tagged index, key = hash(table) ^ hash(field) (hash(table) alone = the row name),
 *           value = (word offset in the record, type; 1 = string index).
 *   tables: tagged index, key = hash(table), value = table header:
 *           tag, primary group, secondary group, record count; each group is an index of
 *           (member key -> tagged sub-index of record offsets), keyed sub-indexes sorted by value.
 *   strings: "STRT", count, (hash, offset) pairs; records hold string indexes.
 */
#define _CRT_SECURE_NO_WARNINGS
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pc_sod.h"

#define SOD_MAX (32u << 20)

typedef struct { uint8_t *p; size_t n, cap; } Buf;

static char g_error[256];
static int fail(const char *what)
{
    if (!g_error[0]) snprintf(g_error, sizeof g_error, "%s", what);
    return 0;
}
const char *pc_sod_error(void) { return g_error; }

static int buf_reserve(Buf *b, size_t n)
{
    if (n <= b->cap) return 1;
    size_t cap = b->cap ? b->cap : 4096;
    while (cap < n) cap *= 2;
    uint8_t *p = (uint8_t *)realloc(b->p, cap);
    if (!p) return 0;
    b->p = p;
    b->cap = cap;
    return 1;
}

static uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static void wr32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }

uint32_t pc_sod_hash(const char *s)
{
    uint32_t h = 5381;
    do { h = h * 33 + (uint8_t)*s; } while (*s++);
    return h;
}

typedef struct {
    const uint8_t *p;
    size_t n;
} View;

static int v_range(const View *v, uint32_t off, uint32_t len) { return off <= v->n && len <= v->n - off; }
static uint32_t v_word(const View *v, uint32_t off) { return v_range(v, off, 4) ? rd32(v->p + off) : 0; }

/* Find key in an index; the address of its value words and its position, or 0. */
static uint32_t v_lookup(const View *v, uint32_t index, int tagged, uint32_t key, uint32_t *position)
{
    uint32_t at = index + (tagged ? 4 : 0);
    if (!v_range(v, at, 8)) return 0;
    uint32_t count = v_word(v, at), stride = v_word(v, at + 4);
    if (!stride || stride > 256 || count > 1000000 || !v_range(v, at + 8, count * 4 * (stride + 1))) return 0;
    for (uint32_t i = 0; i < count; i++)
        if (v_word(v, at + 8 + i * 4) == key) {
            if (position) *position = i;
            return at + 8 + count * 4 + i * stride * 4;
        }
    return 0;
}

typedef struct {
    uint32_t header, rows, rec_list, name_word, strings, nstr;
} TableView;

static int table_view(const View *v, const char *table, TableView *t)
{
    memset(t, 0, sizeof *t);
    if (v->n < 24 || memcmp(v->p, "SODB", 4) || rd32(v->p + 4) != 2) return fail("not a version 2 SODB database");
    uint32_t schema = v_word(v, 12), tables = v_word(v, 16);
    t->strings = v_word(v, 20);
    if (!v_range(v, schema, 4) || memcmp(v->p + schema, "SKMA", 4) || !v_range(v, tables, 4) ||
        memcmp(v->p + tables, "DATA", 4) || !v_range(v, t->strings, 8) || memcmp(v->p + t->strings, "STRT", 4))
        return fail("database sections not found");
    t->nstr = v_word(v, t->strings + 4);
    if (t->nstr > 1000000 || !v_range(v, t->strings + 8, t->nstr * 8)) return fail("bad string table");
    uint32_t thash = pc_sod_hash(table);
    uint32_t hv = v_lookup(v, tables, 1, thash, NULL);
    if (!hv) return fail("table not in the database");
    t->header = v_word(v, hv);
    if (!v_range(v, t->header, 16) || v_word(v, t->header) != thash) return fail("bad table header");
    t->rows = v_word(v, t->header + 12);
    uint32_t group0 = v_word(v, t->header + 4);
    if (!v_range(v, group0, 8) || !v_word(v, group0) || v_word(v, group0 + 4) != 1) return fail("bad table index");
    uint32_t members0 = v_word(v, group0);
    uint32_t first_sub = v_word(v, group0 + 8 + members0 * 4);
    if (!v_range(v, first_sub, 12) || v_word(v, first_sub + 4) != t->rows) return fail("bad record index");
    uint32_t sub_stride = v_word(v, first_sub + 8);
    t->rec_list = first_sub + 12 + (sub_stride ? t->rows * 4 : 0);
    if (!t->rows || !v_range(v, t->rec_list, t->rows * 4)) return fail("table has no records");
    uint32_t nv = v_lookup(v, schema, 1, thash, NULL);
    if (!nv) return fail("table has no row name");
    t->name_word = v_word(v, nv);
    return 1;
}

/* The row name of a record, NULL when it has no text. */
static const char *row_name(const View *v, const TableView *t, uint32_t record, uint32_t *hash)
{
    uint32_t idx = v_word(v, record + t->name_word * 4);
    if (idx >= t->nstr) return NULL;
    if (hash) *hash = v_word(v, t->strings + 8 + idx * 8);
    uint32_t off = v_word(v, t->strings + 12 + idx * 8);
    if (!off || !v_range(v, off, 1) || !memchr(v->p + off, 0, v->n - off)) return NULL;
    return (const char *)v->p + off;
}

int pc_sod_row_count(const uint8_t *db, size_t n, const char *table)
{
    View v = { db, n };
    TableView t;
    g_error[0] = 0;
    return table_view(&v, table, &t) ? (int)t.rows : -1;
}

int pc_sod_table_rank(const uint8_t *db, size_t n, const char *table)
{
    View v = { db, n };
    uint32_t position = 0;
    if (n < 24) return -1;
    return v_lookup(&v, v_word(&v, 16), 1, pc_sod_hash(table), &position) ? (int)position : -1;
}

/* Rank = position in the table's name index (the primary group's first member, sorted by name hash). */
int pc_sod_row_rank(const uint8_t *db, size_t n, const char *table, const char *row)
{
    View v = { db, n };
    TableView t;
    g_error[0] = 0;
    if (!table_view(&v, table, &t)) return -1;
    for (uint32_t i = 0; i < t.rows; i++) {
        const char *name = row_name(&v, &t, v_word(&v, t.rec_list + i * 4), NULL);
        if (name && !strcmp(name, row)) return (int)i;
    }
    return -1;
}

/* ---- appending --------------------------------------------------------------------------------- */

typedef struct {
    Buf out;
    uint32_t nstr;
    uint32_t *str_hash, *str_off;
    uint32_t schema;
} Sod;

static int s_range(const Sod *s, uint32_t off, uint32_t len) { return off <= s->out.n && len <= s->out.n - off; }
static uint32_t s_word(const Sod *s, uint32_t off) { return s_range(s, off, 4) ? rd32(s->out.p + off) : 0; }

static uint32_t s_emit(Sod *s, const void *data, size_t n)
{
    while (s->out.n % 4) {
        if (!buf_reserve(&s->out, s->out.n + 1)) return 0;
        s->out.p[s->out.n++] = 0;
    }
    if (s->out.n + n > SOD_MAX || !buf_reserve(&s->out, s->out.n + n)) return 0;
    uint32_t at = (uint32_t)s->out.n;
    memcpy(s->out.p + at, data, n);
    s->out.n += n;
    return at;
}

static int s_intern(Sod *s, const char *value, uint32_t *index)
{
    uint32_t h = pc_sod_hash(value);
    for (uint32_t i = 0; i < s->nstr; i++) {
        if (s->str_hash[i] != h || !s->str_off[i] || !s_range(s, s->str_off[i], 1)) continue;
        if (!strncmp((const char *)s->out.p + s->str_off[i], value, s->out.n - s->str_off[i])) { *index = i; return 1; }
    }
    uint32_t at = s_emit(s, value, strlen(value) + 1);
    if (!at) return fail("database too large");
    uint32_t *hh = (uint32_t *)realloc(s->str_hash, (s->nstr + 1) * sizeof *hh);
    if (hh) s->str_hash = hh;
    uint32_t *oo = (uint32_t *)realloc(s->str_off, (s->nstr + 1) * sizeof *oo);
    if (oo) s->str_off = oo;
    if (!hh || !oo) return fail("out of memory");
    s->str_hash[s->nstr] = h;
    s->str_off[s->nstr] = at;
    *index = s->nstr++;
    return 1;
}

typedef struct { uint32_t value, offset; } Pair;

static int pair_cmp(const void *a, const void *b)
{
    const Pair *x = (const Pair *)a, *y = (const Pair *)b;
    if (x->value != y->value) return x->value < y->value ? -1 : 1;
    return x->offset < y->offset ? -1 : x->offset > y->offset;
}

int pc_sod_add_rows(const uint8_t *in, size_t n, const char *table, const PcSodRow *rows, int count,
                    uint8_t **out, size_t *out_n, char (*names_out)[160])
{
    View v = { in, n };
    TableView t;
    Sod s;
    Pair *pairs = NULL;
    uint32_t *new_rows = NULL;
    int nnew = 0, ok = 0;
    memset(&s, 0, sizeof s);
    g_error[0] = 0;
    *out = NULL;
    *out_n = 0;
    if (n > SOD_MAX || count < 0 || count > 65536) return fail("database or row count out of range");
    if (!table_view(&v, table, &t)) return 0;
    uint32_t thash = pc_sod_hash(table);
    if (!buf_reserve(&s.out, n)) return fail("out of memory");
    memcpy(s.out.p, in, n);
    s.out.n = n;
    s.schema = s_word(&s, 12);
    s.nstr = t.nstr;
    s.str_hash = (uint32_t *)malloc((s.nstr + 1) * sizeof(uint32_t));
    s.str_off = (uint32_t *)malloc((s.nstr + 1) * sizeof(uint32_t));
    new_rows = (uint32_t *)calloc((size_t)count + 1, sizeof *new_rows);
    if (!s.str_hash || !s.str_off || !new_rows) { fail("out of memory"); goto done; }
    for (uint32_t i = 0; i < s.nstr; i++) {
        s.str_hash[i] = s_word(&s, t.strings + 8 + i * 8);
        s.str_off[i] = s_word(&s, t.strings + 12 + i * 8);
    }
    uint32_t max_hash = 0;
    for (uint32_t i = 0; i < t.rows; i++) {
        uint32_t h = 0;
        uint32_t idx = s_word(&s, s_word(&s, t.rec_list + i * 4) + t.name_word * 4);
        if (idx < s.nstr) h = s.str_hash[idx];
        if (h > max_hash) max_hash = h;
    }

    for (int r = 0; r < count; r++) {
        const PcSodRow *row = &rows[r];
        uint32_t template_off = 0;
        for (uint32_t i = 0; i < t.rows && !template_off; i++) {
            uint32_t o = s_word(&s, t.rec_list + i * 4);
            const char *name = row_name(&v, &t, o, NULL);
            if (name && !strcmp(name, row->template_name)) template_off = o;
        }
        if (!template_off) { fail("a template row is not in the table"); goto done; }
        /* The record extends to the next record (records are contiguous in the retail file). */
        uint32_t next = 0;
        for (uint32_t i = 0; i < t.rows; i++) {
            uint32_t o = s_word(&s, t.rec_list + i * 4);
            if (o > template_off && (!next || o < next)) next = o;
        }
        uint32_t bytes = next ? next - template_off : 0;
        uint32_t words = t.name_word + 1;
        for (int f = 0; f < row->nfields; f++) if (row->fields[f].word + 1 > words) words = row->fields[f].word + 1;
        if (bytes >= words * 4 && bytes <= 4096) words = bytes / 4;
        if (row->nfields > PC_SOD_MAX_FIELDS || words > 1024 || !s_range(&s, template_off, words * 4))
            { fail("bad template record"); goto done; }
        char name[160];
        if (!row->name || strlen(row->name) > 120) { fail("row without a usable name"); goto done; }
        snprintf(name, sizeof name, "%s", row->name);
        for (unsigned salt = 1; pc_sod_hash(name) <= max_hash; salt++) {
            if (salt > 100000000u) { fail("no row name sorts last"); goto done; }
            snprintf(name, sizeof name, "%s~%u", row->name, salt);
        }
        if (names_out) snprintf(names_out[r], 160, "%s", name);
        uint8_t rec[4096];
        uint32_t idx;
        memcpy(rec, s.out.p + template_off, words * 4);
        if (!s_intern(&s, name, &idx)) goto done;
        wr32(rec + t.name_word * 4, idx);
        for (int f = 0; f < row->nfields; f++) {
            const PcSodField *field = &row->fields[f];
            if (field->word == t.name_word) { fail("a field overwrites the row name"); goto done; }
            if (field->is_string) {
                if (!field->text || strlen(field->text) > 256 || !s_intern(&s, field->text, &idx)) { fail("bad text field"); goto done; }
                wr32(rec + field->word * 4, idx);
            } else {
                wr32(rec + field->word * 4, field->value);
            }
        }
        new_rows[nnew] = s_emit(&s, rec, words * 4);
        if (!new_rows[nnew]) { fail("database too large"); goto done; }
        nnew++;
    }

    if (nnew) {
        pairs = (Pair *)malloc(((size_t)t.rows + nnew) * sizeof *pairs);
        if (!pairs) { fail("out of memory"); goto done; }
        for (int g = 0; g < 2; g++) {
            uint32_t group = s_word(&s, t.header + 4 + g * 4);
            if (!s_range(&s, group, 8)) { fail("bad table group"); goto done; }
            uint32_t members = s_word(&s, group), gstride = s_word(&s, group + 4);
            if (!members) continue;
            if (gstride != 1 || !s_range(&s, group + 8, members * 8)) { fail("bad table group"); goto done; }
            for (uint32_t m = 0; m < members; m++) {
                uint32_t key = s_word(&s, group + 8 + m * 4);
                uint32_t sub = s_word(&s, group + 8 + members * 4 + m * 4);
                if (!s_range(&s, sub, 12) || s_word(&s, sub + 4) != t.rows) { fail("bad member index"); goto done; }
                uint32_t tag = s_word(&s, sub), keyed = s_word(&s, sub + 8);
                uint32_t list = sub + 12 + (keyed ? t.rows * 4 : 0);
                if (keyed > 1 || !s_range(&s, list, t.rows * 4)) { fail("bad member index"); goto done; }
                uint32_t total = t.rows + (uint32_t)nnew;
                for (uint32_t i = 0; i < t.rows; i++) pairs[i].offset = s_word(&s, list + i * 4);
                for (int i = 0; i < nnew; i++) pairs[t.rows + i].offset = new_rows[i];
                if (keyed) {
                    View sv = { s.out.p, s.out.n };
                    uint32_t vv = v_lookup(&sv, s.schema, 1, key, NULL);
                    if (!vv) { fail("index key not in schema"); goto done; }
                    uint32_t mw = s_word(&s, vv), mt = s_word(&s, vv + 4);
                    for (uint32_t i = 0; i < total; i++) {
                        uint32_t val = s_word(&s, pairs[i].offset + mw * 4);
                        if (key == thash || mt == 1) {
                            if (val >= s.nstr) { fail("bad string reference"); goto done; }
                            val = s.str_hash[val];
                        }
                        pairs[i].value = val;
                    }
                    qsort(pairs, total, sizeof *pairs, pair_cmp);
                }
                Buf blob = {0};
                if (!buf_reserve(&blob, (3 + (size_t)total * 2) * 4)) { fail("out of memory"); goto done; }
                wr32(blob.p, tag);
                wr32(blob.p + 4, total);
                wr32(blob.p + 8, keyed);
                blob.n = 12;
                if (keyed) for (uint32_t i = 0; i < total; i++, blob.n += 4) wr32(blob.p + blob.n, pairs[i].value);
                for (uint32_t i = 0; i < total; i++, blob.n += 4) wr32(blob.p + blob.n, pairs[i].offset);
                uint32_t at = s_emit(&s, blob.p, blob.n);
                free(blob.p);
                if (!at) { fail("database too large"); goto done; }
                wr32(s.out.p + group + 8 + members * 4 + m * 4, at);
            }
        }
        wr32(s.out.p + t.header + 12, t.rows + (uint32_t)nnew);

        Buf blob = {0};
        if (!buf_reserve(&blob, 8 + (size_t)s.nstr * 8)) { fail("out of memory"); goto done; }
        memcpy(blob.p, "STRT", 4);
        wr32(blob.p + 4, s.nstr);
        for (uint32_t i = 0; i < s.nstr; i++) {
            wr32(blob.p + 8 + i * 8, s.str_hash[i]);
            wr32(blob.p + 12 + i * 8, s.str_off[i]);
        }
        uint32_t at = s_emit(&s, blob.p, 8 + (size_t)s.nstr * 8);
        free(blob.p);
        if (!at) { fail("database too large"); goto done; }
        wr32(s.out.p + 20, at);
    }
    ok = 1;
    *out = s.out.p;
    *out_n = s.out.n;
    s.out.p = NULL;
done:
    free(s.out.p);
    free(s.str_hash);
    free(s.str_off);
    free(pairs);
    free(new_rows);
    return ok;
}
