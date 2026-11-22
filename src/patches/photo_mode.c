/* Photo Mode: freeze the fight screen tick, retain its world draw,
 * and publish a new camera through the game's own camera setter before culling.
 * All guest state is owned by the guest thread. Host UI only queries active. */
#define _CRT_SECURE_NO_WARNINGS
#include "photo_mode.h"
#include "host.h"
#include "input_host.h"
#include "input_map.h"
#include "hooks/pc_ui.h"
#include "hooks/guest_call.h"
#include "hooks/photo_capture.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void sub_00018F90(void);
extern void sub_000796A0(void);
extern void sub_00079E40_gen(void);
extern void sub_001ECF00(void);
extern void sub_001ECF10(void);
#define MATCH 0x349760u
#define VIEW_SLOT 0x2FB158u
static volatile LONG active;
static uint32_t owner_screen, view, projection;
static int pad, test_done, test_kind, test_ticks, live_ticks, entrance_ticks, victory_ticks, test_photo_done, enabled, draining;
static unsigned held_ms[4];
static ULONGLONG last_tick, entered;
static float entry_camera[12], pos[3], yaw, pitch, roll, fov, entry_fov;
static unsigned draw_count, frozen_hash;
static InputRaw previous;
static uint32_t candidate, candidate_vtable;
static unsigned frame_serial, rendered_serial = ~0u;
static int inside_redraw, missing_draws, force_only;
static ULONGLONG last_simulation;
static int panel = 1, settings, row, speed = 1, hud_hidden = 1, thirds, centre, invert_y, exit_after_capture;
static float look_speed = 1, entry_yaw, entry_pitch, entry_roll;
static const float speeds[4] = {12, 35, 80, 160};
static CRITICAL_SECTION status_lock;
static volatile LONG status_ready;
static PhotoModeStatus status;

static void status_enter(void)
{
    if (InterlockedCompareExchange(&status_ready, 1, 0) == 0) {
        InitializeCriticalSection(&status_lock);
        InterlockedExchange(&status_ready, 2);
    }
    while (InterlockedCompareExchange(&status_ready, 0, 0) != 2) Sleep(0);
    EnterCriticalSection(&status_lock);
}
static void status_publish(void)
{
    status_enter();
    status.panel=panel; status.settings=settings; status.row=row; status.speed=speed;
    status.hud_hidden=hud_hidden; status.thirds=thirds; status.centre=centre; status.invert_y=invert_y;
    status.fov=fov; status.roll=roll*180.0f/3.14159265358979323846f; status.look_speed=look_speed;
    LeaveCriticalSection(&status_lock);
}
void photo_mode_status(PhotoModeStatus *out)
{
    status_enter(); *out = status; LeaveCriticalSection(&status_lock);
    out->active = photo_mode_active();
}
void photo_mode_capture_result(const char *message)
{
    status_enter();
    snprintf(status.message, sizeof(status.message), "%s", message);
    LeaveCriticalSection(&status_lock);
}
int photo_mode_hide_hud(void)
{
    return photo_mode_active() && (hud_hidden || photo_capture_waiting());
}
int photo_mode_hide_panel(uint32_t object)
{
    if (!photo_mode_active() || !candidate) return 0;
    return object == MEM32(candidate + (candidate_vtable == 0x29D5E4u ? 0x38u : 0x40u));
}
int photo_mode_hide_pause(uint32_t object)
{
    if (!photo_mode_active() || !candidate) return 0;
    return object == MEM32(candidate + (candidate_vtable == 0x29D5E4u ? 0x2Cu : 0x34u));
}
static void reset_camera(void)
{
    memcpy(pos, entry_camera, sizeof(pos));
    yaw=entry_yaw; pitch=entry_pitch; roll=entry_roll; fov=entry_fov;
    fprintf(stderr,"[PHOTO] reset fov=%.2f roll=%.2f pos=%.2f,%.2f,%.2f\n",fov,roll,pos[0],pos[1],pos[2]);
}
static int pressed(const InputRaw *raw, int control)
{
    return raw->src[control] > 16384 && previous.src[control] <= 16384;
}
static void setting_change(int direction)
{
    switch (row) {
    case 0: fov += direction; break;
    case 1: roll += direction * (5.0f * 3.14159265358979323846f / 180.0f); break;
    case 2: speed = (speed + direction + 4) % 4; break;
    case 3: look_speed += direction * 0.25f; break;
    case 4: invert_y = !invert_y; break;
    case 5: hud_hidden = !hud_hidden; break;
    case 6: thirds = !thirds; break;
    case 7: centre = !centre; break;
    }
    if (look_speed < 0.25f) look_speed=0.25f;
    if (look_speed > 3) look_speed=3;
    if (roll < -3.14159265358979323846f) roll=-3.14159265358979323846f;
    if (roll > 3.14159265358979323846f) roll=3.14159265358979323846f;
    if (getenv("RECOMP_PHOTO_TRACE"))
        fprintf(stderr,"[PHOTO] setting row=%d fov=%.2f roll=%.2f speed=%d look=%.2f invert=%d hud_hidden=%d thirds=%d centre=%d\n",
            row,fov,roll,speed,look_speed,invert_y,hud_hidden,thirds,centre);
}

void photo_mode_simulation_step(void) { last_simulation = GetTickCount64(); }
void photo_mode_result_boundary(void)
{
    /* Test fixture: select 8AB00's extro branch only after a natural result.
     * The transient decision word is otherwise rewritten by input updates. */
    if (test_kind == 4 && !test_done && (MEM32(0x3BE0F4u) & 8u) && !(MEM32(0x3BE0F8u) & 0x40u)) {
        fprintf(stderr,"[PHOTO] fixture select victory branch flags=%08X -> %08X\n",
            MEM32(0x3BE0F8u), MEM32(0x3BE0F8u) | 0x40u);
        MEM32(0x3BE0F8u) |= 0x40u;
    }
}
static int fight_was_paused(void)
{
    uint32_t state = MEM32(MATCH + 0x2D820);
    return (state == 5 || state == 8) && last_simulation && GetTickCount64() - last_simulation > 200;
}

int photo_mode_active(void) { return InterlockedCompareExchange(&active, 0, 0) != 0; }
int photo_mode_freeze(uint32_t screen)
{
    return (photo_mode_active() && screen == owner_screen) || draining;
}
static float axis(int value)
{
    float x = value / 32767.0f;
    if (fabsf(x) < 0.18f) return 0;
    return (x > 0 ? x - 0.18f : x + 0.18f) / 0.82f;
}
static unsigned scene_hash(void)
{
    unsigned h = 2166136261u, i, j;
    /* Simulation-owned fighter fields, not render caches. */
    for (i = 0; i < 4; i++)
        for (j = 0x28; j < 0x1CC; j++) h = (h ^ MEM8(0x3B92E0u + i * 0x12E8u + j)) * 16777619u;
    for (i = 0; i < 8; i++) h = (h ^ MEM8(0x3B9030u + i)) * 16777619u;
    return h;
}
static void publish(const float camera[12], float lens)
{
    uint32_t args[4] = {0x2DBF38u, 0x2DBF48u, 0x2DBF58u, 0};
    uint32_t seh = g_seh_ebp, flags = g_eflags;
    int df = g_df, cmp = g_fp_cmp;
    uint16_t control = g_fp_control_word, cc = g_fp_cc;
    double fp[8];
    RecompXmm xmm[8] = {g_xmm0,g_xmm1,g_xmm2,g_xmm3,g_xmm4,g_xmm5,g_xmm6,g_xmm7};
    /* Preserve the game camera source; the photo camera is temporary render state. */
    unsigned char saved[48];
    memcpy(fp, g_fp_stack, sizeof(fp));
    memcpy(saved, (const void *)XBOX_PTR(0x2DBF38u), 48);
    memcpy((void *)XBOX_PTR(0x2DBF38u), camera, 48);
    guest_call(sub_00018F90, view, 4, args);
    memcpy((void *)XBOX_PTR(0x2DBF38u), saved, 48);
    g_seh_ebp = seh; g_eflags = flags; g_df = df; g_fp_cmp = cmp;
    g_fp_control_word = control; g_fp_cc = cc;
    memcpy(g_fp_stack, fp, sizeof(fp));
    g_xmm0=xmm[0]; g_xmm1=xmm[1]; g_xmm2=xmm[2]; g_xmm3=xmm[3];
    g_xmm4=xmm[4]; g_xmm5=xmm[5]; g_xmm6=xmm[6]; g_xmm7=xmm[7];
    MEMF(projection + 0xC) = lens;
    MEM32(projection + 0x3C) |= 2;
}
void photo_mode_cancel(void)
{
    if (!photo_mode_active()) return;
    photo_capture_cancel_pending();
    /* Scene teardown calls this before the view is destroyed. */
    if (view && projection) publish(entry_camera, entry_fov);
    InterlockedExchange(&active, 0);
    xbox_HostInputSetUiActive(pc_ui_overlay_open());
    fprintf(stderr, "[PHOTO] exit draws=%u frozen=%s module=%u flags=%08X scale=%.2f\n", draw_count,
            scene_hash() == frozen_hash ? "yes" : "NO", MEM32(MEM32(owner_screen + 4) + 0x24), MEM32(0x39C0C0u), MEMF(MATCH + 4));
    draining = 1;
    xbox_HostInputSetUiActive(1);
    /* Keep ownership until the releasing input has drained. */
}
static int begin(uint32_t screen, int slot, const InputRaw *raw)
{
    float dx, dy, dz;
    view = MEM32(VIEW_SLOT);
    if (!view || (view & 0x7FFFFFFFu) >= 0x08000000u) return 0;
    projection = MEM32(view + 0x34);
    if (!projection || (projection & 0x7FFFFFFFu) >= 0x08000000u) return 0;
    /* The documented CINEMA path uses projection mode 1. Retain only the
     * full-screen fight view here; screen ownership is the primary gate. */
    if (MEM32(projection + 0x10) != 0) return 0;
    memcpy(entry_camera, (const void *)XBOX_PTR(view + 0x4C), sizeof(entry_camera));
    entry_fov = MEMF(projection + 0xC);
    dx = entry_camera[4] - entry_camera[0];
    dy = entry_camera[5] - entry_camera[1];
    dz = entry_camera[6] - entry_camera[2];
    if (!isfinite(entry_fov) || entry_fov < 1 || entry_fov > 170 ||
        !isfinite(dx + dy + dz) || dx*dx + dy*dy + dz*dz < 0.00001f) return 0;
    memcpy(pos, entry_camera, sizeof(pos));
    yaw = atan2f(dx, dz); pitch = atan2f(dy, sqrtf(dx*dx + dz*dz));
    entry_yaw = yaw; entry_pitch = pitch;
    {
        float right[3] = {-cosf(yaw),0,sinf(yaw)};
        float up[3] = {-sinf(yaw)*sinf(pitch),cosf(pitch),-cosf(yaw)*sinf(pitch)};
        entry_roll = atan2f(entry_camera[8]*right[0] + entry_camera[9]*right[1] + entry_camera[10]*right[2],
                           entry_camera[8]*up[0] + entry_camera[9]*up[1] + entry_camera[10]*up[2]);
    }
    roll = entry_roll; fov = entry_fov; pad = slot; previous = *raw;
    panel = 1; settings = 0; row = 0; exit_after_capture = test_photo_done = 0;
    owner_screen = screen; entered = GetTickCount64(); draw_count = 0;
    force_only = fight_was_paused();
    frozen_hash = scene_hash();
    xbox_HostInputSetUiActive(1);
    InterlockedExchange(&active, 1);
    photo_mode_capture_result(""); status_publish();
    fprintf(stderr, "[PHOTO] enter screen=%08X state=%u phase=%u module=%u flags=%08X scale=%.2f origin_paused=%d fov=%.2f pos=%.2f,%.2f,%.2f hash=%08X\n",
        screen, MEM32(MATCH + 0x2D820), MEM32(screen + 0x24),
        MEM32(MEM32(screen + 4) + 0x24), MEM32(0x39C0C0u), MEMF(MATCH + 4), force_only, fov, pos[0],pos[1],pos[2],frozen_hash);
    return 1;
}
int photo_mode_tick(uint32_t screen)
{
    ULONGLONG now = GetTickCount64();
    float dt = last_tick ? (float)(now - last_tick) / 1000.0f : 0;
    uint32_t state = MEM32(MATCH + 0x2D820);
    InputRaw raw;
    int i;
    static int configured;
    static uint32_t trace_state = ~0u, trace_pause = ~0u, trace_module = ~0u, trace_flags = ~0u;
    if (!configured) {
        const char *test = getenv("RECOMP_PHOTO_TEST");
        const char *opt = getenv("RECOMP_PHOTO_MODE");
        configured = 1;
        test_kind = !test ? 0 : !strcmp(test,"live") ? 1 : !strcmp(test,"paused") ? 2 :
                    !strcmp(test,"entrance") ? 3 : !strcmp(test,"victory") ? 4 : 0;
        enabled = test_kind || !opt || strcmp(opt, "0");
    }
    if (!enabled) return 0;
    last_tick = now;
    if (test_kind && (trace_state != state || trace_pause != MEM32(screen + 0x24) ||
        trace_module != MEM32(MEM32(screen + 4) + 0x24) || trace_flags != MEM32(0x39C0C0u))) {
        trace_state = state; trace_pause = MEM32(screen + 0x24);
        trace_module = MEM32(MEM32(screen + 4) + 0x24);
        trace_flags = MEM32(0x39C0C0u);
        fprintf(stderr,"[PHOTO] context state=%u screen24=%u module24=%u flags=%08X vtable=%08X scale=%.2f\n",
            state,trace_pause,trace_module,trace_flags,MEM32(screen),MEMF(MATCH + 4));
    }
    if (dt > 0.05f) dt = 0.05f;
    memset(&raw, 0, sizeof(raw));
    if (draining) {
        int held = 0, src;
        for (i = 0; i < 4; i++) {
            xbox_HostInputRawPad(i, &raw);
            for (src = 0; src < INPUT_SRC_COUNT; src++) held |= raw.src[src] > 8000;
            held |= abs(raw.lx) > 8000 || abs(raw.ly) > 8000 || abs(raw.rx) > 8000 || abs(raw.ry) > 8000;
        }
        if (!held) { draining = 0; owner_screen = 0; xbox_HostInputSetUiActive(pc_ui_overlay_open()); }
        return 1;
    }
    if (photo_mode_active()) {
        if (screen != owner_screen) { photo_mode_cancel(); return 0; }
        xbox_HostInputRawPad(pad, &raw);
        if (exit_after_capture && !photo_capture_waiting()) { photo_mode_cancel(); return 1; }
        if (pressed(&raw, INPUT_SRC_EAST)) {
            if (settings) settings = 0;
            else if (photo_capture_waiting()) exit_after_capture = 1;
            else { photo_mode_cancel(); previous = raw; return 1; }
        }
        if (test_kind && now - entered >= 6000) { photo_mode_cancel(); return 1; }
        if (test_kind == 4 && !test_photo_done && now - entered >= 2500) {
            photo_capture_request(); test_photo_done = 1;
        }
        if (pressed(&raw, INPUT_SRC_WEST)) panel = !panel;
        if (pressed(&raw, INPUT_SRC_NORTH)) { settings = !settings; panel = 1; }
        if (settings) {
            if (pressed(&raw, INPUT_SRC_DPAD_UP)) row = (row + 8) % 9;
            if (pressed(&raw, INPUT_SRC_DPAD_DOWN)) row = (row + 1) % 9;
            if (pressed(&raw, INPUT_SRC_DPAD_LEFT)) setting_change(-1);
            if (pressed(&raw, INPUT_SRC_DPAD_RIGHT)) setting_change(1);
            if (row == 8 && pressed(&raw, INPUT_SRC_SOUTH)) reset_camera();
        } else if (pressed(&raw, INPUT_SRC_SOUTH)) photo_capture_request();
        if (test_kind && (now - entered < 2000 || now - entered >= 4000)) {
            raw.lx = 14000; raw.rx = 6000;
        }
        if (settings || photo_capture_waiting()) {
            raw.lx=raw.ly=raw.rx=raw.ry=0;
            raw.src[INPUT_SRC_LEFT_TRIGGER]=raw.src[INPUT_SRC_RIGHT_TRIGGER]=0;
            raw.src[INPUT_SRC_LEFT_SHOULDER]=raw.src[INPUT_SRC_RIGHT_SHOULDER]=0;
        }
        yaw += axis(raw.rx) * dt * 1.5f * look_speed;
        pitch += axis(raw.ry) * dt * 1.2f * look_speed * (invert_y ? -1 : 1);
        if (pitch > 1.5f) pitch = 1.5f;
        if (pitch < -1.5f) pitch = -1.5f;
        for (i = 0; i < 3; i++) {
            float forward = i == 0 ? sinf(yaw)*cosf(pitch) : i == 1 ? sinf(pitch) : cosf(yaw)*cosf(pitch);
            float right = i == 0 ? -cosf(yaw) : i == 1 ? 0 : sinf(yaw);
            pos[i] += (forward * axis(raw.ly) + right * axis(raw.lx)) * speeds[speed] * dt;
        }
        pos[1] += (raw.src[INPUT_SRC_RIGHT_TRIGGER] - raw.src[INPUT_SRC_LEFT_TRIGGER]) / 32767.0f * speeds[speed] * dt;
        fov += (raw.src[INPUT_SRC_RIGHT_SHOULDER] - raw.src[INPUT_SRC_LEFT_SHOULDER]) / 32767.0f * 30 * dt;
        if (fov < 10) fov = 10;
        if (fov > 110) fov = 110;
        /* Preserve real button edges, not the flight-only neutralisation. */
        xbox_HostInputRawPad(pad, &previous);
        photo_mode_draw(screen);
        status_publish();
        return 1;
    }
    /* Loaded fight callbacks only: entrance, lead-in/combat, match decided,
     * and IntroExtro victory (8BE60 -> 89F20 -> A2EA0). Exclude loading,
     * teardown and unclassified states as well as nonzero screen phases. */
    if (MEM32(screen + 0x24) != 0 ||
        !(state == 3 || state == 4 || state == 5 || state == 8 || state == 9 || state == 10) || pc_ui_overlay_open()) {
        memset(held_ms, 0, sizeof(held_ms)); return 0;
    }
    test_ticks++;
    if (state == 3) entrance_ticks++;
    if (state == 10) victory_ticks++;
    if (state == 5 || state == 8) live_ticks++;
    if (test_kind && !test_done &&
        ((test_kind == 1 && (state == 5 || state == 8) && live_ticks > 120) ||
         (test_kind == 2 && fight_was_paused() && live_ticks > 120) ||
         (test_kind == 3 && state == 3 && entrance_ticks >= 15) ||
         (test_kind == 4 && state == 10 && victory_ticks >= 15))) {
        test_done = begin(screen, 0, &raw); return test_done;
    }
    for (i = 0; i < 4; i++) {
        int held = xbox_HostInputRawPad(i, &raw) && raw.src[INPUT_SRC_RIGHT_STICK_CLICK] > 16384 &&
                   raw.src[INPUT_SRC_DPAD_DOWN] > 16384;
        if (!held) held_ms[i] = 0;
        else if (!held_ms[i]) held_ms[i] = (unsigned)now;
        else if ((unsigned)now - held_ms[i] >= 500 && held_ms[i] != ~0u) {
            held_ms[i] = ~0u;
            if (begin(screen, i, &raw)) return 1;
        }
    }
    return 0;
}
void photo_mode_render(uint32_t screen)
{
    candidate = screen; candidate_vtable = MEM32(screen);
    rendered_serial = frame_serial;
    if (!inside_redraw) photo_mode_tick(screen);
}
void photo_mode_clear(void)
{
    photo_capture_cancel_pending();
    candidate = owner_screen = view = projection = 0;
    draining = 0; missing_draws = 0; force_only = 0; last_simulation = 0;
    InterlockedExchange(&active, 0);
    xbox_HostInputSetUiActive(pc_ui_overlay_open());
}
int photo_mode_frame(void)
{
    int seen;
    if (inside_redraw) return 0;
    seen = rendered_serial == frame_serial;
    frame_serial++;
    if (!candidate || MEM32(candidate) != candidate_vtable || MEM32(candidate + 0x24) != 0) return 0;
    if (!seen || force_only) {
        missing_draws++;
        photo_mode_tick(candidate);
        if (photo_mode_active()) {
            uint32_t seh = g_seh_ebp, flags = g_eflags;
            int df = g_df, cmp = g_fp_cmp;
            uint16_t control = g_fp_control_word, cc = g_fp_cc;
            double fp[8];
            const uint32_t lock_arg[1] = {0x2FB000u};
            RecompXmm xmm[8] = {g_xmm0,g_xmm1,g_xmm2,g_xmm3,g_xmm4,g_xmm5,g_xmm6,g_xmm7};
            memcpy(fp, g_fp_stack, sizeof(fp));
            force_only = 1;
            inside_redraw = 1;
            guest_call(sub_001ECF00, 0, 1, lock_arg);
            guest_call(candidate_vtable == 0x29D5E4u ? sub_000796A0 : sub_00079E40_gen, candidate, 0, NULL);
            guest_call(sub_001ECF10, 0, 1, lock_arg);
            inside_redraw = 0;
            g_seh_ebp=seh; g_eflags=flags; g_df=df; g_fp_cmp=cmp;
            g_fp_control_word=control; g_fp_cc=cc; memcpy(g_fp_stack,fp,sizeof(fp));
            g_xmm0=xmm[0]; g_xmm1=xmm[1]; g_xmm2=xmm[2]; g_xmm3=xmm[3];
            g_xmm4=xmm[4]; g_xmm5=xmm[5]; g_xmm6=xmm[6]; g_xmm7=xmm[7];
            return 1;
        }
        force_only = 0;
    } else missing_draws = 0;
    return 0;
}
void photo_mode_draw(uint32_t screen)
{
    float camera[12], forward[3], right[3], up[3];
    int i;
    if (!photo_mode_active() || screen != owner_screen) return;
    forward[0] = sinf(yaw)*cosf(pitch); forward[1] = sinf(pitch); forward[2] = cosf(yaw)*cosf(pitch);
    right[0] = -cosf(yaw); right[1] = 0; right[2] = sinf(yaw);
    up[0] = -sinf(yaw)*sinf(pitch); up[1] = cosf(pitch); up[2] = -cosf(yaw)*sinf(pitch);
    for (i = 0; i < 3; i++) {
        camera[i] = pos[i]; camera[4+i] = pos[i] + forward[i]*40;
        camera[8+i] = up[i]*cosf(roll) + right[i]*sinf(roll);
    }
    camera[3] = camera[7] = camera[11] = 1;
    publish(camera, fov);
    if (++draw_count % 60 == 0)
        fprintf(stderr,"[PHOTO] draw=%u frozen=%s hash=%08X pos=%.2f,%.2f,%.2f\n",draw_count,
            scene_hash() == frozen_hash ? "yes" : "NO",scene_hash(),pos[0],pos[1],pos[2]);
}
