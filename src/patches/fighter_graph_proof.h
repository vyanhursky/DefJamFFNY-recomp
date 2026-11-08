#ifndef DEFJAM_FIGHTER_GRAPH_PROOF_H
#define DEFJAM_FIGHTER_GRAPH_PROOF_H
#include <stddef.h>
#include <stdint.h>
int defjam_fighter_graph_start(const uint8_t *data,size_t bytes,uint32_t motion_count);
int defjam_fighter_graph_has(uint32_t ordinal);
int defjam_fighter_graph_known(uint32_t ordinal,const char *name);
int defjam_fighter_graph_complete(void);
int defjam_fighter_graph_preconstruct(uint32_t bank);
int defjam_fighter_graph_bound(uint32_t ordinal,uint32_t bank);
int defjam_fighter_graph_bank(uint32_t ordinal,uint32_t bank,uint32_t body_index,uint32_t root_index);
int defjam_fighter_graph_actor(uint32_t ordinal,uint32_t actor);
void defjam_fighter_graph_release(void);
#endif
