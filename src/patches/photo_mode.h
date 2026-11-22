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
void photo_mode_render(uint32_t screen);
void photo_mode_clear(void);
void photo_mode_simulation_step(void);
/* Test-only selection of the engine's authored victory path. */
void photo_mode_result_boundary(void);
/* Guest root-render boundary; 1 when Photo Mode drew the frozen world itself. */
int photo_mode_frame(void);
typedef struct PhotoModeStatus {
    int active, panel, settings, row, speed, hud_hidden, thirds, centre, invert_y;
    float fov, roll, look_speed;
    char message[512];
} PhotoModeStatus;
void photo_mode_status(PhotoModeStatus *out);
void photo_mode_capture_result(const char *message);
int photo_mode_hide_hud(void);
int photo_mode_hide_panel(uint32_t object);
int photo_mode_hide_pause(uint32_t object);
void photo_mode_ui(void);
#ifdef __cplusplus
}
#endif
#endif
