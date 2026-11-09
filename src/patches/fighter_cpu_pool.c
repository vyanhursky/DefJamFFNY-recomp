/* CPU-only owned animation storage. Keep the native allocator's headers and
 * free path, but take backing pages from the host's guest heap rather than the
 * title's scarce GPU-capable arena. The bounded backing is retained for reuse;
 * every bank must be freed by the native provider destructor between matches. */
#include "fighter_cpu_pool.h"
#include "fighter_finishers.h"
#include "fighter_film_proof.h"
#include "hooks/guest_call.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CPU_BYTES (32u * 1024u * 1024u)
#define CPU_PREFIX 256u
#define CPU_KEY 63u
#define CPU_REGISTRY (0x3C9158u + CPU_KEY * 4u)
static uint32_t s_backing, s_root, s_first, s_free_bytes, s_allocations;
static int s_open;
static struct { uint32_t address,bytes;unsigned film; } s_spans[512];
static RECOMP_TLS unsigned s_pending_film;
extern uint32_t xbox_HeapAlloc(uint32_t size, uint32_t alignment);
extern void sub_001E9640(void);

static void cpu_stop(const char *message) {
    fprintf(stderr, "[FIGHTERS] CPU animation storage stopped: %s\n", message);
    fflush(stderr); exit(1);
}
int defjam_fighter_cpu_contains(uint32_t address) {
    return s_backing && address >= s_backing + CPU_PREFIX
        && address - s_backing < CPU_BYTES;
}
int defjam_fighter_cpu_range(uint32_t address,uint32_t bytes) {
    if (!defjam_fighter_cpu_contains(address) || !bytes || bytes>CPU_BYTES-(address-s_backing)) return 0;
    for (unsigned i=0;i<s_allocations;++i)
        if (address>=s_spans[i].address && address-s_spans[i].address<=s_spans[i].bytes
            && bytes<=s_spans[i].bytes-(address-s_spans[i].address)) return 1;
    return 0;
}
unsigned defjam_fighter_cpu_film(uint32_t address) {
    for (unsigned i=s_allocations;i>0;--i)
        if (address>=s_spans[i-1].address && address-s_spans[i-1].address<s_spans[i-1].bytes)
            return s_spans[i-1].film;
    return 0;
}
static void cpu_empty(void) {
    if (MEM32(CPU_REGISTRY) != s_root || MEM32(s_root + 0x20) != s_first
        || MEM32(s_root + 0x24) != s_first || MEM16(s_first) != 0x4246
        || MEM32(s_first + 4) != s_free_bytes
        || MEM32(s_first + 0x10) != s_root + 0x10
        || MEM32(s_first + 0x14) != s_root + 0x10)
        cpu_stop("native provider retained or corrupted an owned animation allocation");
}
static void cpu_prepare(void) {
    if (!s_backing) {
        if (MEM32(CPU_REGISTRY)) cpu_stop("native pool key is already occupied");
        s_backing = xbox_HeapAlloc(CPU_BYTES, 128);
        if (!s_backing || s_backing > UINT32_MAX - CPU_BYTES)
            cpu_stop("cannot reserve the bounded 32 MiB guest CPU pool");
        memcpy((void *)XBOX_PTR(s_backing), "Fighter CPU animation", 22);
        uint32_t args[10] = {CPU_KEY, s_backing, s_backing + CPU_PREFIX,
                            CPU_BYTES - CPU_PREFIX, 16, 128, 0, 0, 0, 1};
        uint32_t frame = g_seh_ebp;
        guest_call(sub_001E9640, 0, 10, args);
        g_seh_ebp = frame;
        s_root = MEM32(CPU_REGISTRY);
        if (s_root != s_backing + CPU_PREFIX + 16)
            cpu_stop("native pool registration returned a different owner");
        s_first = MEM32(s_root + 0x20);
        if (!defjam_fighter_cpu_contains(s_first)) cpu_stop("native pool has no bounded free block");
        s_free_bytes = MEM32(s_first + 4);
        cpu_empty();
        fprintf(stderr, "[FIGHTERS] CPU animation pool registered key=%u backing=%08X bytes=%u free=%u\n",
                CPU_KEY, s_backing, CPU_BYTES, s_free_bytes);
    }
    if (!s_open) { cpu_empty(); s_open = 1; s_allocations = 0; }
}
uint32_t defjam_fighter_cpu_flags(uint32_t caller, uint32_t name, uint32_t bytes, uint32_t flags) {
    s_pending_film=0;
    /* Only the verified synchronous archive-reader allocation callbacks take
     * (filename, bytes, flags). 1E4057 is the uncompressed 1E4100 path;
     * 1E4453/1E473D/1E477A cover compressed reads. No global mode changes. */
    if ((caller != 0x1E3F20 && caller != 0x1E4057 && caller != 0x1E4453
        && caller != 0x1E473D && caller != 0x1E477A)
        || !name) return flags;
    char path[64];
    unsigned n;
    for (n = 0; n < sizeof(path) - 1; ++n) {
        path[n] = (char)MEM8(name + n);
        if (!path[n]) break;
    }
    if (n == sizeof(path) - 1) return flags;
    s_pending_film=defjam_fighter_film_file(path);
    if (!s_pending_film && !defjam_fighter_finisher_cpu_file(path)) return flags;
    if ((flags & ~0x100u) || !bytes || bytes > CPU_BYTES - CPU_PREFIX - 256)
        cpu_stop("owned animation request exceeds its reviewed flags or memory budget");
    cpu_prepare();
    /* Bit31 bypasses the small-block manager and default selector OR in
     * 29500. It is removed there; low6 then select the registered native pool. */
    return flags | 0x80000000u | CPU_KEY;
}
uint32_t defjam_fighter_cpu_film_flags(unsigned owner,uint32_t bytes,uint32_t flags) {
    if (!owner) return flags;
    if ((flags&~0x500u) || !bytes || bytes>CPU_BYTES-CPU_PREFIX-256)
        cpu_stop("owned final cinematic copy exceeds reviewed flags or byte budget");
    cpu_prepare();s_pending_film=owner;
    return flags|0x80000000u|CPU_KEY;
}
void defjam_fighter_cpu_result(uint32_t address, uint32_t bytes) {
    if (!s_open || !defjam_fighter_cpu_contains(address)
        || bytes > CPU_BYTES - (address - s_backing)
        || (MEM8(address - 14) & 63) != CPU_KEY)
        cpu_stop("owned animation allocation failed or escaped its native CPU pool");
    if (s_allocations>=512) cpu_stop("owned animation allocation population exceeds the active participant bound");
    s_spans[s_allocations].address=address;s_spans[s_allocations].bytes=bytes;
    s_spans[s_allocations].film=s_pending_film;s_pending_film=0;
    ++s_allocations;
}
void defjam_fighter_cpu_released(void) {
    if (!s_open) return;
    cpu_empty();
    fprintf(stderr, "[FIGHTERS] CPU animation pool fully released after native destructor allocations=%u free=%u\n",
            s_allocations, s_free_bytes);
    s_open = 0;
}
