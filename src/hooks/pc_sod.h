/* Append rows to one table of a SODB database (assets/djv2.sod): src/hooks/pc_sod.c. */
#ifndef DEFJAM_PC_SOD_H
#define DEFJAM_PC_SOD_H
#include <stddef.h>
#include <stdint.h>

#define PC_SOD_MAX_FIELDS 8

typedef struct {
    uint32_t word;          /* the field's word offset in the record */
    int is_string;          /* 1: text (interned, the record holds its string index); 0: integer */
    const char *text;
    uint32_t value;
} PcSodField;

typedef struct {
    const char *template_name;  /* an existing row to copy (its row name) */
    const char *name;           /* the new row's name; "~" + 7 characters are added so that row r of the
                                 * call hashes to the table's highest hash + 1 + r (a search if not free) */
    int nfields;
    PcSodField fields[PC_SOD_MAX_FIELDS];
} PcSodRow;

/*
 * Copy `in`, append `count` rows to table `table` and return the new database in *out
 * (malloc'd). Each new record is a byte copy of its template record (pointer fields keep
 * pointing at the template's lists), then gets its own row name and the given fields.
 * Retail rows keep their offsets, bytes and ranks: the added rows' names sort after every
 * existing name, so the game's record handles of the retail rows do not change.
 * names_out[i] (when given, 160 bytes each) receives row i's final name.
 * Returns 1, or 0 with a reason in pc_sod_error().
 */
int pc_sod_add_rows(const uint8_t *in, size_t n, const char *table, const PcSodRow *rows, int count,
                    uint8_t **out, size_t *out_n, char (*names_out)[160]);

/* Rank of a row (by name) in a table's name index, -1 when absent; and the table's rank in
 * the database directory (the high byte of the game's record handles), -1 when absent. */
int pc_sod_row_rank(const uint8_t *db, size_t n, const char *table, const char *row);
int pc_sod_table_rank(const uint8_t *db, size_t n, const char *table);
int pc_sod_row_count(const uint8_t *db, size_t n, const char *table);

/* The database's own string hash: djb2 over the bytes and the terminating NUL. */
uint32_t pc_sod_hash(const char *s);

/* "<prefix>~" plus 7 characters ('0'..'P') whose hash is exactly `target`, in out (prefix + 9
 * bytes). Returns 1 when it checks out. */
int pc_sod_name_for_hash(const char *prefix, uint32_t target, char *out, size_t size);

const char *pc_sod_error(void);
#endif
