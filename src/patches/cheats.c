/* Cheats: the [cheats] settings and the Story profile edits behind the overlay's Cheats page
 * (docs/cheats.md for players; docs/research/cheat-menu.md has the fields and how they were found).
 *
 * Fight cheats change only fighter records in memory, so they leave no trace in a save:
 *
 *   infinite_health  health changes that would lower a covered fighter's health are dropped at
 *                    the game's one health-apply function, sub_001A50B0 (record, float delta,
 *                    byte flags, float extra), so no KO can start from a hit. Each fight step
 *                    also puts the recoverable ceiling (+0x358, which hits lower) and health
 *                    (+0x350) back to the maximum (+0x354). Knock-outs that bypass that
 *                    function (stage hazards, sub_001D1140) still count.
 *   max_blazin       before each fighting step a covered fighter whose meter is not ready or
 *                    active is given momentum through the game's own gain function,
 *                    sub_001A5190(record, amount): it parks the meter at 99, marks Blazin'
 *                    ready (+0x93E bit 0) and sends the HUD event, as the tutorial does. While
 *                    ready, the ready timer (+0x368) is held at its start value so it does not
 *                    run out; once Blazin' has been used the next step makes it ready again.
 *   no_regen         the passive recovery (sub_001A5730, flags bit 0, a positive delta) is
 *                    dropped for covered fighters, so lost health stays lost.
 *
 * Each covers "players" (fighters not under CPU control, record +0x937 bit 0 clear) or
 * "everyone". Fighter records: 0x3B92E0 + slot * 0x12E8, a slot unused when +0x28 is -1.
 *
 * Story edits write the profile slot in use, S = P + index * 0x5950 + 0x177C with
 * P = [game-data + 4] and index = [P + 0x5AC7C]; cash is S+0x20 and development points S+0x28
 * (the shop's GetPlayerCash sub_0004CA30 and GetPlayerDevPts sub_0004CA70 read them). The game
 * saves that slot as it is in memory, so these changes are kept in the player's save.
 */
#include "host.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "recomp/gen/recomp_types.h"
#include "recomp_settings.h"
#include "cheats.h"

extern void sub_001A5190(void);

#define RECORDS          0x003B92E0u
#define RECORD_STRIDE    0x12E8u
#define SLOTS            4
#define R_SLOT           0x28u
#define R_HEALTH         0x350u
#define R_HEALTH_MAX     0x354u
#define R_HEALTH_CEILING 0x358u
#define R_HEALTH_RATIO   0x35Cu
#define R_BLAZIN_TIMER   0x368u
#define R_CONTROL        0x937u        /* bit 0: CPU */
#define R_BLAZIN         0x93Eu        /* bit 0 ready, bit 1 active */
#define R_FINISHED       0x933u        /* bit 1: out of the match */
#define BLAZIN_READY_TIME 1800.0f      /* what the game sets when Blazin' becomes ready */
#define G_PHASE          0x003B8F30u   /* 1 while fighting */

#define MANAGERS         0x002FB148u
#define GAMEDATA_SLOT    0x18u
#define PROFILE_INDEX    0x5AC7Cu
#define PROFILE_STRIDE   0x5950u
#define PROFILE_FIRST    0x177Cu
#define PROFILE_SLOTS    16u
#define S_CASH           0x20u
#define S_DEV_POINTS     0x28u
#define GUEST_LIMIT      0x04000000u   /* the console's 64 MB */

enum { COVER_OFF, COVER_PLAYERS, COVER_EVERYONE };
static const char *const k_cover[] = { "off", "players", "everyone", NULL };

static volatile int s_health, s_blazin, s_no_regen;

size_t cheats_settings(RecompSetting *out, size_t max)
{
    size_t n = 0;
    if (max < 3) return 0;
    memset(out, 0, sizeof(*out) * 3);
#define ADD(...) do { RecompSetting s_ = { __VA_ARGS__ }; out[n++] = s_; } while (0)
    ADD("cheats", "infinite_health", RECOMP_SETTING_ENUM, COVER_OFF, 0, 0, k_cover, "RECOMP_CHEAT_HEALTH", 0,
        "Fighters who take no damage: off, players (not the CPU) or everyone. Stage hazards can still knock "
        "a fighter out. Changes nothing in your save.");
    ADD("cheats", "max_blazin", RECOMP_SETTING_ENUM, COVER_OFF, 0, 0, k_cover, "RECOMP_CHEAT_BLAZIN", 0,
        "Fighters whose Blazin' meter is always full and ready: off, players or everyone. Trigger Blazin' "
        "as usual. Changes nothing in your save.");
    ADD("cheats", "no_regen", RECOMP_SETTING_ENUM, COVER_OFF, 0, 0, k_cover, "RECOMP_CHEAT_NO_REGEN", 0,
        "Fighters whose health does not recover over time: off, players or everyone. Changes nothing in "
        "your save.");
#undef ADD
    return n;
}

void cheats_apply_settings(void)
{
    static int logged = -1;
    int h = recomp_settings_get("cheats", "infinite_health", COVER_OFF);
    int b = recomp_settings_get("cheats", "max_blazin", COVER_OFF);
    int r = recomp_settings_get("cheats", "no_regen", COVER_OFF);
    s_health = h;
    s_blazin = b;
    s_no_regen = r;
    if (logged != h * 100 + b * 10 + r) {
        logged = h * 100 + b * 10 + r;
        fprintf(stderr, "[CHEATS] infinite_health %s, max_blazin %s, no_regen %s\n",
                k_cover[h], k_cover[b], k_cover[r]);
    }
}

static uint32_t record(int slot) { return RECORDS + (uint32_t)slot * RECORD_STRIDE; }

static int covers(int cover, uint32_t r)
{
    if (cover == COVER_EVERYONE) return 1;
    if (cover == COVER_PLAYERS) return (MEM8(r + R_CONTROL) & 1) == 0;
    return 0;
}

static int known_record(uint32_t r)
{
    return r >= RECORDS && r < record(SLOTS) && (r - RECORDS) % RECORD_STRIDE == 0 &&
           MEM32(r + R_SLOT) != 0xFFFFFFFFu;
}

static uint32_t f2u(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static float u2f(uint32_t u) { float f; memcpy(&f, &u, 4); return f; }

/* sub_001A5190(record, amount): cdecl, the caller drops the two arguments. */
static void give_momentum(uint32_t r, float amount)
{
    uint32_t eax = g_eax, ecx = g_ecx, edx = g_edx, esp = g_esp;
    g_esp -= 12;
    MEM32(g_esp) = 0;                   /* return address; the callee pops it */
    MEM32(g_esp + 4) = r;
    MEM32(g_esp + 8) = f2u(amount);
    sub_001A5190();
    g_esp = esp;
    g_eax = eax;
    g_ecx = ecx;
    g_edx = edx;
}

void cheats_fight_step(void)
{
    int health = s_health, blazin = s_blazin, slot;
    static unsigned long readied;
    if (!health && !blazin) return;
    for (slot = 0; slot < SLOTS; slot++) {
        uint32_t r = record(slot);
        if (MEM32(r + R_SLOT) == 0xFFFFFFFFu) continue;
        if (covers(health, r)) {
            uint32_t max = MEM32(r + R_HEALTH_MAX);
            if (u2f(max) > 0.0f) {
                MEM32(r + R_HEALTH_CEILING) = max;
                MEM32(r + R_HEALTH) = max;
                MEM32(r + R_HEALTH_RATIO) = f2u(1.0f);
            }
        }
        if (covers(blazin, r) && MEM32(G_PHASE) == 1 && !(MEM8(r + R_FINISHED) & 2)) {
            uint8_t state = MEM8(r + R_BLAZIN);
            if (state & 1) {
                MEM32(r + R_BLAZIN_TIMER) = f2u(BLAZIN_READY_TIME);
            } else if (!(state & 2)) {
                give_momentum(r, 1000.0f);  /* any amount past the gain multipliers reaches 99 */
                if (++readied == 1 || readied == 10)
                    fprintf(stderr, "[CHEATS] Blazin' made ready (slot %d, state %u, meter %.1f)\n", slot,
                            MEM8(r + R_BLAZIN), (double)MEMF(r + 0x364));
            }
        }
    }
}

/* sub_001A50B0_enter: [esp+4] record, [esp+8] float delta, [esp+0xC] flags (bit 0: the
 * per-step recovery or drain). */
void cheats_health_change(void)
{
    int health = s_health, regen = s_no_regen;
    uint32_t r;
    float delta;
    static unsigned long dropped_hits, dropped_regen;
    if (!health && !regen) return;
    r = MEM32(g_esp + 4);
    if (!known_record(r)) return;
    delta = u2f(MEM32(g_esp + 8));
    if (delta < 0.0f && covers(health, r)) {
        MEM32(g_esp + 8) = f2u(0.0f);
        if (++dropped_hits == 1 || dropped_hits == 100)
            fprintf(stderr, "[CHEATS] health loss dropped (%lu so far)\n", dropped_hits);
    } else if (delta > 0.0f && (MEM8(g_esp + 0xC) & 1) && covers(regen, r)) {
        MEM32(g_esp + 8) = f2u(0.0f);
        if (++dropped_regen == 1 || dropped_regen == 1000)
            fprintf(stderr, "[CHEATS] health recovery dropped (%lu so far)\n", dropped_regen);
    }
}

/* ---- Story profile ------------------------------------------------------------------------ */

static uint32_t story_slot(int *index)
{
    uint32_t gd = MEM32(MANAGERS + GAMEDATA_SLOT * 4), p, i;
    if (gd < 0x10000u || gd >= GUEST_LIMIT) return 0;
    p = MEM32(gd + 4);
    if (p < 0x10000u || p >= GUEST_LIMIT - PROFILE_INDEX - 4) return 0;
    i = MEM32(p + PROFILE_INDEX);
    if (i >= PROFILE_SLOTS) return 0;
    if (index) *index = (int)i;
    return p + i * PROFILE_STRIDE + PROFILE_FIRST;
}

void cheats_story_read(CheatsStory *out)
{
    int index = -1;
    uint32_t s = story_slot(&index);
    memset(out, 0, sizeof(*out));
    if (!s) return;
    out->valid = 1;
    out->slot = index;
    out->cash = MEM32(s + S_CASH);
    out->dev_points = MEM32(s + S_DEV_POINTS);
}

static int story_write(uint32_t offset, uint32_t value, const char *what)
{
    int index = -1;
    uint32_t s = story_slot(&index);
    if (!s) return 0;
    if (value > CHEATS_STORY_MAX) value = CHEATS_STORY_MAX;
    fprintf(stderr, "[CHEATS] Story profile slot %d: %s %u -> %u\n", index, what, MEM32(s + offset), value);
    fflush(stderr);
    MEM32(s + offset) = value;
    return 1;
}

int cheats_story_set_cash(uint32_t value) { return story_write(S_CASH, value, "cash"); }
int cheats_story_set_dev_points(uint32_t value) { return story_write(S_DEV_POINTS, value, "development points"); }
