#ifndef DEFJAM_FIGHTER_CPU_POOL_H
#define DEFJAM_FIGHTER_CPU_POOL_H
#include <stdint.h>
uint32_t defjam_fighter_cpu_flags(uint32_t caller, uint32_t name, uint32_t bytes, uint32_t flags);
void defjam_fighter_cpu_result(uint32_t address, uint32_t bytes);
int defjam_fighter_cpu_contains(uint32_t address);
int defjam_fighter_cpu_range(uint32_t address,uint32_t bytes);
unsigned defjam_fighter_cpu_film(uint32_t address);
uint32_t defjam_fighter_cpu_film_flags(unsigned owner,uint32_t bytes,uint32_t flags);
void defjam_fighter_cpu_released(void);
#endif
