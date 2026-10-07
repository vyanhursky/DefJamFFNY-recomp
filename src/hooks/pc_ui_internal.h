// What the launcher and the overlay share: the settings screen and the way it takes input.
#pragma once

#include <windows.h>
#include "imgui.h"

// The Win32 backend's message handler (its header only declares it in a comment).
extern LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

enum UiMode { UI_OVERLAY, UI_LAUNCHER };

struct UiResult {
    bool play = false;      // launcher: the Play button
    bool leave = false;     // launcher: Quit; overlay: Close
};

// A fresh ImGui context with the port's fonts and style, scaled for `window`'s display.
void ui_context_begin(HWND window);
void ui_context_end();

// Make the text and controls the right size for `window` (display scaling times [ui] scale).
void ui_apply_scale(HWND window);

// Once a frame, before ImGui::NewFrame: every pad's buttons become the menu's gamepad navigation.
void ui_feed_gamepad();

// A key, mouse button or wheel notch being learned for a binding takes the message. Returns true
// when it did, and the message should go no further. Window thread; call with the UI lock held.
bool ui_capture_message(HWND window, UINT msg, WPARAM wp, LPARAM lp);

// The settings screen, drawn into the whole of the current frame (launcher) or a panel (overlay).
UiResult ui_draw(UiMode mode, float x, float y, float width, float height);

// The current frame's pad-press detection runs here, so it is only done while a screen is showing.
bool ui_capturing();

// The lock that keeps the window thread's input events and the drawing thread out of ImGui at once.
void ui_lock();
void ui_unlock();
