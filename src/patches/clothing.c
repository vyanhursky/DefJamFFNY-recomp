/*
 * Custom Story clothing (docs/custom-clothing.md).
 *
 * Clothing packs are compiled before Play by setup/clothing_pack.py into <data>/cache/clothing:
 *   items.txt        one line per item: key, base row, texture-set code, colours, price,
 *                    availability (wardrobe|shop), display name
 *   v2cp-add.viv     the items' garment textures (V2CP_<cat>_<model>_<code>_<colour>.xsh)
 *   screens-add.viv  their shop and wardrobe thumbnails
 *
 * At start this file
 *   - appends one Clothing row per item to the game's database (a copy of its base row with the
 *     item's own texture-set code, name and price; the retail rows keep their ranks and so the
 *     record handles saves hold), and serves that copy as assets/djv2.sod;
 *   - serves assets/v2cp_0.viv and screens/screens.viv with the pack's files appended (the game
 *     opens all four v2cp archives and finds a texture in any of them);
 *   - keeps the items' own states (locked / unlocked / owned) in a table of its own: the
 *     profile's clothing state set holds 2 bits per retail item and colour in a fixed block of
 *     the save, so added items never enter it (clothing_after_build) and its methods are
 *     answered here for them (clothing_set_call);
 *   - answers the game's text lookup for the items' names.
 * Wardrobe items are owned from the start; shop items are unlocked (to buy).
 *
 * Probe: RECOMP_CLOTHING_PROBE=1 logs the state sets. Trace: RECOMP_CLOTHING_TRACE=1.
 */
#define _CRT_SECURE_NO_WARNINGS
#include "host.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <sys/stat.h>
#if defined(_WIN32)
#include <direct.h>
#else
#include <strings.h>
#define _stricmp strcasecmp
#define _strdup strdup
#endif

#include "recomp/gen/recomp_types.h"
#include "hooks/guest_call.h"
#include "hooks/pc_big.h"
#include "hooks/pc_sod.h"
#include "clothing.h"

#if defined(_WIN32)
typedef WCHAR xbox_host_char;
#else
typedef char xbox_host_char;
#endif
extern BOOL (*g_xbox_game_file_redirect)(const char *relative, xbox_host_char *host_path, DWORD size);
extern void sub_00029680(void);   /* the game's allocator (size, tag, flags) */

#define PATH_MAX_LEN   1024
#define FILE_MAX       (600u << 20)
#define SOD_NAME       "assets/djv2.sod"
/* The served files: the database, the four garment archives (the creator reads each body part's
 * files from one fixed archive, "assets/v2cp_N.viv|<name>", sub_000990B0), the thumbnails. */
#define SERVED 6
static const char *const k_served[SERVED] = {
    SOD_NAME, "assets/v2cp_0.viv", "assets/v2cp_1.viv", "assets/v2cp_2.viv", "assets/v2cp_3.viv", "screens/screens.viv",
};
static const char *const k_add[SERVED] = {
    NULL, "v2cp_0-add.viv", "v2cp_1-add.viv", "v2cp_2-add.viv", "v2cp_3-add.viv", "screens-add.viv",
};
#define TABLE          "Clothing"
#define F_VARIANT      2u      /* Clothing record words (setup/clothing_pack.py, Game._rows) */
#define F_COST         4u
#define F_DISPLAY      5u
#define SLOTS          16u     /* profile slots; the state sets keep one block per slot */
#define SET_CLOTHING   0x1594u /* the clothing state set in the profile manager */
#define SLOT_INDEX     0x5AC7Cu
#define STATE_UNLOCKED 1u
#define STATE_OWNED    3u      /* "Owned" is bit 1; the retail cheat sets 3 */

typedef struct {
    char key[96], base[128], variant[8], avail[12], name[CLOTHING_MAX_NAME + 1];
    char row[160], text_key[96];
    char compiled[8], base_variant[8];          /* the compiler's code; the base's own set */
    uint32_t colours, price, text_hash, rank, base_rank, first;   /* first: its first state in g_state[slot] */
    uint32_t category, models[CLOTHING_MAX_FITS];                /* every fit model (base model first) */
    int nmodels;
} Item;

/* Where a profile row (slot + 0x1788, 0x5904 bytes, what a save holds) keeps the appearance: two
 * 38-word part arrays (the outfit worn, and the copy the creator keeps to undo), clothing in
 * parts 12-19. Found with RECOMP_CLOTHING_PROBE; the handles there are table<<24|colour<<16|row. */
#define ROW_OFFSET     0x1788u
#define ROW_BYTES      0x5904u
#define SLOT_STRIDE    0x5950u
static const uint32_t k_part_arrays[2] = { 0x5558u, 0x5618u };
#define PART_FIRST     12u
#define PART_LAST      19u

static Item g_items[CLOTHING_MAX_ITEMS];
static int g_count;
static uint32_t g_states;                 /* total colours of all items */
static uint8_t *g_state[SLOTS];
static int g_active, g_trace, g_probe;
static uint32_t g_table_rank = 0xFFFFFFFFu, g_retail_rows, g_rows;
static char g_served[SERVED][PATH_MAX_LEN];   /* host paths, k_served order */
static uint32_t g_name_pool;              /* guest UTF-16 names, allocated on first use */
static uint32_t g_name_offset[CLOTHING_MAX_ITEMS];
static BOOL (*g_previous_redirect)(const char *relative, xbox_host_char *host_path, DWORD size);
static char g_state_dir[PATH_MAX_LEN];    /* <data>/clothing-state */
static char g_digest[80];                 /* clothing-set-1 of the enabled packs (items.txt) */

static int env_on(const char *name)
{
    const char *v = getenv(name);
    return v && *v && strcmp(v, "0");
}

/* ---- files -------------------------------------------------------------------------------------- */

static int read_all(const char *path, uint8_t **data, size_t *n)
{
    FILE *f = fopen(path, "rb");
    *data = NULL;
    *n = 0;
    if (!f) return 0;
    if (fseek(f, 0, SEEK_END) || ftell(f) <= 0 || ftell(f) > (long)FILE_MAX) { fclose(f); return 0; }
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    *data = (uint8_t *)malloc((size_t)len);
    if (*data && fread(*data, 1, (size_t)len, f) == (size_t)len) *n = (size_t)len;
    fclose(f);
    if (!*n) { free(*data); *data = NULL; return 0; }
    return 1;
}

static void make_dirs(const char *path)
{
    char tmp[PATH_MAX_LEN];
    snprintf(tmp, sizeof tmp, "%s", path);
    for (char *p = tmp + 1; *p; p++) {
        if (*p != '/' && *p != '\\') continue;
        char c = *p;
        *p = 0;
#if defined(_WIN32)
        _mkdir(tmp);
#else
        mkdir(tmp, 0755);
#endif
        *p = c;
    }
}

/* Write unless the file already holds exactly these bytes (a running game's copy stays valid). */
static int write_if_changed(const char *path, const uint8_t *data, size_t n)
{
    uint8_t *old = NULL;
    size_t old_n = 0;
    int same = read_all(path, &old, &old_n) && old_n == n && !memcmp(old, data, n);
    free(old);
    if (same) return 1;
    char part[PATH_MAX_LEN + 8];
    snprintf(part, sizeof part, "%s.part", path);
    make_dirs(path);
    FILE *f = fopen(part, "wb");
    int ok = f && fwrite(data, 1, n, f) == n;
    if (f && fclose(f)) ok = 0;
    remove(path);
    if (!ok || rename(part, path)) { remove(part); return 0; }
    return 1;
}

/* "size:mtime" of a file, "-" when it is missing. */
static void file_stamp(const char *path, char *out, size_t size)
{
    struct stat st;
    if (stat(path, &st)) snprintf(out, size, "-");
    else snprintf(out, size, "%lld:%lld", (long long)st.st_size, (long long)st.st_mtime);
}

static BOOL serve(const char *host, xbox_host_char *host_path, DWORD size)
{
#if defined(_WIN32)
    return MultiByteToWideChar(CP_UTF8, 0, host, -1, host_path, (int)size) != 0;
#else
    return (size_t)snprintf(host_path, size, "%s", host) < size;
#endif
}

static int same_name(const char *a, const char *b)
{
    for (; *a && *b; a++, b++) {
        char x = *a == '\\' ? '/' : (char)((*a >= 'A' && *a <= 'Z') ? *a + 32 : *a);
        char y = *b == '\\' ? '/' : (char)((*b >= 'A' && *b <= 'Z') ? *b + 32 : *b);
        if (x != y) return 0;
    }
    return *a == *b;
}

static BOOL clothing_redirect(const char *relative, xbox_host_char *host_path, DWORD size)
{
    for (int i = 0; i < SERVED; i++)
        if (g_served[i][0] && same_name(relative, k_served[i])) return serve(g_served[i], host_path, size);
    return g_previous_redirect ? g_previous_redirect(relative, host_path, size) : FALSE;
}

/* The file the game would otherwise read: an earlier redirect's (a language pack, fighters,
 * songs), else the dump's. */
static int source_file(const char *game_dir, const char *relative, char *out, size_t size)
{
    if (g_previous_redirect) {
        xbox_host_char host[PATH_MAX_LEN];
        if (g_previous_redirect(relative, host, PATH_MAX_LEN)) {
#if defined(_WIN32)
            return WideCharToMultiByte(CP_UTF8, 0, host, -1, out, (int)size, NULL, NULL) != 0;
#else
            return (size_t)snprintf(out, size, "%s", host) < size;
#endif
        }
    }
    char rel[256];
    snprintf(rel, sizeof rel, "%s", relative);
    for (char *p = rel; *p; p++) if (*p == '/') *p = HOST_SEP_CHAR;
    return (size_t)snprintf(out, size, "%s" HOST_SEP "%s", game_dir, rel) < size;
}

/* ---- items.txt ---------------------------------------------------------------------------------- */

static int split_tabs(char *line, char **fields, int max)
{
    int n = 0;
    fields[n++] = line;
    for (char *p = line; *p && n < max; p++)
        if (*p == '\t') { *p = 0; fields[n++] = p + 1; }
    return n;
}

static Item *item_by_key(const char *key);

static int read_items(const char *path)
{
    FILE *f = fopen(path, "rb");
    char line[1024];
    if (!f) return 0;
    if (!fgets(line, sizeof line, f) || strncmp(line, "clothing-items-1", 16)) {
        fclose(f);
        fprintf(stderr, "[CLOTHING] %s is not a clothing item list; no custom clothing\n", path);
        return 0;
    }
    g_count = 0;
    while (fgets(line, sizeof line, f) && g_count < CLOTHING_MAX_ITEMS) {
        char *fields[8];
        line[strcspn(line, "\r\n")] = 0;
        if (!line[0]) continue;
        if (!strncmp(line, "#clothing-set-1\t", 16)) {     /* the compiler's digest of the enabled packs */
            snprintf(g_digest, sizeof g_digest, "%s", line + 16);
            continue;
        }
        if (split_tabs(line, fields, 8) != 7) continue;
        Item *it = &g_items[g_count];
        memset(it, 0, sizeof *it);
        if (strlen(fields[0]) >= sizeof it->key || strlen(fields[1]) >= sizeof it->base || strlen(fields[2]) != 3
            || strlen(fields[5]) >= sizeof it->avail || strlen(fields[6]) > CLOTHING_MAX_NAME || !fields[6][0]) continue;
        snprintf(it->key, sizeof it->key, "%s", fields[0]);
        snprintf(it->base, sizeof it->base, "%s", fields[1]);
        snprintf(it->variant, sizeof it->variant, "%s", fields[2]);
        snprintf(it->compiled, sizeof it->compiled, "%s", fields[2]);
        it->colours = (uint32_t)strtoul(fields[3], NULL, 10);
        it->price = (uint32_t)strtoul(fields[4], NULL, 10);
        snprintf(it->avail, sizeof it->avail, "%s", fields[5]);
        snprintf(it->name, sizeof it->name, "%s", fields[6]);
        if (it->colours < 1 || it->colours > 32 || it->price > 99999) continue;
        snprintf(it->row, sizeof it->row, "Custom_%s", it->key);
        /* The game shows a DisplayName string's own text when it has one (retail names have
         * none and go through the language's string table); clothing_localized() answers the
         * lookup by its hash as well. */
        snprintf(it->text_key, sizeof it->text_key, "%s", it->name);
        it->text_hash = pc_sod_hash(it->text_key);
        g_count++;
    }
    fclose(f);
    return g_count > 0;
}

/* ---- serving the three files --------------------------------------------------------------------- */

static int serve_database(const char *game_dir, const char *cache)
{
    char source[PATH_MAX_LEN], served[PATH_MAX_LEN];
    uint8_t *in = NULL, *out = NULL;
    size_t in_n = 0, out_n = 0;
    PcSodRow *rows = (PcSodRow *)calloc((size_t)g_count, sizeof *rows);
    char (*names)[160] = (char (*)[160])calloc((size_t)g_count, 160);
    int ok = 0;
    if (!rows || !names) goto done;
    if (!source_file(game_dir, SOD_NAME, source, sizeof source) || !read_all(source, &in, &in_n)) {
        fprintf(stderr, "[CLOTHING] cannot read %s\n", source);
        goto done;
    }
    int retail = pc_sod_row_count(in, in_n, TABLE), rank = pc_sod_table_rank(in, in_n, TABLE);
    if (retail <= 0 || rank < 0) { fprintf(stderr, "[CLOTHING] no Clothing table in %s\n", source); goto done; }
    for (int i = 0; i < g_count; i++) {
        Item *it = &g_items[i];
        rows[i].template_name = it->base;
        rows[i].name = it->row;
        rows[i].nfields = 3;
        rows[i].fields[0] = (PcSodField){ F_VARIANT, 1, it->variant, 0 };
        rows[i].fields[1] = (PcSodField){ F_COST, 0, NULL, it->price };
        rows[i].fields[2] = (PcSodField){ F_DISPLAY, 1, it->text_key, 0 };
    }
    if (!pc_sod_add_rows(in, in_n, TABLE, rows, g_count, &out, &out_n, names)) {
        fprintf(stderr, "[CLOTHING] clothing rows not added (%s)\n", pc_sod_error());
        goto done;
    }
    g_retail_rows = (uint32_t)retail;
    g_table_rank = (uint32_t)rank;
    g_rows = (uint32_t)pc_sod_row_count(out, out_n, TABLE);
    g_states = 0;
    for (int i = 0; i < g_count; i++) {
        Item *it = &g_items[i];
        snprintf(it->row, sizeof it->row, "%s", names[i]);
        int r = pc_sod_row_rank(out, out_n, TABLE, it->row);
        if (r < (int)g_retail_rows) { fprintf(stderr, "[CLOTHING] row %s did not sort after the retail rows\n", it->row); goto done; }
        it->rank = (uint32_t)r;
        int b = pc_sod_row_rank(in, in_n, TABLE, it->base);
        if (b < 0 || b >= retail) { fprintf(stderr, "[CLOTHING] base row %s not found\n", it->base); goto done; }
        it->base_rank = (uint32_t)b;
        it->first = g_states;
        g_states += it->colours;
    }
    snprintf(served, sizeof served, "%s" HOST_SEP "served" HOST_SEP "djv2.sod", cache);
    if (!write_if_changed(served, out, out_n)) { fprintf(stderr, "[CLOTHING] cannot write %s\n", served); goto done; }
    snprintf(g_served[0], sizeof g_served[0], "%s", served);
    ok = 1;
done:
    free(in);
    free(out);
    free(rows);
    free(names);
    return ok;
}

/* ---- the chain: codes and the parts catalogue from the files actually served ---------------------
 *
 * Other layers (a language pack, a fork's own clothing tool) may serve the v2cp archives and
 * screens.viv before us. Texture-set codes are taken so they are free in the copies served, and
 * the creator's parts catalogue is the served one with our lines inserted, so another layer's
 * lines stay. Codes: retail uses A..L; this system uses Z01..Z99 (the compiler's choice first);
 * FFNY Online's Studio uses Y. docs/custom-clothing.md.
 */

#define PARTS_NAME "createplayer_parts.xml"

typedef struct { char **names; int count; } NameList;

static NameList g_names[SERVED];           /* directory names of the served sources (slots 1..5) */
static char *g_catalogue;                  /* the served parts catalogue (text), patched */
static size_t g_catalogue_n;
static char g_codes[4096];                 /* "key=code;" of every item, for the served-copy stamp */

static void names_free(NameList *l)
{
    for (int i = 0; i < l->count; i++) free(l->names[i]);
    free(l->names);
    l->names = NULL;
    l->count = 0;
}

/* The directory of a BIG archive: its names (read from the head of the file only). */
static int read_names(const char *path, NameList *out)
{
    FILE *f = fopen(path, "rb");
    uint8_t head[16];
    out->names = NULL;
    out->count = 0;
    if (!f) return 0;
    if (fread(head, 1, 16, f) != 16 || (memcmp(head, "BIGF", 4) && memcmp(head, "BIG4", 4))) { fclose(f); return 0; }
    uint32_t count = (uint32_t)head[8] << 24 | (uint32_t)head[9] << 16 | (uint32_t)head[10] << 8 | head[11];
    uint32_t end = (uint32_t)head[12] << 24 | (uint32_t)head[13] << 16 | (uint32_t)head[14] << 8 | head[15];
    if (!count || count > 100000u || end < 16 || end > (64u << 20)) { fclose(f); return 0; }
    uint8_t *dir = (uint8_t *)malloc(end);
    if (!dir) { fclose(f); return 0; }
    memcpy(dir, head, 16);
    int ok = fread(dir + 16, 1, end - 16, f) == end - 16;
    fclose(f);
    out->names = ok ? (char **)calloc(count, sizeof(char *)) : NULL;
    for (uint32_t i = 0, at = 16; ok && out->names && i < count; i++) {
        const uint8_t *z = at + 8 < end ? (const uint8_t *)memchr(dir + at + 8, 0, end - at - 8) : NULL;
        if (!z) break;
        out->names[out->count++] = _strdup((const char *)dir + at + 8);
        at = (uint32_t)(z - dir) + 1;
    }
    free(dir);
    return out->names != NULL;
}

/* One member of a BIG archive file, decoded (RefPack or stored). */
static int read_member(const char *path, const char *name, uint8_t **data, size_t *n)
{
    uint8_t *all = NULL;
    size_t all_n = 0;
    PcBigMember *m = NULL;
    int ok = 0;
    *data = NULL;
    *n = 0;
    if (!read_all(path, &all, &all_n)) return 0;
    int count = pc_big_members(all, all_n, &m);
    const PcBigMember *e = count > 0 ? pc_big_find(m, count, name) : NULL;
    if (e) {
        if (pc_refpack_is(e->data, e->size)) ok = pc_refpack_decode(e->data, e->size, data, n);
        else if ((*data = (uint8_t *)malloc(e->size + 1)) != NULL) { memcpy(*data, e->data, e->size); *n = e->size; ok = 1; }
    }
    free(m);
    free(all);
    return ok;
}

static int has_prefix_ci(const char *s, const char *prefix)
{
    for (; *prefix; s++, prefix++)
        if (tolower((unsigned char)*s) != tolower((unsigned char)*prefix)) return 0;
    return 1;
}

static int code_taken(const Item *it, const char *code, int upto)
{
    char prefix[96];
    for (int k = 0; k < it->nmodels; k++) {
        snprintf(prefix, sizeof prefix, "V2CP_%03u_%04u_%s_", it->category, it->models[k], code);
        for (int slot = 1; slot <= 4; slot++)
            for (int i = 0; i < g_names[slot].count; i++)
                if (has_prefix_ci(g_names[slot].names[i], prefix)) return 1;
        if (g_catalogue && strstr(g_catalogue, prefix)) return 1;
        for (int j = 0; j < upto; j++) {           /* an item before it on the same model */
            const Item *o = &g_items[j];
            if (o->category != it->category || strcmp(o->variant, code)) continue;
            for (int q = 0; q < o->nmodels; q++) if (o->models[q] == it->models[k]) return 1;
        }
    }
    snprintf(prefix, sizeof prefix, "screens/shopThumbs/100/V2TN_%03u_%04u_%s_", it->category, it->models[0], code);
    for (int i = 0; i < g_names[5].count; i++)
        if (has_prefix_ci(g_names[5].names[i], prefix)) return 1;
    return 0;
}

/* Give every item a code free in the served copies; drop an item when none is. */
static void choose_codes(void)
{
    int kept = 0;
    size_t n = 0;
    for (int i = 0; i < g_count; i++) {
        Item *it = &g_items[i];
        if (it->nmodels == 0) {
            fprintf(stderr, "[CLOTHING] %s: no parts lines (compile the packs again); left out\n", it->key);
            continue;
        }
        g_items[kept] = *it;
        it = &g_items[kept];
        char code[4];
        snprintf(code, sizeof code, "%s", it->compiled);
        int free_code = !code_taken(it, code, kept);
        for (int c = 1; !free_code && c <= 99; c++) {
            snprintf(code, sizeof code, "Z%02d", c);
            free_code = !code_taken(it, code, kept);
        }
        if (!free_code) {
            fprintf(stderr, "[CLOTHING] %s: every Z code is taken on its models; left out\n", it->key);
            continue;
        }
        snprintf(it->variant, sizeof it->variant, "%s", code);
        if (strcmp(code, it->compiled))
            fprintf(stderr, "[CLOTHING] %s: %s is taken in the files served before ours; it uses %s\n", it->key, it->compiled, code);
        n += (size_t)snprintf(g_codes + n, n < sizeof g_codes ? sizeof g_codes - n : 0, "%s=%s;", it->key, code);
        kept++;
    }
    g_count = kept;
}

/* The served catalogue with a texture set per item under each of its fit meshes. */
static void patch_catalogue(void)
{
    if (!g_catalogue) return;
    const char *text = g_catalogue, *newline = strstr(text, "\r\n") ? "\r\n" : "\n";
    size_t cap = g_catalogue_n + 4096, n = 0;
    for (int i = 0; i < g_count; i++) cap += (size_t)g_items[i].nmodels * (256 + 128 * g_items[i].colours);
    char *out = (char *)malloc(cap);
    if (!out) return;
    const char *at = text;
    int patched = 0;
    for (;;) {
        const char *start = strstr(at, "<model>");
        const char *end = start ? strstr(start, "</model>") : NULL;
        if (!start || !end) break;
        /* The block's mesh: its first <name>, e.g. V2CP_121_0027_C; the stem is up to the third '_'. */
        const char *nm = strstr(start, "<name>");
        char stem[32] = "";
        if (nm && nm < end) {
            nm += 6;
            int us = 0, k = 0;
            while (nm[k] && nm[k] != '<' && k < 30) { stem[k] = nm[k]; if (nm[k] == '_' && ++us == 3) { k++; break; } k++; }
            stem[k] = us == 3 ? 0 : (stem[0] = 0);
        }
        /* Text up to the block's end, trailing tabs trimmed when something is inserted. */
        size_t body = (size_t)(end - at);
        char added[65536];
        size_t an = 0;
        int sets = 0;
        for (int i = 0; stem[0] && i < g_count; i++) {
            const Item *it = &g_items[i];
            for (int k = 0; k < it->nmodels; k++) {
                char s[32], first[96];
                snprintf(s, sizeof s, "V2CP_%03u_%04u_", it->category, it->models[k]);
                if (_stricmp(s, stem)) continue;
                snprintf(first, sizeof first, "<name>%s%s_01</name>", s, it->base_variant);
                const char *f = strstr(start, first);
                if (!f || f > end || an + 4096 > sizeof added) continue;
                an += (size_t)snprintf(added + an, sizeof added - an, "\t\t\t\t<texture>%s\t\t\t\t\t<name>%s%s_01</name>%s",
                                       newline, s, it->variant, newline);
                if (it->colours > 1) {
                    an += (size_t)snprintf(added + an, sizeof added - an, "\t\t\t\t\t<count>%u</count>%s", it->colours - 1, newline);
                    for (uint32_t c = 2; c <= it->colours; c++)
                        an += (size_t)snprintf(added + an, sizeof added - an,
                                               "\t\t\t\t\t<colour>%s\t\t\t\t\t\t<name>%s%s_%02u</name>%s\t\t\t\t\t</colour>%s",
                                               newline, s, it->variant, c, newline, newline);
                }
                an += (size_t)snprintf(added + an, sizeof added - an, "\t\t\t\t</texture>%s", newline);
                sets++;
            }
        }
        if (n + body + an + 64 > cap) break;
        if (!sets) {
            memcpy(out + n, at, body);
            n += body;
        } else {
            /* The block's own texture count goes up by the sets added. */
            const char *count = strstr(start, "<count>");
            size_t pre = count && count < end ? (size_t)(count + 7 - at) : 0;
            if (pre) {
                memcpy(out + n, at, pre);
                n += pre;
                n += (size_t)snprintf(out + n, cap - n, "%d", atoi(count + 7) + sets);
                const char *after = count + 7;
                while (*after >= '0' && *after <= '9') after++;
                at = after;
                body = (size_t)(end - at);
            }
            while (body && at[body - 1] == '\t') body--;
            memcpy(out + n, at, body);
            n += body;
            memcpy(out + n, added, an);
            n += an;
            n += (size_t)snprintf(out + n, cap - n, "\t\t\t");
            patched += sets;
        }
        memcpy(out + n, "</model>", 8);
        n += 8;
        at = end + 8;
    }
    size_t rest = strlen(at);
    if (n + rest + 1 > cap) { free(out); return; }
    memcpy(out + n, at, rest + 1);
    n += rest;
    free(g_catalogue);
    g_catalogue = out;
    g_catalogue_n = n;
    fprintf(stderr, "[CLOTHING] parts catalogue: %d texture set(s) listed\n", patched);
}

static int read_parts(const char *path)
{
    FILE *f = fopen(path, "rb");
    char line[512];
    if (!f) return 0;
    if (!fgets(line, sizeof line, f) || strncmp(line, "clothing-parts-1", 16)) { fclose(f); return 0; }
    while (fgets(line, sizeof line, f)) {
        char *fields[6];
        line[strcspn(line, "\r\n")] = 0;
        if (split_tabs(line, fields, 6) != 4) continue;
        Item *it = item_by_key(fields[0]);
        uint32_t model = (uint32_t)strtoul(fields[2], NULL, 10);
        if (!it || it->nmodels >= CLOTHING_MAX_FITS || strlen(fields[3]) != 3 || model > 9999) continue;
        it->category = (uint32_t)strtoul(fields[1], NULL, 10);
        snprintf(it->base_variant, sizeof it->base_variant, "%s", fields[3]);
        it->models[it->nmodels++] = model;
    }
    fclose(f);
    return 1;
}

/* Rename one item's files from the compiled code to its chosen one (same length: in place for
 * names; thumbnails carry their own name inside and are decoded, renamed and stored again). */
static int rename_member(PcBigMember *m, int screens)
{
    for (int i = 0; i < g_count; i++) {
        const Item *it = &g_items[i];
        if (!strcmp(it->variant, it->compiled)) continue;
        char from[96], to[96];
        if (screens) {
            snprintf(from, sizeof from, "V2TN_%03u_%04u_%s_", it->category, it->models[0], it->compiled);
            snprintf(to, sizeof to, "V2TN_%03u_%04u_%s_", it->category, it->models[0], it->variant);
            char *at = strstr(m->name, from);
            if (!at) continue;
            memcpy(at, to, strlen(to));
            uint8_t *plain = NULL, *stored = NULL;
            size_t plain_n = 0, stored_n = 0;
            if (pc_refpack_is(m->data, m->size)) {
                if (!pc_refpack_decode(m->data, m->size, &plain, &plain_n)) return 0;
            } else {
                plain = (uint8_t *)malloc(m->size);
                if (!plain) return 0;
                memcpy(plain, m->data, m->size);
                plain_n = m->size;
            }
            size_t len = strlen(from);
            for (size_t k = 0; k + len <= plain_n; k++)
                if (!memcmp(plain + k, from, len)) memcpy(plain + k, to, len);
            int ok = pc_refpack_store(plain, plain_n, &stored, &stored_n);
            free(plain);
            if (!ok) return 0;
            free(m->owned);
            m->owned = stored;
            m->data = stored;
            m->size = stored_n;
            return 1;
        }
        for (int k = 0; k < it->nmodels; k++) {
            snprintf(from, sizeof from, "V2CP_%03u_%04u_%s_", it->category, it->models[k], it->compiled);
            if (!has_prefix_ci(m->name, from)) continue;
            memcpy(m->name + strlen(from) - 4, it->variant, 3);
            return 1;
        }
    }
    return 1;
}

static int serve_archive(int slot, const char *game_dir, const char *cache)
{
    const char *relative = k_served[slot], *add_name = k_add[slot], *served_name = strrchr(k_served[slot], '/') + 1;
    char source[PATH_MAX_LEN], add_path[PATH_MAX_LEN], parts_path[PATH_MAX_LEN], served[PATH_MAX_LEN];
    uint8_t *base = NULL, *add = NULL, *out = NULL, *built = NULL, *stored = NULL;
    size_t base_n = 0, add_n = 0, out_n = 0, built_n = 0, stored_n = 0;
    PcBigMember *members = NULL;
    int ok = 0, count = 0;
    char key[3 * PATH_MAX_LEN + sizeof g_codes], key_path[PATH_MAX_LEN + 8], stamp_source[64], stamp_add[64], stamp_parts[64];
    /* The catalogue goes into both archives that hold it (v2cp_0 and v2cp_3). */
    int catalogue = g_catalogue && (slot == 1 || slot == 4);
    snprintf(add_path, sizeof add_path, "%s" HOST_SEP "%s", cache, add_name);
    snprintf(parts_path, sizeof parts_path, "%s" HOST_SEP "parts-add.txt", cache);
    file_stamp(add_path, stamp_add, sizeof stamp_add);
    file_stamp(parts_path, stamp_parts, sizeof stamp_parts);
    int have_add = stamp_add[0] != '-' && strncmp(stamp_add, "0:", 2);
    if (!have_add && !catalogue) return 1;                      /* nothing to add: the game's file stays */
    if (!source_file(game_dir, relative, source, sizeof source)) goto done;
    /* The merged copy is reused while its inputs are the same files (screens.viv is ~96 MB). */
    snprintf(served, sizeof served, "%s" HOST_SEP "served" HOST_SEP "%s", cache, served_name);
    snprintf(key_path, sizeof key_path, "%s.key", served);
    file_stamp(source, stamp_source, sizeof stamp_source);
    snprintf(key, sizeof key, "clothing-served-2\n%s\n%s\n%s\n%s\n%s\n", source, stamp_source, have_add ? stamp_add : "-",
             catalogue ? stamp_parts : "-", g_codes);
    {
        uint8_t *old = NULL;
        size_t old_n = 0;
        char served_stamp[64];
        file_stamp(served, served_stamp, sizeof served_stamp);
        int same = served_stamp[0] != '-' && read_all(key_path, &old, &old_n) && old_n == strlen(key) && !memcmp(old, key, old_n);
        free(old);
        if (same) {
            snprintf(g_served[slot], sizeof g_served[slot], "%s", served);
            fprintf(stderr, "[CLOTHING] %s: the merged copy is current\n", relative);
            return 1;
        }
    }
    if (have_add) {
        if (!read_all(add_path, &add, &add_n)) goto done;
        count = pc_big_members(add, add_n, &members);
        if (count < 0) { fprintf(stderr, "[CLOTHING] %s: %s\n", add_name, pc_big_error()); goto done; }
    }
    if (catalogue) {
        PcBigMember *grown = (PcBigMember *)realloc(members, ((size_t)count + 1) * sizeof *members);
        if (!grown || !pc_refpack_store((const uint8_t *)g_catalogue, g_catalogue_n, &stored, &stored_n)) { free(grown ? grown : members); members = NULL; goto done; }
        members = grown;
        memset(&members[count], 0, sizeof members[count]);
        snprintf(members[count].name, sizeof members[count].name, "%s", PARTS_NAME);
        members[count].data = stored;
        members[count].size = stored_n;
        count++;
    }
    for (int i = 0; i < count; i++)
        if (!rename_member(&members[i], slot == 5)) { fprintf(stderr, "[CLOTHING] %s: cannot rename %s\n", add_name, members[i].name); goto done; }
    if (pc_big_build(members, count, &built, &built_n) < 0) { fprintf(stderr, "[CLOTHING] %s: %s\n", add_name, pc_big_error()); goto done; }
    if (!read_all(source, &base, &base_n)) {
        fprintf(stderr, "[CLOTHING] cannot read %s\n", source);
        goto done;
    }
    /* The creator's parts catalogue is the one file an item set changes rather than adds. */
    static const char *const replaceable[] = { PARTS_NAME, NULL };
    int added = pc_big_append(base, base_n, built, built_n, replaceable, &out, &out_n);
    if (added < 0) { fprintf(stderr, "[CLOTHING] %s not extended (%s)\n", relative, pc_big_error()); goto done; }
    remove(key_path);
    if (!write_if_changed(served, out, out_n)) { fprintf(stderr, "[CLOTHING] cannot write %s\n", served); goto done; }
    write_if_changed(key_path, (const uint8_t *)key, strlen(key));
    snprintf(g_served[slot], sizeof g_served[slot], "%s", served);
    fprintf(stderr, "[CLOTHING] %s: %d file(s) added or replaced\n", relative, added);
    ok = 1;
done:
    for (int i = 0; i < count && members; i++) if (members[i].owned) free(members[i].owned);
    free(members);
    free(stored);
    free(built);
    free(base);
    free(add);
    free(out);
    return ok;
}

/* Read what the chain serves before us: the archives' names and the parts catalogue. */
static void read_chain(const char *game_dir)
{
    char source[PATH_MAX_LEN];
    for (int slot = 1; slot < SERVED; slot++) {
        names_free(&g_names[slot]);
        if (source_file(game_dir, k_served[slot], source, sizeof source)) read_names(source, &g_names[slot]);
    }
    free(g_catalogue);
    g_catalogue = NULL;
    uint8_t *text = NULL;
    size_t n = 0;
    /* v2cp_3's copy, the one the creator reads (the last archive opened); v2cp_0 holds the same. */
    if (source_file(game_dir, k_served[4], source, sizeof source) && read_member(source, PARTS_NAME, &text, &n)) {
        char *t = (char *)realloc(text, n + 1);
        if (t) { t[n] = 0; g_catalogue = t; g_catalogue_n = n; }
        else free(text);
    }
}

void clothing_start(const char *data_root, const char *game_dir)
{
    char cache[PATH_MAX_LEN], items[PATH_MAX_LEN], parts[PATH_MAX_LEN];
    const char *override = getenv("RECOMP_CLOTHING_CACHE");
    g_trace = env_on("RECOMP_CLOTHING_TRACE");
    g_probe = env_on("RECOMP_CLOTHING_PROBE");
    if (override && *override) snprintf(cache, sizeof cache, "%s", override);
    else if (data_root && *data_root) snprintf(cache, sizeof cache, "%s" HOST_SEP "cache" HOST_SEP "clothing", data_root);
    else return;
    snprintf(items, sizeof items, "%s" HOST_SEP "items.txt", cache);
    snprintf(parts, sizeof parts, "%s" HOST_SEP "parts-add.txt", cache);
    if (data_root && *data_root)
        snprintf(g_state_dir, sizeof g_state_dir, "%s" HOST_SEP "clothing-state", data_root);
    if (!read_items(items)) return;
    g_previous_redirect = g_xbox_game_file_redirect;
    read_parts(parts);
    read_chain(game_dir);
    choose_codes();
    patch_catalogue();
    int ok = g_count > 0 && serve_database(game_dir, cache);
    for (int slot = 1; ok && slot < SERVED; slot++) ok = serve_archive(slot, game_dir, cache);
    for (int slot = 1; slot < SERVED; slot++) names_free(&g_names[slot]);
    free(g_catalogue);
    g_catalogue = NULL;
    if (!ok) {
        memset(g_served, 0, sizeof g_served);
        g_count = 0;
        g_digest[0] = 0;
        fprintf(stderr, "[CLOTHING] custom clothing is off for this run\n");
        return;
    }
    for (uint32_t s = 0; s < SLOTS; s++) {
        g_state[s] = (uint8_t *)calloc(g_states ? g_states : 1, 1);
        if (!g_state[s]) { g_count = 0; return; }
        for (int i = 0; i < g_count; i++)
            memset(g_state[s] + g_items[i].first, strcmp(g_items[i].avail, "shop") ? STATE_OWNED : STATE_UNLOCKED,
                   g_items[i].colours);
    }
    g_xbox_game_file_redirect = clothing_redirect;
    g_active = 1;
    fprintf(stderr, "[CLOTHING] %d custom item(s) from %s; Clothing rows %u retail + %d, table rank %u; set digest %s\n",
            g_count, cache, g_retail_rows, g_count, g_table_rank, g_digest[0] ? g_digest : "(none)");
    for (int i = 0; i < g_count; i++)
        fprintf(stderr, "[CLOTHING]   %s: \"%s\" on %s, set %s, %u colour(s), %s, row %u\n", g_items[i].key,
                g_items[i].name, g_items[i].base, g_items[i].variant, g_items[i].colours, g_items[i].avail, g_items[i].rank);
}

/* ---- for forks: the enabled set and retail handles ----------------------------------------------- */

const char *clothing_set_digest(void) { return g_active ? g_digest : ""; }

static Item *item_of(uint32_t handle);

uint32_t clothing_base_handle(uint32_t handle)
{
    const Item *it = item_of(handle & 0xFF00FFFFu);
    return it ? (g_table_rank << 24) | (handle & 0x00FF0000u) | it->base_rank : handle;
}

void clothing_retail_parts(const uint32_t *parts, uint32_t *out, int count)
{
    for (int i = 0; i < count; i++) out[i] = clothing_base_handle(parts[i]);
}

/* ---- the state sets ------------------------------------------------------------------------------ */

static uint32_t profiles(void)
{
    uint32_t data = MEM32(0x002FB148u + 0x18u * 4u);
    return data ? MEM32(data + 4) : 0;
}

/* The item of a record handle of an added row, or NULL. */
static Item *item_of(uint32_t handle)
{
    if (!g_active || (handle >> 24) != g_table_rank) return NULL;
    uint32_t rank = handle & 0xFFFFu;
    if (rank < g_retail_rows) return NULL;
    for (int i = 0; i < g_count; i++) if (g_items[i].rank == rank) return &g_items[i];
    return NULL;
}

static uint8_t *slot_states(uint32_t set)
{
    uint32_t cur = MEM32(set + 0x4C);
    int slot = cur ? (int)MEM32(cur) : -1;
    if (slot < 0 || slot >= (int)SLOTS) slot = 0;
    return g_state[slot];
}

void clothing_after_build(uint32_t set)
{
    if (!g_active) return;
    uint32_t keys = MEM32(set + 4), count = MEM32(set + 8), kept = 0;
    if (!keys || count > 100000) return;
    for (uint32_t i = 0; i < count; i++) {
        uint32_t key = MEM32(keys + i * 4);
        if (item_of(key & 0xFF00FFFFu)) continue;
        MEM32(keys + kept * 4) = key;
        kept++;
    }
    if (kept != count) {
        MEM32(set + 8) = kept;
        fprintf(stderr, "[CLOTHING] state set %08X: %u retail keys kept, %u added ones answered here\n", set, kept, count - kept);
    }
}

int clothing_set_call(int op, uint32_t set, uint32_t a1, uint32_t a2, uint32_t a3, uint32_t *result)
{
    Item *it = item_of(a1 & 0xFF00FFFFu);
    if (!it) return 0;
    uint8_t *st = slot_states(set);
    uint32_t colour = (a1 >> 16) & 0xFFu;
    uint8_t *one = colour < it->colours ? st + it->first + colour : NULL;
    *result = 0;
    switch (op) {
    case CLOTHING_GET: *result = one ? *one : 0xFFFFFFFFu; break;
    case CLOTHING_SET: if (one) *one = (uint8_t)(a2 & 3u); break;
    case CLOTHING_OR: if (one) *one |= (uint8_t)(a2 & 3u); break;
    case CLOTHING_CLEAR: if (one) *one &= (uint8_t)~(a2 & 3u); break;
    case CLOTHING_OR_ALL: for (uint32_t c = 0; c < it->colours; c++) st[it->first + c] |= (uint8_t)(a3 & 3u); break;
    case CLOTHING_ANY: for (uint32_t c = 0; c < it->colours; c++) *result |= st[it->first + c]; break;
    default: return 0;
    }
    if (g_trace) {
        static unsigned traced;
        if (traced++ < 400)
            fprintf(stderr, "[CLOTHING] set %08X op %d key %08X (%s colour %u) -> %u\n", set, op, a1, it->key, colour, *result);
    }
    return 1;
}

void clothing_set_all(uint32_t set, uint32_t state)
{
    if (!g_active || set != profiles() + SET_CLOTHING) return;
    uint8_t *st = slot_states(set);
    memset(st, (int)(state & 3u), g_states);
}

/* ---- names --------------------------------------------------------------------------------------- */

uint32_t clothing_localized(uint32_t key, uint32_t native_value)
{
    if (native_value || !g_active) return native_value;
    for (int i = 0; i < g_count; i++) {
        if (g_items[i].text_hash != key) continue;
        if (!g_name_pool) {
            uint32_t size = 0;
            for (int j = 0; j < g_count; j++) { g_name_offset[j] = size; size += (uint32_t)(strlen(g_items[j].name) + 1) * 2; }
            uint32_t args[3] = { size, 0x0029D4B4u, 0 };
            g_name_pool = guest_call(sub_00029680, 0, 3, args);
            if (!g_name_pool) return native_value;
            for (int j = 0; j < g_count; j++) {
                const unsigned char *s = (const unsigned char *)g_items[j].name;
                uint32_t at = g_name_pool + g_name_offset[j];
                for (; *s; s++, at += 2) MEM16(at) = (uint16_t)(*s < 0x80 ? *s : '?');
                MEM16(at) = 0;
            }
        }
        return g_name_pool + g_name_offset[i];
    }
    return native_value;
}

/* ---- profile load and front-end calls ------------------------------------------------------------ */

static void probe(const char *when)
{
    uint32_t manager = profiles();
    fprintf(stderr, "[CLOTHING] probe %s profiles=%08X slot=%d\n", when, manager,
            manager ? (int)MEM32(manager + SLOT_INDEX) : -2);
    if (!manager) return;
    uint32_t s = manager + SET_CLOTHING;
    fprintf(stderr, "[CLOTHING] probe clothing set vt=%08X keys=%08X count=%u cur=%d\n",
            MEM32(s), MEM32(s + 4), MEM32(s + 8), MEM32(s + 0x4C) ? (int)MEM32(MEM32(s + 0x4C)) : -2);
    int slot = (int)MEM32(manager + SLOT_INDEX);
    if (slot < 0 || slot >= (int)SLOTS) return;
    uint32_t row = manager + (uint32_t)slot * 0x5950u + 0x1788u;
    for (uint32_t at = 0; at + 4 <= 0x5904u; at += 4) {
        uint32_t w = MEM32(row + at);
        if ((w >> 24) == g_table_rank && (w & 0xFFFFu) < g_rows && ((w >> 16) & 0xFFu) < 32)
            fprintf(stderr, "[CLOTHING] probe row+%04X = %08X%s\n", at, w, item_of(w & 0xFF00FFFFu) ? " (added item)" : "");
    }
}

void clothing_after_load(uint32_t loader)
{
    (void)loader;
    if (g_probe) probe("load");
}

/* ---- saves stay retail ---------------------------------------------------------------------------
 *
 * A save holds the profile row as it is in memory, so an added item worn would be saved as a
 * handle of a row only this pack set has. While the game copies the row into a save
 * (sub_000D23B0), every added item in the two part arrays is its base item instead (same
 * colour); right after, the row is put back. What was swapped goes to the profile's file in
 * <data>/clothing-state, with the base handle it was saved as; when the row is loaded again and
 * still holds that base handle there, the added item comes back, if its pack is enabled. With
 * the pack off, the hero wears the base item and the save is one the original game reads.
 */

#define MAX_SWAPS 16
static struct { uint32_t at, custom; } g_swaps[MAX_SWAPS];
static int g_nswaps;
static int g_restore_pending;             /* a row was loaded: restore before the next front-end call */

static Item *item_by_key(const char *key)
{
    for (int i = 0; i < g_count; i++) if (!strcmp(g_items[i].key, key)) return &g_items[i];
    return NULL;
}

static uint32_t base_handle(const Item *it, uint32_t handle)
{
    return (g_table_rank << 24) | (handle & 0x00FF0000u) | it->base_rank;
}

static void row_profile(uint32_t row, char *out, size_t size)
{
    size_t n = 0;
    for (uint32_t i = 0; i < 16 && n + 3 < size; i++) {
        uint8_t c = MEM8(row + i);
        if (!c) break;
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_')
            out[n++] = (char)c;
        else
            n += (size_t)snprintf(out + n, size - n, "%02X", c);
    }
    out[n] = 0;
    if (!n) snprintf(out, size, "profile");
}

static void state_path(uint32_t row, char *out, size_t size)
{
    char name[64];
    row_profile(row, name, sizeof name);
    snprintf(out, size, "%s" HOST_SEP "%s.txt", g_state_dir, name);
}

/* sub_000D23B0 (name, row): about to copy a profile row into a save. */
void clothing_before_save(uint32_t row)
{
    g_nswaps = 0;
    if (!g_active || !row) return;
    char path[PATH_MAX_LEN], out[16384], line[512];
    size_t n = 0;
    int lines = 0;
    uint32_t manager = profiles();
    int slot = manager && row >= manager + ROW_OFFSET ? (int)((row - manager - ROW_OFFSET) / SLOT_STRIDE) : -1;
    n += (size_t)snprintf(out + n, sizeof out - n, "clothing-state-1\n");
    for (int a = 0; a < 2; a++)
        for (uint32_t part = PART_FIRST; part <= PART_LAST; part++) {
            uint32_t at = k_part_arrays[a] + part * 4u, w = MEM32(row + at);
            Item *it = item_of(w & 0xFF00FFFFu);
            if (!it || g_nswaps >= MAX_SWAPS) continue;
            uint32_t saved = base_handle(it, w);
            g_swaps[g_nswaps].at = row + at;
            g_swaps[g_nswaps].custom = w;
            g_nswaps++;
            MEM32(row + at) = saved;
            n += (size_t)snprintf(out + n, sizeof out - n, "worn\t%04X\t%08X\t%s\t%u\n", at, saved, it->key, (w >> 16) & 0xFFu);
            lines++;
        }
    /* Bought (or otherwise changed) states of the enabled items, for this profile slot. */
    if (slot >= 0 && slot < (int)SLOTS)
        for (int i = 0; i < g_count; i++) {
            uint8_t initial = strcmp(g_items[i].avail, "shop") ? STATE_OWNED : STATE_UNLOCKED;
            for (uint32_t c = 0; c < g_items[i].colours && n + 200 < sizeof out; c++)
                if (g_state[slot][g_items[i].first + c] != initial) {
                    n += (size_t)snprintf(out + n, sizeof out - n, "state\t%s\t%u\t%u\n", g_items[i].key, c,
                                          g_state[slot][g_items[i].first + c]);
                    lines++;
                }
        }
    if (!g_state_dir[0]) return;
    state_path(row, path, sizeof path);
    /* Lines of items whose pack is not enabled now stay, so enabling it again brings them back
     * (a worn one only while the save still holds its base item there). */
    FILE *old = fopen(path, "rb");
    if (old) {
        if (fgets(line, sizeof line, old) && !strncmp(line, "clothing-state-1", 16))
            while (fgets(line, sizeof line, old) && n + strlen(line) + 2 < sizeof out) {
                char copy[512], *fields[6];
                snprintf(copy, sizeof copy, "%s", line);
                copy[strcspn(copy, "\r\n")] = 0;
                int nf = split_tabs(copy, fields, 6);
                const char *key = !strcmp(fields[0], "worn") && nf == 5 ? fields[3]
                                : !strcmp(fields[0], "state") && nf == 4 ? fields[1] : NULL;
                if (!key || item_by_key(key)) continue;
                uint32_t at = (uint32_t)strtoul(nf == 5 ? fields[1] : "0", NULL, 16) & 0xFFFCu;
                if (nf == 5 && (at >= ROW_BYTES || MEM32(row + at) != (uint32_t)strtoul(fields[2], NULL, 16)))
                    continue;
                n += (size_t)snprintf(out + n, sizeof out - n, "%s", line);
                if (line[strlen(line) - 1] != '\n') out[n++] = '\n';
                lines++;
            }
        fclose(old);
    }
    if (lines) {
        make_dirs(path);
        if (!write_if_changed(path, (const uint8_t *)out, n))
            fprintf(stderr, "[CLOTHING] cannot write %s\n", path);
    } else {
        remove(path);   /* nothing added is worn or bought: an earlier file no longer describes this save */
    }
    if (g_nswaps)
        fprintf(stderr, "[CLOTHING] save: %d added item(s) saved as their base items\n", g_nswaps);
}

void clothing_after_save(void)
{
    for (int i = 0; i < g_nswaps; i++) MEM32(g_swaps[i].at) = g_swaps[i].custom;
    g_nswaps = 0;
}

/* sub_000156D0: a profile row was loaded from a save. */
void clothing_after_row_load(void) { g_restore_pending = 1; }

static void restore_current(void)
{
    uint32_t manager = profiles();
    if (!manager || !g_state_dir[0]) return;
    int slot = (int)MEM32(manager + SLOT_INDEX);
    if (slot < 0 || slot >= (int)SLOTS) return;
    g_restore_pending = 0;
    /* A loaded profile starts from the items' initial states; its file says what changed. */
    if (g_active)
        for (int i = 0; i < g_count; i++)
            memset(g_state[slot] + g_items[i].first, strcmp(g_items[i].avail, "shop") ? STATE_OWNED : STATE_UNLOCKED,
                   g_items[i].colours);
    uint32_t row = manager + (uint32_t)slot * SLOT_STRIDE + ROW_OFFSET;
    char path[PATH_MAX_LEN], line[512];
    state_path(row, path, sizeof path);
    FILE *f = fopen(path, "rb");
    if (!f) return;
    int restored = 0, kept = 0;
    if (fgets(line, sizeof line, f) && !strncmp(line, "clothing-state-1", 16)) {
        while (fgets(line, sizeof line, f)) {
            char *fields[6];
            line[strcspn(line, "\r\n")] = 0;
            int nf = split_tabs(line, fields, 6);
            if (nf == 4 && !strcmp(fields[0], "state")) {
                Item *it = g_active ? item_by_key(fields[1]) : NULL;
                uint32_t c = (uint32_t)strtoul(fields[2], NULL, 10);
                if (it && c < it->colours) g_state[slot][it->first + c] = (uint8_t)(strtoul(fields[3], NULL, 10) & 3u);
                continue;
            }
            if (nf != 5 || strcmp(fields[0], "worn")) continue;
            uint32_t at = (uint32_t)strtoul(fields[1], NULL, 16), saved = (uint32_t)strtoul(fields[2], NULL, 16);
            uint32_t colour = (uint32_t)strtoul(fields[4], NULL, 10);
            int known = 0;
            for (int a = 0; a < 2; a++)
                if (at >= k_part_arrays[a] + PART_FIRST * 4u && at <= k_part_arrays[a] + PART_LAST * 4u && !(at & 3u)) known = 1;
            if (!known || MEM32(row + at) != saved) continue;   /* changed since: the save decides */
            Item *it = item_by_key(fields[3]);
            if (!it || !g_active || colour >= it->colours || base_handle(it, colour << 16) != saved) { kept++; continue; }
            MEM32(row + at) = (g_table_rank << 24) | (colour << 16) | it->rank;
            restored++;
        }
    }
    fclose(f);
    if (restored || kept)
        fprintf(stderr, "[CLOTHING] profile slot %d: %d added item(s) worn again, %d left as their base items (pack not enabled)\n",
                slot, restored, kept);
}

void clothing_on_funccall(const char *text)
{
    if (g_restore_pending) restore_current();
    if (g_probe && (!strncmp(text, "Shops.", 6) || !strncmp(text, "MemCard.", 8))) probe(text);
}
