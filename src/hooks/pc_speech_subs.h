/* Speech subtitles for in-game voices (fighter intros/extros, career player
 * voices, shops, taunts, tutorial, front-end, voicemail).
 *
 * Loaded from <mod_dir>/speech_subtitles.txt when a language pack has one.
 * Triggered deterministically when the game opens a loose speech stream path
 * or reads a SCHl audio block from audio/speech1..3.viv.
 */

#ifndef DEFJAM_PC_SPEECH_SUBS_H
#define DEFJAM_PC_SPEECH_SUBS_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Load <mod_dir>/speech_subtitles.txt. Safe to call with NULL/missing file. */
void pc_speech_subs_load(const char *mod_dir);

/* Whether voice subtitles should be displayed right now ([language] voice_subtitles). */
int pc_speech_subs_enabled(void);

/* Copy the currently active UTF-8 subtitle line into `out` (up to `cap` bytes)
 * and return 1 if a line is active at the current timestamp, or 0 otherwise. */
int pc_speech_subs_current(char *out, size_t cap);

/* Hooks called from src/recomp_manual.c when speech files are opened/read. */
void xbox_speech_notify_open(const char *xbox_path, void *handle);
void xbox_speech_notify_close(void *handle);
void xbox_speech_notify_read(void *handle, uint64_t offset, const void *buf, uint32_t len);
void xbox_speech_notify_path(const char *xbox_path);

/* Match intro/extro synchronization hooks */
void pc_speech_subs_clear_match(void);
void pc_speech_subs_reset(void);
void pc_speech_subs_register_intro(const char *key);
void pc_speech_subs_register_extro(const char *key);
void pc_speech_subs_play_intro(uint32_t fighter_idx);
void pc_speech_subs_play_extro(uint32_t fighter_idx);
void pc_speech_subs_trigger_direct(const char *clip_key);

#ifdef __cplusplus
}
#endif

#endif
