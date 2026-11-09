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
int defjam_fighter_graph_visual(uint32_t visual,uint32_t bones,const uint8_t *rigs,unsigned rig_count,
                               const uint32_t *face_need,const uint32_t *hand_need);
void defjam_fighter_graph_release(void);
#endif
