/* Full generation-tagged request ownership survives native async row recycling.
 * Route only the reviewed final-copy allocation, never its static debug label. */
#include "fighter_film_async.h"
#include "fighter_fatal.h"
#include "fighter_film_proof.h"
#include "fighter_cpu_pool.h"
#include "recomp/gen/recomp_types.h"
#include <stdio.h>
#include <stdlib.h>
static struct {uint32_t handle;unsigned owner;} s_requests[64];
static RECOMP_TLS unsigned s_request_owner;
static RECOMP_TLS FighterFilmAsyncScope s_callback;
static void stop(void) {defjam_fighter_fatal("cinematic async","request ownership differs from the reviewed film request");}
unsigned defjam_fighter_film_request_begin(uint32_t name) {
    unsigned previous=s_request_owner;s_request_owner=0;
    if (!name) return previous;
    char path[64];unsigned i;
    for (i=0;i<sizeof path-1;++i) {path[i]=(char)MEM8(name+i);if (!path[i]) break;}
    if (i<sizeof path-1) s_request_owner=defjam_fighter_film_file(path);
    return previous;
}
void defjam_fighter_film_request_end(unsigned previous) {s_request_owner=previous;}
void defjam_fighter_film_opened(uint32_t handle) {
    if (handle<0x100) return;
    unsigned empty=64;
    for (unsigned i=0;i<64;++i) {
        if (s_requests[i].owner && s_requests[i].handle==handle) {empty=i;break;}
        if (!s_requests[i].owner && empty==64) empty=i;
    }
    if (empty==64) {if (s_request_owner) stop();return;}
    s_requests[empty].handle=handle;s_requests[empty].owner=s_request_owner;
}
FighterFilmAsyncScope defjam_fighter_film_callback_begin(uint32_t handle) {
    FighterFilmAsyncScope previous=s_callback;s_callback.owner=0;s_callback.handle=handle;
    for (unsigned i=0;i<64;++i) if (s_requests[i].owner && s_requests[i].handle==handle) {
        s_callback.owner=s_requests[i].owner;s_requests[i].owner=0;break;
    }
    return previous;
}
void defjam_fighter_film_callback_end(FighterFilmAsyncScope previous) {s_callback=previous;}
void defjam_fighter_film_cancel(uint32_t handle) {
    for (unsigned i=0;i<64;++i) if (s_requests[i].handle==handle) s_requests[i].owner=0;
}
uint32_t defjam_fighter_film_allocation(uint32_t caller,uint32_t slot_offset,uint32_t bytes,uint32_t flags) {
    if (!s_callback.owner || (caller!=0x1AA99 && caller!=0x1AACF)) return flags;
    if (slot_offset>=32*0x14 || slot_offset%0x14 || MEM32(0x3319A0+slot_offset)!=s_callback.handle
        || MEM32(0x3319AC+slot_offset)!=flags || MEM8(0x3319B0+slot_offset)!=1) stop();
    return defjam_fighter_cpu_film_flags(s_callback.owner,bytes,flags);
}
