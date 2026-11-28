/* PNG photos: bounded readback on the GPU thread, encoding and file IO on an
 * SDL worker. No guest functions or guest registers are used by either path. */
#define _CRT_SECURE_NO_WARNINGS
#include "host.h"
#include "photo_capture.h"
#include "patches/photo_mode.h"
#ifdef XBOXRECOMP_HAVE_SDL3
#include "d3d8_xbox.h"
#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define STB_IMAGE_WRITE_IMPLEMENTATION
#define STB_IMAGE_WRITE_STATIC
#include "stb/stb_image_write.h"

/* 0 idle, 1 waiting for clean frames, 2 copying, 3 encoding. */
static volatile LONG stage, warmup, sequence;
typedef struct PhotoJob {
    unsigned width, height;
    unsigned char *pixels;
    char filename[128];
} PhotoJob;
typedef struct PhotoWriter { SDL_IOStream *io; int ok; } PhotoWriter;

int photo_capture_busy(void) { return InterlockedCompareExchange(&stage, 0, 0) != 0; }
int photo_capture_waiting(void)
{
    LONG s = InterlockedCompareExchange(&stage, 0, 0);
    return s == 1 || s == 2;
}
void photo_capture_cancel_pending(void) { InterlockedCompareExchange(&stage, 0, 1); }
int photo_capture_request(void)
{
    if (photo_capture_busy()) return 0;
    /* Hold the composed pose while previously submitted frames drain. HUD is
     * suppressed during this interval even if it was enabled for preview. */
    InterlockedExchange(&warmup, 4);
    if (InterlockedCompareExchange(&stage, 1, 0) != 0) return 0;
    photo_mode_capture_result("Taking photo...");
    return 1;
}
static void write_png(void *context, void *data, int size)
{
    PhotoWriter *writer = (PhotoWriter *)context;
    if (writer->ok && SDL_WriteIO(writer->io, data, (size_t)size) != (size_t)size) writer->ok = 0;
}
static int SDLCALL save_photo(void *data)
{
    PhotoJob *job = (PhotoJob *)data;
    char directory[1536], path[2048], message[512];
    const char *override = getenv("RECOMP_PHOTO_DIR");
    const char *pictures = SDL_GetUserFolder(SDL_FOLDER_PICTURES);
    char *preferences = NULL;
    PhotoWriter writer = {NULL, 1};
    int ok = 0, n;
    if (override && *override) n = snprintf(directory, sizeof(directory), "%s", override);
    else if (pictures && *pictures) n = snprintf(directory, sizeof(directory), "%s/DefJamRecompiled", pictures);
    else {
        preferences = SDL_GetPrefPath("DefJamRecompiled", "DefJamRecompiled");
        directory[0] = 0;
        n = preferences ? snprintf(directory, sizeof(directory), "%sphotos", preferences) : -1;
    }
    path[0] = 0;
    if (n > 0 && n < (int)sizeof(directory) && SDL_CreateDirectory(directory)) {
        n = snprintf(path, sizeof(path), "%s/%s", directory, job->filename);
        if (n > 0 && n < (int)sizeof(path)) {
            SDL_PathInfo existing;
            if (SDL_GetPathInfo(path, &existing)) SDL_SetError("Photo name already exists");
            else writer.io = SDL_IOFromFile(path, "wb");
        }
        if (writer.io) {
            int encoded = stbi_write_png_to_func(write_png, &writer, (int)job->width, (int)job->height,
                                                4, job->pixels, (int)job->width * 4);
            int flushed = SDL_FlushIO(writer.io);
            int closed = SDL_CloseIO(writer.io);
            ok = encoded && writer.ok && flushed && closed;
            if (!ok) SDL_RemovePath(path); /* this job's new, uniquely named partial file */
        }
    }
    if (ok) {
        snprintf(message, sizeof(message), "Saved %s", job->filename);
        fprintf(stderr, "[PHOTO] saved %ux%u PNG %s\n", job->width, job->height, path);
    } else {
        snprintf(message, sizeof(message), "Could not save photo: %.400s", SDL_GetError());
        fprintf(stderr, "[PHOTO] save failed: %s (%s)\n", message, path[0] ? path : directory);
    }
    SDL_free(preferences);
    free(job->pixels); free(job);
    photo_mode_capture_result(message);
    InterlockedExchange(&stage, 0);
    return 0;
}
void photo_capture_frame(void *device)
{
    IDirect3DDevice8 *dev = (IDirect3DDevice8 *)device;
    IDirect3DSurface8 *surface = NULL;
    D3DLOCKED_RECT locked;
    PhotoJob *job = NULL;
    SDL_Thread *worker;
    unsigned x, y, width, height;
    unsigned char gamma[3][256];
    int gamma_on;
    time_t stamp;
    struct tm local;
    extern unsigned d3d8_GetBackbufferWidth(void), d3d8_GetBackbufferHeight(void), d3d8_GetRenderScale(void);
    extern float d3d8_GetCanvasScaleX(void);
    extern unsigned char g_recomp_gamma[3][256];
    extern int g_recomp_gamma_on;
    if (InterlockedCompareExchange(&stage, 0, 0) != 1) return;
    if (InterlockedDecrement(&warmup) > 0) return;
    if (InterlockedCompareExchange(&stage, 2, 1) != 1) return;
    width = (unsigned)(d3d8_GetBackbufferWidth() * d3d8_GetCanvasScaleX() + 0.5f);
    height = d3d8_GetBackbufferHeight() * d3d8_GetRenderScale();
    if (!width || !height || width > 16384 || height > 16384 || (uint64_t)width * height > 32000000u) goto failed;
    if (FAILED(dev->lpVtbl->GetBackBuffer(dev, 0, 0, &surface)) || !surface) goto failed;
    memset(&locked, 0, sizeof(locked));
    if (FAILED(surface->lpVtbl->LockRect(surface, &locked, NULL, 0))) goto failed;
    job = (PhotoJob *)calloc(1, sizeof(*job));
    if (job) job->pixels = (unsigned char *)malloc((size_t)width * height * 4);
    if (!job || !job->pixels || !locked.pBits || locked.Pitch < (int)width * 4) {
        surface->lpVtbl->UnlockRect(surface); goto failed;
    }
    job->width = width; job->height = height;
    gamma_on = g_recomp_gamma_on;
    memcpy(gamma, g_recomp_gamma, sizeof(gamma));
    for (y = 0; y < height; y++) {
        const unsigned char *src = (const unsigned char *)locked.pBits + (size_t)y * locked.Pitch;
        unsigned char *dst = job->pixels + (size_t)y * width * 4;
        for (x = 0; x < width; x++) {
            dst[x*4] = gamma_on ? gamma[0][src[x*4]] : src[x*4];
            dst[x*4+1] = gamma_on ? gamma[1][src[x*4+1]] : src[x*4+1];
            dst[x*4+2] = gamma_on ? gamma[2][src[x*4+2]] : src[x*4+2];
            dst[x*4+3] = 255;
        }
    }
    surface->lpVtbl->UnlockRect(surface);
    surface->lpVtbl->Release(surface); surface = NULL;
    stamp = time(NULL);
#if defined(_WIN32)
    localtime_s(&local, &stamp);
#else
    localtime_r(&stamp, &local);
#endif
    snprintf(job->filename, sizeof(job->filename), "DefJam_%04d%02d%02d_%02d%02d%02d_%lu_%llu_%ld.png",
        local.tm_year+1900, local.tm_mon+1, local.tm_mday, local.tm_hour, local.tm_min, local.tm_sec,
        (unsigned long)GetCurrentProcessId(), (unsigned long long)GetTickCount64(), (long)InterlockedIncrement(&sequence));
    InterlockedExchange(&stage, 3);
    worker = SDL_CreateThread(save_photo, "Photo PNG", job);
    if (!worker) goto failed;
    SDL_DetachThread(worker);
    return;
failed:
    if (surface) surface->lpVtbl->Release(surface);
    if (job) { free(job->pixels); free(job); }
    photo_mode_capture_result("Could not capture photo. Try again.");
    fprintf(stderr, "[PHOTO] capture failed\n");
    InterlockedExchange(&stage, 0);
}
#else
/* Preserve custom XInput-only builds; standard builds include SDL. */
int photo_capture_busy(void) { return 0; }
int photo_capture_waiting(void) { return 0; }
void photo_capture_cancel_pending(void) {}
void photo_capture_frame(void *device) { (void)device; }
int photo_capture_request(void)
{
    photo_mode_capture_result("Photo saving requires an SDL-enabled build.");
    return 0;
}
#endif
