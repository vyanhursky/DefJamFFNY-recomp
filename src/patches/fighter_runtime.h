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
void defjam_fighter_settings_bound(uint32_t self);
void defjam_fighter_settings_validate(uint32_t self, uint32_t payload);
void defjam_fighter_settings_saving(void);
void defjam_fighter_settings_saved(void);
void defjam_fighter_profile_staging(uint32_t name, uint32_t payload);
void defjam_fighter_save_batch(void);
void defjam_fighter_unlock_inserting(uint32_t self);
void defjam_fighter_selection_gate(uint32_t selection);
/* Reads the original string vector before the native dispatcher narrows it.
 * UINT32_MAX means preserve the original submission/sentinel. */
uint32_t defjam_fighter_controller_submission(uint32_t arguments);
void defjam_fighter_menu_event(const char *text);
uint32_t defjam_fighter_filter_banks(uint32_t entries, uint32_t count);
#endif
