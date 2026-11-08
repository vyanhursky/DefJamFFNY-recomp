#ifndef DEFJAM_FIGHTER_EVENTS_H
#define DEFJAM_FIGHTER_EVENTS_H
int defjam_fighter_events_start(void);
int defjam_fighter_events_has(const char *name,unsigned flags);
const char *defjam_fighter_events_tags_path(void);
const char *defjam_fighter_events_cameras_path(void);
#endif
