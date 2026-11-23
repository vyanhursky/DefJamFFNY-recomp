/* Picture options: brightness and the venue vignette. See picture.c. */
#ifndef DEFJAM_PICTURE_H
#define DEFJAM_PICTURE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* The title's gamma ramp (256 bytes each of red, green, blue), or NULL to apply only the
 * brightness (the title's ramp is off). Hands the composed ramp to the presentation pass. */
void picture_title_ramp(const uint8_t *ramp);

/* Read [display] brightness, vignette, vignette_strength, color_tint and scratches; call at
 * start-up and on a change. */
void picture_apply_settings(void);

typedef struct PictureOptions {
    int brightness, color_tint, vignette, vignette_strength, scratches;
} PictureOptions;
/* Temporary runtime-only look. End restores the exact entry options; no INI
 * values are changed, and ordinary settings application cannot replace it. */
void picture_photo_begin(PictureOptions *entry);
void picture_photo_set(const PictureOptions *options);
void picture_photo_current(PictureOptions *options);
void picture_photo_end(void);

/* Guest hooks (src/recomp_manual.c). */
void picture_tint_draw_enter(void);
void picture_quad_color_enter(void);
void picture_postfx_enter(void);
int picture_scratches_on(void);

#ifdef __cplusplus
}
#endif

#endif
