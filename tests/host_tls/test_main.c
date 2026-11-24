/* Exercise host.h's actual qualifier: ignoring __declspec(thread) can compile
 * successfully while turning per-thread telemetry into shared process state. */
#include "host.h"
#include <stdio.h>

static HOST_TLS DWORD value;
static volatile LONG ready;
static HANDLE release_workers;
static DWORD *addresses[2];

static DWORD WINAPI worker(void *arg)
{
    unsigned index = (unsigned)(uintptr_t)arg;
    DWORD own = GetCurrentThreadId();
    value = own;
    addresses[index] = &value;
    InterlockedIncrement(&ready);
    if (WaitForSingleObject(release_workers, 5000) != WAIT_OBJECT_0)
        return 2;
    return value == own ? 0 : 3;
}

int main(void)
{
    HANDLE threads[2];
    DWORD result[2] = {1, 1};
    ULONGLONG deadline = GetTickCount64() + 5000;
    value = 0x12345678;
    release_workers = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!release_workers) return 1;
    threads[0] = CreateThread(NULL, 0, worker, (void *)(uintptr_t)0, 0, NULL);
    threads[1] = CreateThread(NULL, 0, worker, (void *)(uintptr_t)1, 0, NULL);
    if (!threads[0] || !threads[1]) return 1;
    while (InterlockedCompareExchange(&ready, 0, 0) != 2) {
        if (GetTickCount64() >= deadline) return 1;
        Sleep(1);
    }
    SetEvent(release_workers);
    if (WaitForMultipleObjects(2, threads, TRUE, 5000) != WAIT_OBJECT_0) return 1;
    GetExitCodeThread(threads[0], &result[0]);
    GetExitCodeThread(threads[1], &result[1]);
    CloseHandle(threads[0]); CloseHandle(threads[1]); CloseHandle(release_workers);
    if (result[0] || result[1] || value != 0x12345678 ||
        addresses[0] == addresses[1] || addresses[0] == &value || addresses[1] == &value)
        return 1;
    puts("host TLS: three independent thread values and addresses");
    return 0;
}
