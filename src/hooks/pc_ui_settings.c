/*
 * The launcher's and overlay's own settings, and the rule for when the launcher shows.
 *
 * Kept in plain C, apart from the Dear ImGui code, so the rule can be unit tested without a
 * window and the settings table builds without C++.
 */

#define _CRT_SECURE_NO_WARNINGS
#include <string.h>

#include "pc_ui.h"

size_t pc_ui_settings(RecompSetting *out, size_t max)
{
    size_t n = 0;
    if (max < 8) return 0;
    memset(out, 0, sizeof(*out) * 8);

#define ADD(...) do { RecompSetting s_ = { __VA_ARGS__ }; out[n++] = s_; } while (0)
    ADD("launcher", "skip", RECOMP_SETTING_BOOL, 0, 0, 0, NULL, "RECOMP_NO_LAUNCHER", 0,
        "Skip the launcher and start the game at once. Hold Shift while the game starts, start it with "
        "--launcher, or turn this off in the in-game overlay to see the launcher again.");
    ADD("ui", "overlay_key", RECOMP_SETTING_STRING, 0, 0, 0, NULL, NULL, 0,
        "The key that opens and closes the in-game overlay, one key name (see the [keyboard] section).",
        "F1");
    ADD("ui", "overlay_pad", RECOMP_SETTING_STRING, 0, 0, 0, NULL, NULL, 0,
        "Pad buttons that open and close the overlay. Alternatives are separated by commas; a combination "
        "of buttons joined with + must be held for half a second. Button names as in [gamepad]. "
        "Empty for none.",
        "guide, left_stick_click+right_stick_click");
    ADD("ui", "scale", RECOMP_SETTING_INT, 100, 60, 250, NULL, NULL, 0,
        "Size of the launcher and overlay text and controls in percent, on top of your display's scaling.");
#undef ADD
    return n;
}

int pc_launcher_wanted(int skip_setting, int force_flag, int no_flag, int shift_held, int test_run)
{
    if (test_run) return 0;
    if (no_flag) return 0;
    if (force_flag || shift_held) return 1;
    return skip_setting ? 0 : 1;
}
