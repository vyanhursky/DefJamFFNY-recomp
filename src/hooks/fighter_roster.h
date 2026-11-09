#ifndef DEFJAM_FIGHTER_ROSTER_H
#define DEFJAM_FIGHTER_ROSTER_H
#include "fighter_names.h"
/* Native list tokens are opaque snapshot-scoped handles, not symbol hashes or
 * selection/core IDs. The caller supplies separately resolved name hashes.
 * Keep both groups' relative order, including context-specific retail ordering.
 * scratch must have count entries and must not overlap items. */
uint32_t fighter_roster_partition(uint32_t *items, const uint32_t *name_keys, uint32_t count,
                                 uint32_t *scratch, const FighterNames *names);
#endif
