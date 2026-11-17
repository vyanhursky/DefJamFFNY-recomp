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
#include <sys/stat.h>
#if defined(_WIN32)
#include <direct.h>
#else
#include <strings.h>
#define _stricmp strcasecmp
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
    uint32_t colours, price, text_hash, rank, base_rank, first;   /* first: its first state in g_state[slot] */
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
        if (split_tabs(line, fields, 8) != 7) continue;
        Item *it = &g_items[g_count];
        memset(it, 0, sizeof *it);
        if (strlen(fields[0]) >= sizeof it->key || strlen(fields[1]) >= sizeof it->base || strlen(fields[2]) != 3
            || strlen(fields[5]) >= sizeof it->avail || strlen(fields[6]) > CLOTHING_MAX_NAME || !fields[6][0]) continue;
        snprintf(it->key, sizeof it->key, "%s", fields[0]);
        snprintf(it->base, sizeof it->base, "%s", fields[1]);
        snprintf(it->variant, sizeof it->variant, "%s", fields[2]);
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

static int serve_archive(int slot, const char *game_dir, const char *cache)
{
    const char *relative = k_served[slot], *add_name = k_add[slot], *served_name = strrchr(k_served[slot], '/') + 1;
    char source[PATH_MAX_LEN], add_path[PATH_MAX_LEN], served[PATH_MAX_LEN];
    uint8_t *base = NULL, *add = NULL, *out = NULL;
    size_t base_n = 0, add_n = 0, out_n = 0;
    int ok = 0;
    snprintf(add_path, sizeof add_path, "%s" HOST_SEP "%s", cache, add_name);
    if (!read_all(add_path, &add, &add_n)) return 1;              /* nothing to add: the game's file stays */
    if (!source_file(game_dir, relative, source, sizeof source) || !read_all(source, &base, &base_n)) {
        fprintf(stderr, "[CLOTHING] cannot read %s\n", source);
        goto done;
    }
    /* The creator's parts catalogue is the one file an item set changes rather than adds. */
    static const char *const replaceable[] = { "createplayer_parts.xml", NULL };
    int added = pc_big_append(base, base_n, add, add_n, replaceable, &out, &out_n);
    if (added < 0) { fprintf(stderr, "[CLOTHING] %s not extended (%s)\n", relative, pc_big_error()); goto done; }
    snprintf(served, sizeof served, "%s" HOST_SEP "served" HOST_SEP "%s", cache, served_name);
    if (!write_if_changed(served, out, out_n)) { fprintf(stderr, "[CLOTHING] cannot write %s\n", served); goto done; }
    snprintf(g_served[slot], sizeof g_served[slot], "%s", served);
    fprintf(stderr, "[CLOTHING] %s: %d file(s) added\n", relative, added);
    ok = 1;
done:
    free(base);
    free(add);
    free(out);
    return ok;
}

void clothing_start(const char *data_root, const char *game_dir)
{
    char cache[PATH_MAX_LEN], items[PATH_MAX_LEN];
    const char *override = getenv("RECOMP_CLOTHING_CACHE");
    g_trace = env_on("RECOMP_CLOTHING_TRACE");
    g_probe = env_on("RECOMP_CLOTHING_PROBE");
    if (override && *override) snprintf(cache, sizeof cache, "%s", override);
    else if (data_root && *data_root) snprintf(cache, sizeof cache, "%s" HOST_SEP "cache" HOST_SEP "clothing", data_root);
    else return;
    snprintf(items, sizeof items, "%s" HOST_SEP "items.txt", cache);
    if (data_root && *data_root)
        snprintf(g_state_dir, sizeof g_state_dir, "%s" HOST_SEP "clothing-state", data_root);
    if (!read_items(items)) return;
    g_previous_redirect = g_xbox_game_file_redirect;
    int ok = serve_database(game_dir, cache);
    for (int slot = 1; ok && slot < SERVED; slot++) ok = serve_archive(slot, game_dir, cache);
    if (!ok) {
        memset(g_served, 0, sizeof g_served);
        g_count = 0;
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
    fprintf(stderr, "[CLOTHING] %d custom item(s) from %s; Clothing rows %u retail + %d, table rank %u\n",
            g_count, cache, g_retail_rows, g_count, g_table_rank);
    for (int i = 0; i < g_count; i++)
        fprintf(stderr, "[CLOTHING]   %s: \"%s\" on %s, set %s, %u colour(s), %s, row %u\n", g_items[i].key,
                g_items[i].name, g_items[i].base, g_items[i].variant, g_items[i].colours, g_items[i].avail, g_items[i].rank);
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
    char path[PATH_MAX_LEN];
    FILE *f = NULL;
    for (int a = 0; a < 2; a++)
        for (uint32_t part = PART_FIRST; part <= PART_LAST; part++) {
            uint32_t at = k_part_arrays[a] + part * 4u, w = MEM32(row + at);
            Item *it = item_of(w & 0xFF00FFFFu);
            if (!it || g_nswaps >= MAX_SWAPS) continue;
            if (!f && g_state_dir[0]) {
                state_path(row, path, sizeof path);
                make_dirs(path);
                f = fopen(path, "wb");
                if (f) fprintf(f, "clothing-state-1\n");
            }
            uint32_t saved = base_handle(it, w);
            g_swaps[g_nswaps].at = row + at;
            g_swaps[g_nswaps].custom = w;
            g_nswaps++;
            MEM32(row + at) = saved;
            if (f) fprintf(f, "worn\t%04X\t%08X\t%s\t%u\n", at, saved, it->key, (w >> 16) & 0xFFu);
        }
    if (f) fclose(f);
    else if (g_state_dir[0]) {
        /* Nothing added is worn: an earlier file no longer describes this save. */
        state_path(row, path, sizeof path);
        remove(path);
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
            if (split_tabs(line, fields, 6) != 5 || strcmp(fields[0], "worn")) continue;
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
