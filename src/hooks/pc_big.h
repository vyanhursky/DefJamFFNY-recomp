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
#endif
