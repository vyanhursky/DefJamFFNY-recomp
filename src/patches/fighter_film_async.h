#ifndef DEFJAM_FIGHTER_FILM_ASYNC_H
#define DEFJAM_FIGHTER_FILM_ASYNC_H
#include <stdint.h>
typedef struct FighterFilmAsyncScope {unsigned owner;uint32_t handle;} FighterFilmAsyncScope;
unsigned defjam_fighter_film_request_begin(uint32_t name);
void defjam_fighter_film_request_end(unsigned previous);
void defjam_fighter_film_opened(uint32_t handle);
FighterFilmAsyncScope defjam_fighter_film_callback_begin(uint32_t handle);
void defjam_fighter_film_callback_end(FighterFilmAsyncScope previous);
void defjam_fighter_film_cancel(uint32_t handle);
uint32_t defjam_fighter_film_allocation(uint32_t caller,uint32_t slot_offset,uint32_t bytes,uint32_t flags);
#endif
