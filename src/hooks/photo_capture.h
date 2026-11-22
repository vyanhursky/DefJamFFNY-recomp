#ifndef DEFJAM_PHOTO_CAPTURE_H
#define DEFJAM_PHOTO_CAPTURE_H
#ifdef __cplusplus
extern "C" {
#endif
int photo_capture_request(void);
int photo_capture_busy(void);
int photo_capture_waiting(void);
void photo_capture_cancel_pending(void);
/* GPU executor only: read a completed game target before host overlays. */
void photo_capture_frame(void *device);
#ifdef __cplusplus
}
#endif
#endif
