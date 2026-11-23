/* Merge two BIG archives (.viv): src/hooks/pc_big.c. */
#ifndef DEFJAM_PC_BIG_H
#define DEFJAM_PC_BIG_H
#include <stddef.h>
#include <stdint.h>

/*
 * A copy of `base` with every member of `add` appended (malloc'd in *out). The base's
 * directory order, footer, payload bytes and payload alignment are kept (its payloads move
 * by a multiple of 4096 to make room for the longer directory). A member of `add` whose name
 * the base already has (ignoring case) replaces it only when it is named in `replaceable`
 * (a NULL-terminated list, or NULL); otherwise the merge is refused.
 * Returns the number of members added or replaced, or -1 with a reason in pc_big_error().
 */
int pc_big_append(const uint8_t *base, size_t base_n, const uint8_t *add, size_t add_n,
                  const char *const *replaceable, uint8_t **out, size_t *out_n);

const char *pc_big_error(void);

/* One member of an archive: its name and bytes (borrowed from the archive's buffer, or owned when
 * `owned` is set by the caller). */
typedef struct {
    char name[256];
    const uint8_t *data;
    size_t size;
    uint8_t *owned;
} PcBigMember;

/* The members of a BIG archive, in directory order (malloc'd array in *out; free it). Returns the
 * count, or -1 with a reason in pc_big_error(). */
int pc_big_members(const uint8_t *p, size_t n, PcBigMember **out);
const PcBigMember *pc_big_find(const PcBigMember *m, int count, const char *name);   /* ignoring case */

/* A BIGF archive of these members, in this order (malloc'd in *out). Returns the count or -1. */
int pc_big_build(const PcBigMember *m, int count, uint8_t **out, size_t *out_n);

/* RefPack, as the game reads it: decode (1/0), and literal-only store (1/0). Results are malloc'd. */
int pc_refpack_is(const uint8_t *p, size_t n);
int pc_refpack_decode(const uint8_t *src, size_t n, uint8_t **out, size_t *out_n);
int pc_refpack_store(const uint8_t *data, size_t n, uint8_t **out, size_t *out_n);
#endif
