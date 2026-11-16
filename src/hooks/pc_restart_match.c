/*
 * Mod: Instant Rematch / Restart Match Shortcut (L3 + R3)
 *
 * Allows restarting the active fight in Story Mode and Battle Mode by holding
 * both thumbstick buttons (L3 + R3 / Left Stick Click + Right Stick Click)
 * for 300ms.
 *
 * Works in live combat, during pause, and on KO / match end.
 */

#include "host.h"
#include "pc_restart_match.h"
#include "guest_call.h"
#if defined(__has_include) && __has_include("pc_speech_subs.h")
#include "pc_speech_subs.h"
#define HAVE_SPEECH_SUBS 1
#endif
#include "input_host.h"
#include "xinput_xbox.h"
#include "recomp/gen/recomp_funcs.h"
#include "recomp/gen/recomp_types.h"
#include <stdio.h>
#include <stdint.h>

#define GAMEDATA_SLOT     0x18u
#define MODE_MGR_SLOT     0x17u
#define MANAGERS          0x002FB148u
#define REMATCH_FLAGS_VA  0x0037514Cu
#define RESTART_HOLD_MS   300u

static uint64_t g_hold_start_ms = 0;
static int      g_triggered_while_held = 0;

static int is_mode_7a_vtable(uint32_t fight_mode)
{
    uint32_t vtbl = fight_mode ? MEM32(fight_mode) : 0u;
    return vtbl && MEM32(vtbl + 0x10u) == 0x0007A8F0u;
}

static int is_l3_r3_held(void)
{
    const uint16_t combo = XBOX_GAMEPAD_LEFT_THUMB | XBOX_GAMEPAD_RIGHT_THUMB;
    int host_active = xbox_HostInputActive();

    if (host_active) {
        for (int slot = 0; slot < 4; slot++) {
            InputRaw raw;
            if (xbox_HostInputRawPad(slot, &raw) &&
                raw.src[INPUT_SRC_LEFT_STICK_CLICK] >= 16384 &&
                raw.src[INPUT_SRC_RIGHT_STICK_CLICK] >= 16384) {
                return 1;
            }
        }
    }

    for (int port = 0; port < 4; port++) {
        XBOX_INPUT_STATE state;
        DWORD res = host_active
            ? xbox_HostInputCurrentState(port, &state)
            : xbox_InputGetState((DWORD)port, &state);
        if (res == ERROR_SUCCESS && ((state.Gamepad.wButtons & combo) == combo)) {
            return 1;
        }
    }

    return 0;
}

static void trigger_fight_restart(uint32_t mode_mgr, uint32_t fight_mode)
{
#ifdef HAVE_SPEECH_SUBS
    pc_speech_subs_reset();
#endif

    int is_mode_7a = is_mode_7a_vtable(fight_mode);
    /* If pause menu controller (+0x38 / +0x40) is active (+8 != 0), close it first */
    uint32_t pause_ctrl = MEM32(fight_mode + (is_mode_7a ? 0x40u : 0x38u));
    if (pause_ctrl != 0 && MEM32(pause_ctrl + 8u) != 0) {
        guest_call(sub_0006BB70, pause_ctrl, 0, NULL);
    }

    /* Clear any pending fight end result and set the engine's Rematch flag (0x400) */
    MEM32(fight_mode + 0x24u) = 0;
    MEM32(REMATCH_FLAGS_VA) |= 0x400u;

    /* Request Game Mode Manager (0x17) to tear down and re-init the active Fight Mode */
    guest_call(sub_00077020, mode_mgr, 0, NULL);

    uint32_t gd = MEM32(MANAGERS + GAMEDATA_SLOT * 4u);
    fprintf(stderr, "[REMATCH] L3 + R3 held! Restarting fight via mode_mgr=%08X fight_mode=%08X (Mode=%u)\n",
            mode_mgr, fight_mode, gd ? MEM32(gd + 0x344u) : 0u);
    fflush(stderr);
}

void pc_restart_match_trigger(void)
{
    uint32_t mode_mgr = MEM32(MANAGERS + MODE_MGR_SLOT * 4u);
    uint32_t fight_mode = mode_mgr ? MEM32(mode_mgr + 0x18u) : 0u;
    if (!mode_mgr || !fight_mode) {
        return;
    }
    trigger_fight_restart(mode_mgr, fight_mode);
}

void pc_restart_match_check(void)
{
    uint32_t mode_mgr = MEM32(MANAGERS + MODE_MGR_SLOT * 4u);
    uint32_t fight_mode = mode_mgr ? MEM32(mode_mgr + 0x18u) : 0u;
    int is_mode_7a = is_mode_7a_vtable(fight_mode);
    uint32_t match_obj = fight_mode ? MEM32(fight_mode + (is_mode_7a ? 0x2Cu : 0x28u)) : 0u;
    if (!mode_mgr || !fight_mode || !match_obj || MEM32(mode_mgr + 0x24u) != 0) {
        g_hold_start_ms = 0;
        g_triggered_while_held = 0;
        return;
    }

    int held = is_l3_r3_held();
    uint64_t now = GetTickCount64();

    if (held) {
        if (!g_hold_start_ms) {
            g_hold_start_ms = now;
        } else if (!g_triggered_while_held && (now - g_hold_start_ms >= RESTART_HOLD_MS)) {
            g_triggered_while_held = 1;
            trigger_fight_restart(mode_mgr, fight_mode);
        }
    } else {
        g_hold_start_ms = 0;
        g_triggered_while_held = 0;
    }
}
