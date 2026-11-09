#ifndef DEFJAM_FIGHTER_FILM_PROOF_H
#define DEFJAM_FIGHTER_FILM_PROOF_H
#include <stdint.h>
int defjam_fighter_film_start(void);
unsigned defjam_fighter_film_file(const char *path);
int defjam_fighter_film_preconstruct(uint32_t bank);
int defjam_fighter_film_known(const char *name);
int defjam_fighter_film_complete(const char *name,int intro);
int defjam_fighter_film_bind(const char *name,uint32_t entry,uint32_t visual,uint32_t descriptor);
void defjam_fighter_film_release(void);
#endif
