#ifndef DEFJAM_SAVE_ACTIVITY_H
#define DEFJAM_SAVE_ACTIVITY_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Save files the game is writing (src/hooks/save_activity.c). Fed by the write and
 * close wrappers in src/recomp_manual.c; read by the window thread on close. */
void save_activity_write(uint32_t handle);
void save_activity_close(uint32_t handle);
int save_activity_busy(void);
int save_activity_exit_requested(void);
/* Mark the exit as requested and wait until no save is in progress, at most
 * timeout_ms. Returns 1 when idle, 0 on timeout. Call from the window thread. */
int save_activity_wait_idle(unsigned timeout_ms);
/* Ask the game window to close, as the player's close button does (test control). */
void host_request_close(void);

#ifdef __cplusplus
}
#endif
#endif
