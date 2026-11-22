#ifndef DEFJAM_PHOTO_MODE_H
#define DEFJAM_PHOTO_MODE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int photo_mode_active(void);
/* Guest-thread boundaries: a fight screen's tick, and immediately before its draw. */
int photo_mode_tick(uint32_t screen);
int photo_mode_freeze(uint32_t screen);
void photo_mode_draw(uint32_t screen);
void photo_mode_cancel(void);
#ifdef __cplusplus
}
#endif
#endif
