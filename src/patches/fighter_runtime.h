#ifndef DEFJAM_FIGHTER_RUNTIME_H
#define DEFJAM_FIGHTER_RUNTIME_H
#include <stdint.h>
/* Local R&D hooks. Roster probes require disposable data and no player settings;
 * no shipping fighter capability or normal-profile activation. */
int defjam_fighter_runtime_start(void);
uint32_t defjam_fighter_localized(uint32_t key, uint32_t native_value, uint32_t localizer);
void defjam_fighter_order(uint32_t database, uint32_t entries, uint32_t count, const char *source);
void defjam_fighter_materialized(uint32_t self, uint32_t handle);
void defjam_fighter_model_input(uint32_t object);
uint32_t defjam_fighter_native_handle(uint32_t handle);
void defjam_fighter_handle_produced(uint32_t database, uint32_t table, uint32_t output);
#endif
