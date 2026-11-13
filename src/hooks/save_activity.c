/* Which save files the game is in the middle of writing (P5 of the 2026-11-12 review).
 *
 * The game writes its saves through two kernel-level wrappers that recomp_manual.c
 * already overrides: a write (sub_001F8D61) and a close (sub_001F694D). A handle
 * that has been written and not yet closed is a save in progress. Closing the
 * window asks for an exit; the window thread then waits here, a few seconds at
 * most, until no save is in progress, so a close during a save cannot leave a
 * truncated profile. */
#include "save_activity.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(_WIN32)
#include <windows.h>
#else
#include <sched.h>
#include <time.h>
#endif

#define SAVE_ACTIVITY_MAX 32

static volatile long s_lock;
static uint32_t s_handles[SAVE_ACTIVITY_MAX];
static unsigned s_count;
static volatile long s_exit_requested;
static unsigned s_lost; /* writes we could not track: count them as busy until the next idle close */

static void lock(void) {
#if defined(_WIN32)
    while (InterlockedCompareExchange((volatile LONG *)&s_lock, 1, 0)) Sleep(0);
#else
    while (__sync_lock_test_and_set(&s_lock, 1)) sched_yield();
#endif
}

static void unlock(void) {
#if defined(_WIN32)
    InterlockedExchange((volatile LONG *)&s_lock, 0);
#else
    __sync_lock_release(&s_lock);
#endif
}

void save_activity_write(uint32_t handle) {
    unsigned i;
    lock();
    for (i = 0; i < s_count && s_handles[i] != handle; ++i) {}
    if (i == s_count) {
        if (s_count < SAVE_ACTIVITY_MAX) s_handles[s_count++] = handle;
        else ++s_lost;
    }
    unlock();
}

void save_activity_close(uint32_t handle) {
    lock();
    for (unsigned i = 0; i < s_count; ++i)
        if (s_handles[i] == handle) { s_handles[i] = s_handles[--s_count]; break; }
    if (!s_count) s_lost = 0;
    unlock();
}

int save_activity_busy(void) {
    int busy;
    lock();
    busy = s_count != 0 || s_lost != 0;
    unlock();
    return busy;
}

int save_activity_exit_requested(void) { return s_exit_requested != 0; }

static unsigned long long now_ms(void) {
#if defined(_WIN32)
    return GetTickCount64();
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (unsigned long long)t.tv_sec * 1000u + (unsigned long long)t.tv_nsec / 1000000u;
#endif
}

int save_activity_wait_idle(unsigned timeout_ms) {
    unsigned long long start = now_ms();
    int waited = 0;
    s_exit_requested = 1;
    while (save_activity_busy()) {
        if (now_ms() - start >= timeout_ms) {
            fprintf(stderr, "[SAVES] a save was still being written after %u ms; exiting anyway\n", timeout_ms);
            return 0;
        }
        waited = 1;
#if defined(_WIN32)
        Sleep(10);
#else
        {
            struct timespec pause = {0, 10000000L};
            nanosleep(&pause, NULL);
        }
#endif
    }
    if (waited) fprintf(stderr, "[SAVES] waited %llu ms for a save to finish before exiting\n", now_ms() - start);
    return 1;
}
