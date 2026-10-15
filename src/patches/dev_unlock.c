/* Developer switches the retail image still carries, behind environment variables.
 *
 *   RECOMP_UNLOCK_ALL=1  every fighter and venue, 10,000 points (below)
 *   RECOMP_DEV_DEBUG=1   the in-fight debug overlay: what the "Debug" branch of the
 *                        Extras code handler (guest 0x00049EB5) does, which is to call
 *                        sub_000B4CE0(1), a setter for the byte at 0x0039C1DA. sub_000B5AD0
 *                        reads it every frame and, in a fight, draws a debug label
 *                        (for example "N4007 A") under each fighter's health bar.
 *
 * Developer unlock (RECOMP_UNLOCK_ALL=1): every fighter and venue, 10,000 points.
 *
 * The retail image still carries the developers' "unlock everything" routine,
 * guest 0x000158F0. It walks the character table (key 0x4CE5B1B2) and the
 * venue table (key 0xD7DCA628) and inserts each id into the profile's unlocked
 * sets, which is exactly what BuyCharacter and BuyVenue do one id at a time,
 * then sets the reward points (profile + 0x50) to 10,000 and tells the profile
 * owner it changed. Its only caller is the Extras code-entry handler's case 5
 * (the "BIGBANG" branch), and the retail code classifier never produces case 5,
 * so no pad input reaches it. docs/research/unlock-everything.md has the trail.
 *
 * This file calls it from the front end's own call stream. The front end logs
 * each call its screens make into the game; once the main menu has started, the
 * routine runs on every screen change, so a profile loaded later (Story, the
 * user-ID screen) is unlocked before the next screen can look at it. It only
 * inserts ids that are missing, so repeating it costs nothing and changes
 * nothing but the points, which are held at 10,000 until the profile is saved
 * differently.
 *
 * It changes the profile in memory and asks the game to save it: run it on a
 * disposable save (the harness and the scenario suite already do), not on a
 * real one. Off unless asked for, so the unmodified path stays testable.
 */
#include "host.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"

extern void sub_000158F0(void);

#define DEBUG_FLAG 0x0039C1DAu

static int s_enabled = -1;
static int s_debug = -1;
static int s_started;
static unsigned long s_runs;

int defjam_unlock_all_enabled(void)
{
    if (s_enabled < 0) {
        const char *v = getenv("RECOMP_UNLOCK_ALL");
        s_enabled = v && *v && strcmp(v, "0") != 0;
        if (s_enabled)
            fprintf(stderr, "[UNLOCK] RECOMP_UNLOCK_ALL: every fighter and venue, 10000 points, "
                            "on each screen change after the main menu starts\n");
    }
    return s_enabled;
}

static int debug_enabled(void)
{
    if (s_debug < 0) {
        const char *v = getenv("RECOMP_DEV_DEBUG");
        s_debug = v && *v && strcmp(v, "0") != 0;
        if (s_debug)
            fprintf(stderr, "[UNLOCK] RECOMP_DEV_DEBUG: in-fight debug overlay on\n");
    }
    return s_debug;
}

static void run_unlock(void)
{
    uint32_t eax = g_eax, ecx = g_ecx, edx = g_edx;

    /* A call needs a return address; the callee pops it and keeps the callee-saved
     * registers (ebx, esi, edi, ebp) as the x86 original did. */
    g_esp -= 4;
    MEM32(g_esp) = 0;
    sub_000158F0();
    g_eax = eax;
    g_ecx = ecx;
    g_edx = edx;
    s_runs++;
    if (s_runs == 1 || s_runs == 10 || s_runs == 100)
        fprintf(stderr, "[UNLOCK] sub_000158F0 run %lu\n", s_runs);
}

/* Called with the text of each front-end call, before the game handles it. */
void defjam_unlock_all_on_funccall(const char *text)
{
    int unlock = defjam_unlock_all_enabled();
    int debug = debug_enabled();

    if (!unlock && !debug)
        return;
    if (!s_started) {
        /* The managers sub_000158F0 reads exist once the front end is up. */
        if (strstr(text, "Game.StartMainMenu"))
            s_started = 1;
        return;
    }
    if (debug)
        MEM8(DEBUG_FLAG) = 1;
    if (unlock && strncmp(text, "Control.GetScreenInfo(", 22) == 0)
        run_unlock();
}
