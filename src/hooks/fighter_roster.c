#include "fighter_roster.h"
#include <string.h>

uint32_t fighter_roster_partition(uint32_t *items, const uint32_t *name_keys, uint32_t count,
                                 uint32_t *scratch, const FighterNames *names) {
    uint32_t offset, length, retail = 0, custom = 0;
    for (uint32_t i = 0; i < count; ++i)
        if (!fighter_names_find(names, name_keys[i], &offset, &length)) scratch[retail++] = items[i];
    for (uint32_t i = 0; i < count; ++i)
        if (fighter_names_find(names, name_keys[i], &offset, &length)) scratch[retail + custom++] = items[i];
    if (count) memcpy(items, scratch, count * sizeof *items);
    return custom;
}
