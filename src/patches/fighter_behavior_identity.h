#ifndef DEFJAM_FIGHTER_BEHAVIOR_IDENTITY_H
#define DEFJAM_FIGHTER_BEHAVIOR_IDENTITY_H
#include "fighter_caf.h"
#define CAF_BEHAVIOR_BIT 0x80000000u
#define CAF_BEHAVIOR_MAX 16384u
typedef struct { uint32_t selection, index; } CafBehaviorBinding;
static int caf_behavior_key(uint32_t key) {
    return key>=0x80000064u && key<=0xfffffffeu;
}
static uint32_t caf_behavior_index(const CafBehaviorBinding *rows,uint32_t count,uint32_t slot) {
    uint32_t selection=defjam_fighter_caf_selection(slot),low=0,high=count;
    if(selection<100)return UINT32_MAX;
    while(low<high) {uint32_t middle=low+(high-low)/2;if(rows[middle].selection<selection)low=middle+1;else high=middle;}
    return low<count && rows[low].selection==selection?rows[low].index:UINT32_MAX;
}
#endif
