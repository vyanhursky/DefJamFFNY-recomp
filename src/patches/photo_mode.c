/* Photo Mode prototype: freeze the fight screen tick, retain its world draw,
 * and publish a new camera through the game's own camera setter before culling.
 * All guest state is owned by the guest thread. Host UI only queries active. */
#define _CRT_SECURE_NO_WARNINGS
#include "photo_mode.h"
#include "host.h"
#include "input_host.h"
#include "input_map.h"
#include "hooks/pc_ui.h"
#include "hooks/guest_call.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void sub_00018F90(void);
#define MATCH 0x349760u
#define VIEW_SLOT 0x2FB158u
#define PI 3.14159265358979323846f
static volatile LONG active;
static uint32_t owner_screen, view, projection;
static int pad, test_done, test_kind, test_ticks, live_ticks, enabled, draining;
static unsigned held_ms[4];
static ULONGLONG last_tick, entered;
static float entry_camera[12], pos[3], yaw, pitch, roll, fov, entry_fov;
static unsigned draw_count, frozen_hash;
static InputRaw previous;

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
    /* Scene teardown calls this before the view is destroyed. */
    if (view && projection) publish(entry_camera, entry_fov);
    InterlockedExchange(&active, 0);
    xbox_HostInputSetUiActive(pc_ui_overlay_open());
    fprintf(stderr, "[PHOTO] exit draws=%u frozen=%s module=%u flags=%08X\n", draw_count,
            scene_hash() == frozen_hash ? "yes" : "NO", MEM32(MEM32(owner_screen + 4) + 0x24), MEM32(0x39C0C0u));
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
    memcpy(entry_camera, (const void *)XBOX_PTR(view + 0x4C), sizeof(entry_camera));
    entry_fov = MEMF(projection + 0xC);
    dx = entry_camera[4] - entry_camera[0];
    dy = entry_camera[5] - entry_camera[1];
    dz = entry_camera[6] - entry_camera[2];
    if (!isfinite(entry_fov) || entry_fov < 1 || entry_fov > 170 ||
        !isfinite(dx + dy + dz) || dx*dx + dy*dy + dz*dz < 0.00001f) return 0;
    memcpy(pos, entry_camera, sizeof(pos));
    yaw = atan2f(dx, dz); pitch = atan2f(dy, sqrtf(dx*dx + dz*dz));
    roll = 0; fov = entry_fov; pad = slot; previous = *raw;
    owner_screen = screen; entered = GetTickCount64(); draw_count = 0;
    frozen_hash = scene_hash();
    xbox_HostInputSetUiActive(1);
    InterlockedExchange(&active, 1);
    fprintf(stderr, "[PHOTO] enter screen=%08X state=%u pause=%u module=%u flags=%08X fov=%.2f pos=%.2f,%.2f,%.2f hash=%08X\n",
        screen, MEM32(MATCH + 0x2D820), MEM32(screen + 0x24),
        MEM32(MEM32(screen + 4) + 0x24), MEM32(0x39C0C0u), fov, pos[0],pos[1],pos[2],frozen_hash);
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
    uint32_t ui = MEM32(screen + (MEM32(screen) == 0x29D604u ? 0x38u : 0x40u));
    if (!configured) {
        const char *test = getenv("RECOMP_PHOTO_TEST");
        const char *opt = getenv("RECOMP_PHOTO_MODE");
        configured = 1;
        test_kind = !test ? 0 : !strcmp(test,"live") ? 1 : !strcmp(test,"paused") ? 2 :
                    !strcmp(test,"entrance") ? 3 : !strcmp(test,"victory") ? 4 : 0;
        enabled = test_kind || (opt && !strcmp(opt, "1"));
    }
    if (!enabled) return 0;
    last_tick = now;
    if (test_kind && (trace_state != state || trace_pause != MEM32(screen + 0x24) ||
        trace_module != MEM32(MEM32(screen + 4) + 0x24) || trace_flags != MEM32(0x39C0C0u))) {
        trace_state = state; trace_pause = MEM32(screen + 0x24);
        trace_module = MEM32(MEM32(screen + 4) + 0x24);
        trace_flags = MEM32(0x39C0C0u);
        fprintf(stderr,"[PHOTO] context state=%u screen24=%u module24=%u flags=%08X vtable=%08X ui=%08X enabled=%u\n",
            state,trace_pause,trace_module,trace_flags,MEM32(screen),ui,ui ? MEM8(ui + 4) : 0);
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
        if (raw.src[INPUT_SRC_EAST] && !previous.src[INPUT_SRC_EAST]) {
            photo_mode_cancel(); previous = raw; return 1;
        }
        if (test_kind && now - entered >= 6000) { photo_mode_cancel(); return 1; }
        if (test_kind && (now - entered < 2000 || now - entered >= 4000)) {
            raw.lx = 14000; raw.rx = 6000;
        }
        yaw += axis(raw.rx) * dt * 1.5f;
        pitch += axis(raw.ry) * dt * 1.2f;
        if (pitch > 1.5f) pitch = 1.5f;
        if (pitch < -1.5f) pitch = -1.5f;
        for (i = 0; i < 3; i++) {
            float forward = i == 0 ? sinf(yaw)*cosf(pitch) : i == 1 ? sinf(pitch) : cosf(yaw)*cosf(pitch);
            float right = i == 0 ? -cosf(yaw) : i == 1 ? 0 : sinf(yaw);
            pos[i] += (forward * axis(raw.ly) + right * axis(raw.lx)) * 45 * dt;
        }
        pos[1] += (raw.src[INPUT_SRC_RIGHT_TRIGGER] - raw.src[INPUT_SRC_LEFT_TRIGGER]) / 32767.0f * 35 * dt;
        fov += (raw.src[INPUT_SRC_RIGHT_SHOULDER] - raw.src[INPUT_SRC_LEFT_SHOULDER]) / 32767.0f * 30 * dt;
        if (fov < 10) fov = 10;
        if (fov > 110) fov = 110;
        previous = raw;
        photo_mode_draw(screen);
        return 1;
    }
    /* These wrappers are reached only by fight screens. Results use nonzero +24;
     * states 1..13 include loaded entrances/combat/victory, excluding teardown. */
    if (MEM32(screen + 0x24) != 0 || state < 1 || state > 13 || pc_ui_overlay_open()) {
        memset(held_ms, 0, sizeof(held_ms)); return 0;
    }
    test_ticks++;
    if (state == 5 || state == 8) live_ticks++;
    if (test_kind && !test_done &&
        ((test_kind == 1 && (state == 5 || state == 8) && live_ticks > 120) ||
         (test_kind == 2 && (state == 5 || state == 8) && (MEM32(0x39C0C0u) & 0x40u)) ||
         (test_kind == 3 && state < 4 && test_ticks > 30) ||
         (test_kind == 4 && state >= 9))) {
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
