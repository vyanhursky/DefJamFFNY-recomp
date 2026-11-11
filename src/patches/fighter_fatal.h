#ifndef DEFJAM_FIGHTER_FATAL_H
#define DEFJAM_FIGHTER_FATAL_H
/* The one way a fighter module stops the game. Every module used to keep its own
 * stop function; most only wrote to stderr, so the player saw the window vanish.
 * This logs "[FIGHTERS] <area> stopped: <message>", shows the message in the
 * host's error dialog and exits. Harness runs have no one to click a dialog, so
 * the research entry point turns it off with defjam_fighter_fatal_dialog(0). */
#ifdef _MSC_VER
#define DEFJAM_FIGHTER_NORETURN __declspec(noreturn)
#else
#define DEFJAM_FIGHTER_NORETURN _Noreturn
#endif
/* area may be NULL for the plain "[FIGHTERS] stopped:" line. */
DEFJAM_FIGHTER_NORETURN void defjam_fighter_fatal(const char *area, const char *message);
void defjam_fighter_fatal_dialog(int enabled);
#endif
