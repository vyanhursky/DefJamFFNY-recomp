#ifndef DEFJAM_FIGHTER_PALETTE_CONTEXT_H
#define DEFJAM_FIGHTER_PALETTE_CONTEXT_H
#include <stdint.h>
typedef struct FighterPaletteScope { uint32_t wrapper, begin, bytes; } FighterPaletteScope;
FighterPaletteScope defjam_fighter_palette_begin(uint32_t wrapper);
void defjam_fighter_palette_input(uint32_t descriptor);
void defjam_fighter_palette_end(FighterPaletteScope previous, int success);
void defjam_fighter_palette_release(uint32_t wrapper);
/* Validate actual borrowed palette storage, rather than guessing its size from
 * a wrapper or an evaluator key count. Returns zero for unobserved lifetimes. */
int defjam_fighter_palette_check(uint32_t wrapper, uint32_t root, uint32_t bones,
                                const uint32_t required[2]);
#endif
