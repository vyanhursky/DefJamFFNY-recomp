/* Game-state telemetry for the scenario harness, enabled by RECOMP_TEST_OBSERVATIONS=1.
 *
 * Emits two kinds of line on stderr:
 *
 *   [TEST-STATE] {...}   a sample of the match and the four fighter records every
 *                        STATE_PERIOD fight steps: raw fields, for calibration and
 *                        for a report to plot.
 *   [TEST-EVENT] {...}   an edge the harness asserts on: rng, match_start, movement,
 *                        attack, damage, result, match_over.
 *
 * Everything is specific to the verified USA dump. The addresses come from
 * docs/research/simulation-tick.md, match-end-state.md and fighter-record-fields.md;
 * docs/research/combat-telemetry.md says which were confirmed against live fights.
 *
 * "step" counts entries to sub_00087700, the routine that advances a live fight
 * by one simulation step. It restarts at each match start. It is not a count of
 * presented frames: the game runs zero to four steps per frame.
 *
 * The probes read guest memory and never write it, with one opt-in exception:
 * RECOMP_TEST_RNG_SEED=<n> replaces the seed argument of the match's random
 * number generator, which the game otherwise takes from the time-stamp counter.
 * That changes what the CPU fighters do; it exists so a scenario can be repeated.
 */
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "recomp/gen/recomp_types.h"
#include "test_observations.h"

#define ACTORS        0x003B92E0u
#define STRIDE        0x12E8u
#define SLOTS         4
#define STATE_PERIOD  30            /* fight steps between [TEST-STATE] samples */

/* Match globals (match-end-state.md, simulation-tick.md). */
#define G_FLAGS       0x003B9054u   /* bit 0x08: match decided */
#define G_PHASE       0x003B8F30u   /* 0 start, 1 fighting, 2 decided, 3 finished */
#define G_WINNER      0x003B8F40u
#define G_CLOCK_MIN   0x003B9030u
#define G_CLOCK_SEC   0x003B9034u
#define G_MATCH_TYPE  0x003B9084u
#define G_TIME_SCALE  0x003B8F2Cu

/* Fighter record fields (fighter-record-fields.md). */
#define F_SLOT        0x28u         /* 0xFFFFFFFF when the slot is unused */
#define F_CHARACTER   0x2Cu
#define F_STATE       0x30u
#define F_POS_X       0x44u
#define F_POS_Y       0x48u
#define F_POS_Z       0x4Cu
#define F_FACING      0x54u
#define F_HEALTH      0x350u
#define F_HEALTH_MAX  0x354u
#define F_CONTROL     0x937u        /* bit 0: CPU */
#define F_HELD        0x9E0u
#define F_PRESSED     0x9F0u
#define F_STICK_X     0x9FCu
#define F_STICK_Y     0xA00u

#define DIRECTION_BITS 0x3000Fu     /* d-pad nibble, left stick, right stick */
#define ACTION_BITS    0x30F0u      /* 0x10 0x20 0x40 0x80 0x1000 0x2000 */
#define MOVE_DISTANCE  2.0f         /* world units walked during one hold of a direction */
#define MOVE_STEP_MAX  1.0f         /* a larger change in one step is a reposition, not a walk */

static LONG64 s_step;               /* fight steps since the last match start */
static LONG s_match;                /* match ordinal in this process */
static int s_in_match, s_setup_due, s_over_reported;
static int s_moved[SLOTS], s_holding[SLOTS];
static float s_hold_x[SLOTS], s_hold_z[SLOTS], s_path[SLOTS];
static LONG64 s_press_step[SLOTS];
static uint32_t s_press_bits[SLOTS];
static LONG s_budget = 20000;       /* lines; a runaway must not fill the disk */

/* Each line is built whole and written with one call: stderr is shared with
 * every other thread's log, and a line assembled from several writes had other
 * output land in the middle of its JSON. */
static __declspec(thread) char s_line[4096];
static __declspec(thread) size_t s_len;

static void put(const char *format, ...)
{
    va_list args;
    int n;
    if (s_len >= sizeof(s_line) - 1) return;
    va_start(args, format);
    n = vsnprintf(s_line + s_len, sizeof(s_line) - s_len, format, args);
    va_end(args);
    if (n < 0) return;
    s_len += (size_t)n;
    if (s_len > sizeof(s_line) - 1) s_len = sizeof(s_line) - 1;
}

static void end_line(void)
{
    /* A line that filled the buffer was cut short and is not valid JSON: drop it. */
    if (s_len < sizeof(s_line) - 1)
        fprintf(stderr, "%s}\n", s_line);
    s_len = 0;
    s_line[0] = 0;
}

static uint32_t record(int slot) { return ACTORS + (uint32_t)slot * STRIDE; }

static float f32(uint32_t address)
{
    uint32_t bits = MEM32(address);
    float value;
    memcpy(&value, &bits, sizeof(value));
    return isfinite(value) ? value : 0.0f;
}

static int active(int slot) { return MEM32(record(slot) + F_SLOT) != 0xFFFFFFFFu; }

static int is_cpu(int slot)
{
    /* The byte at F_CONTROL, read through its containing dword. */
    return (int)((MEM32(record(slot) + (F_CONTROL & ~3u)) >> (8u * (F_CONTROL & 3u))) & 1u);
}

static int budget(void) { return InterlockedDecrement(&s_budget) >= 0; }

static void begin_line(const char *tag, const char *event)
{
    s_len = 0;
    put("[%s] {\"event\":\"%s\",\"match\":%ld,\"step\":%lld,\"host_ms\":%llu",
        tag, event, (long)s_match, (long long)s_step, (unsigned long long)GetTickCount64());
}

static void put_fighters(void)
{
    int slot, first = 1;
    put(",\"fighters\":[");
    for (slot = 0; slot < SLOTS; slot++) {
        uint32_t r = record(slot);
        if (!active(slot)) continue;
        put("%s{\"slot\":%d,\"character\":%u,\"cpu\":%d,\"state\":%u,"
            "\"x\":%.4g,\"y\":%.4g,\"z\":%.4g,\"facing\":%.4g,"
            "\"health\":%.6g,\"health_max\":%.6g,\"held\":%u,\"pressed\":%u,"
            "\"stick_x\":%.3g,\"stick_y\":%.3g}",
            first ? "" : ",", slot, MEM32(r + F_CHARACTER), is_cpu(slot), MEM32(r + F_STATE),
            (double)f32(r + F_POS_X), (double)f32(r + F_POS_Y), (double)f32(r + F_POS_Z),
            (double)f32(r + F_FACING), (double)f32(r + F_HEALTH), (double)f32(r + F_HEALTH_MAX),
            MEM32(r + F_HELD), MEM32(r + F_PRESSED),
            (double)f32(r + F_STICK_X), (double)f32(r + F_STICK_Y));
        first = 0;
    }
    put("]");
}

static void put_slot_list(const char *name, uint32_t list)
{
    int i, first = 1;
    put(",\"%s\":[", name);
    /* Up to four slot indices ended by -1, on the guest stack or in guest data.
     * Anything outside guest RAM is not followed. */
    if (list >= 0x10000u && list < 0x04000000u - 16u) {
        for (i = 0; i < SLOTS; i++) {
            uint32_t value = MEM32(list + 4u * (uint32_t)i);
            if (value >= SLOTS) break;
            put("%s%u", first ? "" : ",", value);
            first = 0;
        }
    }
    put("]");
}

/* sub_001A4D90: the match is being set up. The records are filled by this call,
 * so the match_start event waits for the first step after it. */
void defjam_test_match_start(void)
{
    if (!defjam_test_observations_enabled()) return;
    InterlockedIncrement(&s_match);
    s_step = 0;
    s_in_match = 1;
    s_setup_due = 1;
    s_over_reported = 0;
    memset(s_moved, 0, sizeof(s_moved));
    memset(s_holding, 0, sizeof(s_holding));
    memset(s_press_step, 0, sizeof(s_press_step));
    memset(s_press_bits, 0, sizeof(s_press_bits));
}

/* sub_001BC690(seed, increment): the match's random number generator is seeded. */
void defjam_test_rng(uint32_t stack)
{
    const char *want;
    uint32_t seed, increment;
    int forced = 0;
    if (!defjam_test_observations_enabled()) return;
    seed = MEM32(stack + 4);
    increment = MEM32(stack + 8);
    want = getenv("RECOMP_TEST_RNG_SEED");
    if (want && *want) {
        seed = (uint32_t)strtoul(want, NULL, 0);
        MEM32(stack + 4) = seed;        /* the one deliberate write; see the header */
        forced = 1;
    }
    if (!budget()) return;
    begin_line("TEST-EVENT", "rng");
    put(",\"seed\":%u,\"increment\":%u,\"forced\":%s", seed, increment, forced ? "true" : "false");
    end_line();
}

/* sub_00087700: one simulation step of a live fight is about to run. */
void defjam_test_step(void)
{
    int slot;
    if (!defjam_test_observations_enabled() || !s_in_match) return;
    s_step++;

    if (s_setup_due) {
        s_setup_due = 0;
        if (budget()) {
            begin_line("TEST-EVENT", "match_start");
            put(",\"match_type\":%u", MEM32(G_MATCH_TYPE));
            put_fighters();
            end_line();
        }
    }

    for (slot = 0; slot < SLOTS; slot++) {
        uint32_t r = record(slot), pressed, held;
        if (!active(slot) || is_cpu(slot)) continue;
        /* A human fighter's action press, remembered so a hit it lands can be
         * tied to an input rather than to whatever else was going on. */
        pressed = MEM32(r + F_PRESSED) & ACTION_BITS;
        if (pressed) {
            s_press_step[slot] = s_step;
            s_press_bits[slot] = pressed;
        }
        /* Movement is distance covered during one unbroken hold of a direction,
         * measured from where the hold began. Distance from the spawn point
         * would also count the walk-in before the fight and being thrown. */
        held = MEM32(r + F_HELD);
        if (!(held & DIRECTION_BITS) || MEM32(G_PHASE) != 1u) {
            s_holding[slot] = 0;
        } else if (!s_holding[slot]) {
            s_holding[slot] = 1;
            s_path[slot] = 0.0f;
            s_hold_x[slot] = f32(r + F_POS_X);
            s_hold_z[slot] = f32(r + F_POS_Z);
        } else if (!s_moved[slot]) {
            float dx = f32(r + F_POS_X) - s_hold_x[slot], dz = f32(r + F_POS_Z) - s_hold_z[slot];
            float delta = (float)sqrt((double)(dx * dx + dz * dz));
            s_hold_x[slot] = f32(r + F_POS_X);
            s_hold_z[slot] = f32(r + F_POS_Z);
            /* Walking covers a fraction of a unit per step. A larger jump is the
             * game placing the fighter (the walk-in ending, a throw): not counted. */
            if (delta <= MOVE_STEP_MAX)
                s_path[slot] += delta;
            if (s_path[slot] > MOVE_DISTANCE && budget()) {
                s_moved[slot] = 1;
                begin_line("TEST-EVENT", "movement");
                put(",\"slot\":%d,\"distance\":%.4g,\"held\":%u,\"stick_x\":%.3g,\"stick_y\":%.3g",
                    slot, (double)s_path[slot], held,
                    (double)f32(r + F_STICK_X), (double)f32(r + F_STICK_Y));
                end_line();
            }
        }
    }

    /* Phase 2 or 3 is the game's own "decided". Bit 0x08 of the flag word, which
     * a reading of the code suggested, stayed clear through a knockout in a live
     * One on One (flags went 0x2 -> 0x6: bit 0x04 is the end-of-fight slow motion). */
    if (!s_over_reported && MEM32(G_PHASE) >= 2u && MEM32(G_PHASE) <= 3u) {
        s_over_reported = 1;
        if (budget()) {
            begin_line("TEST-EVENT", "match_over");
            put(",\"winner_slot\":%u,\"phase\":%u,\"clock\":[%u,%u]",
                MEM32(G_WINNER), MEM32(G_PHASE), MEM32(G_CLOCK_MIN), MEM32(G_CLOCK_SEC));
            put_fighters();
            end_line();
        }
    }

    if (s_step % STATE_PERIOD == 1 && budget()) {
        begin_line("TEST-STATE", "sample");
        put(",\"flags\":%u,\"phase\":%u,\"clock\":[%u,%u],\"time_scale\":%.4g",
            MEM32(G_FLAGS), MEM32(G_PHASE), MEM32(G_CLOCK_MIN), MEM32(G_CLOCK_SEC), (double)f32(G_TIME_SCALE));
        put_fighters();
        end_line();
    }
}

/* Called from the hit-resolution hook (sub_001A5DD0) with validated slots. */
void defjam_test_attack(int attacker, int defender)
{
    if (!s_in_match || attacker < 0 || defender < 0 || is_cpu(attacker)) return;
    if (!s_press_step[attacker] || !budget()) return;
    begin_line("TEST-EVENT", "attack");
    put(",\"slot\":%d,\"target_slot\":%d,\"pressed\":%u,\"steps_since_press\":%lld",
        attacker, defender, s_press_bits[attacker], (long long)(s_step - s_press_step[attacker]));
    end_line();
}

/* Called from the health-notify hook with a validated record and its values. */
void defjam_test_damage(int defender, float before, float after)
{
    if (!s_in_match || defender < 0 || !(after < before) || !budget()) return;
    begin_line("TEST-EVENT", "damage");
    put(",\"slot\":%d,\"cpu\":%d,\"health_before\":%.6g,\"health_after\":%.6g,\"health_max\":%.6g",
        defender, is_cpu(defender), (double)before, (double)after,
        (double)f32(record(defender) + F_HEALTH_MAX));
    end_line();
}

/* sub_001A6A80(winners, losers, code): the game records a result. */
void defjam_test_result(uint32_t winners, uint32_t losers, uint32_t code)
{
    if (!defjam_test_observations_enabled() || !s_in_match || !budget()) return;
    begin_line("TEST-EVENT", "result");
    put(",\"code\":%u,\"decisive\":%s,\"draw\":%s,\"time_up\":%s", code & 0xFFFFu,
        (code & 1u) ? "true" : "false", (code & 4u) ? "true" : "false", (code & 0x40u) ? "true" : "false");
    put_slot_list("winners", winners);
    put_slot_list("losers", losers);
    put(",\"clock\":[%u,%u]", MEM32(G_CLOCK_MIN), MEM32(G_CLOCK_SEC));
    put_fighters();
    end_line();
}
