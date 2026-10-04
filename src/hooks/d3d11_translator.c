/*
 * Stand up a Direct3D 11 device for the push-buffer translator to draw through.
 *
 * This title's Direct3D 8 is statically linked into the XBE, so it was
 * recompiled along with the game and never calls the runtime's own Direct3D.
 * That leaves the runtime's translator, src/nv2a/nv2a_pgraph_d3d11.c, with no
 * device: it renders through xbox_GetD3DDevice(), which only returns one after
 * something has gone through the factory's CreateDevice path.
 *
 * So the host program creates it. Nothing about it is the title's: it is our
 * window, our swap chain, and the title never learns it exists. The title
 * keeps building its own command stream exactly as it did, the executor in
 * src/kernel/nv2a_pb_exec.c keeps decoding it, and each decoded method is
 * handed to the translator, which turns it into draw calls against this
 * device.
 *
 * That is the documented upgrade path away from the executor's software
 * rasteriser, which can only draw flat untextured geometry already in screen
 * space. It also avoids the alternative, which is identifying and replacing
 * every Direct3D 8 entry point in the lifted image by address; this route
 * needs no symbols at all, because the command stream is the interface.
 *
 * Opt-in through RECOMP_PB_D3D11, which the same variable gates in the
 * executor. Without it nothing here runs and the software path is unchanged.
 */

#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "d3d8_xbox.h"
#include "nv2a_pgraph_d3d11.h"

/* The title sets a 640x480 mode. Matching it keeps the translator's screen
 * space and ours the same, so a vertex the title placed at 320,240 lands in
 * the middle rather than somewhere that needs explaining. */
#define TRANSLATOR_WIDTH   640
#define TRANSLATOR_HEIGHT  480

static void capture_backbuffer(IDirect3DDevice8 *dev);

static HWND  s_window;
static int   s_ready;

void d3d11_translator_pump(void);
void d3d11_translator_report(void);

static LRESULT CALLBACK translator_wndproc(HWND h, UINT msg, WPARAM wp, LPARAM lp)
{
    /* Closing the window ends the run. Left to DefWindowProc it would destroy
     * the window and leave the title running with nothing to draw into; the
     * log line keeps a deliberate close from reading like a crash. */
    if (msg == WM_CLOSE) {
        fprintf(stderr, "[TRANS] window closed by the user; exiting\n");
        fflush(stderr);
        fflush(stdout);
        TerminateProcess(GetCurrentProcess(), 0);
    }
    return DefWindowProcW(h, msg, wp, lp);
}

static HWND make_window(void)
{
    WNDCLASSEXW wc;
    RECT r;

    memset(&wc, 0, sizeof(wc));
    wc.cbSize        = sizeof(wc);
    wc.lpfnWndProc   = translator_wndproc;
    wc.hInstance     = GetModuleHandleW(NULL);
    wc.hCursor       = LoadCursorW(NULL, IDC_ARROW);
    wc.lpszClassName = L"DefJamRecompTranslator";
    RegisterClassExW(&wc);

    r.left = 0; r.top = 0; r.right = TRANSLATOR_WIDTH; r.bottom = TRANSLATOR_HEIGHT;
    AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);

    return CreateWindowExW(0, L"DefJamRecompTranslator",
                           L"Def Jam: Fight for NY", WS_OVERLAPPEDWINDOW,
                           CW_USEDEFAULT, CW_USEDEFAULT,
                           r.right - r.left, r.bottom - r.top,
                           NULL, NULL, GetModuleHandleW(NULL), NULL);
}

/* The window lives on a thread of its own, which creates it and then does
 * nothing but pump its messages.
 *
 * A window's messages go to the thread that created it. This one used to be
 * created on the main thread, which then becomes the title's main thread and
 * never looks at its queue again, while the pump ran on the GPU executor's
 * thread -- where PeekMessage sees only that thread's own windows. Nothing
 * ever serviced the window. That went unnoticed until something needed an
 * answer from it: a click, focus leaving or returning, Alt-Tab. Five seconds
 * later Windows marked it Not Responding and painted a frozen ghost over it
 * for good. Direct3D presents from the executor thread as before; a swap
 * chain does not need its window's thread, only for that thread to answer. */
static HANDLE s_window_ready;

static DWORD WINAPI window_thread(LPVOID unused)
{
    MSG msg;
    (void)unused;
    s_window = make_window();
    if (s_window)
        ShowWindow(s_window, SW_SHOW);
    SetEvent(s_window_ready);
    if (!s_window)
        return 1;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return 0;
}

int d3d11_translator_init(void)
{
    IDirect3D8 *d3d;
    IDirect3DDevice8 *dev = NULL;
    D3DPRESENT_PARAMETERS pp;
    HRESULT hr;

    if (s_ready)
        return 1;
    if (!getenv("RECOMP_PB_D3D11"))
        return 0;

    s_window_ready = CreateEventW(NULL, TRUE, FALSE, NULL);
    {
        HANDLE th = s_window_ready ? CreateThread(NULL, 0, window_thread, NULL, 0, NULL) : NULL;
        if (!th) {
            fprintf(stderr, "[TRANS] could not start the window thread (error %lu)\n",
                    GetLastError());
            return 0;
        }
        CloseHandle(th);
    }
    WaitForSingleObject(s_window_ready, INFINITE);
    if (!s_window) {
        fprintf(stderr, "[TRANS] could not create a window\n");
        return 0;
    }

    d3d = xbox_Direct3DCreate8(0);
    if (!d3d) {
        fprintf(stderr, "[TRANS] Direct3DCreate8 returned nothing\n");
        return 0;
    }

    memset(&pp, 0, sizeof(pp));
    pp.BackBufferWidth        = TRANSLATOR_WIDTH;
    pp.BackBufferHeight       = TRANSLATOR_HEIGHT;
    pp.BackBufferFormat       = D3DFMT_A8R8G8B8;
    pp.BackBufferCount        = 1;
    pp.SwapEffect             = D3DSWAPEFFECT_DISCARD;
    pp.hDeviceWindow          = s_window;
    pp.Windowed               = TRUE;
    pp.EnableAutoDepthStencil = FALSE;

    hr = d3d->lpVtbl->CreateDevice(d3d, 0, 1 /* HAL */, s_window,
                                   0x00000040 /* SOFTWARE_VERTEXPROCESSING */,
                                   &pp, &dev);
    if (FAILED(hr) || !dev) {
        fprintf(stderr, "[TRANS] CreateDevice failed (0x%08lX)\n", (unsigned long)hr);
        return 0;
    }

    pgraph_d3d11_init();
    s_ready = 1;
    fprintf(stderr, "[TRANS] D3D11 translator ready: %ux%u window, "
                    "push-buffer methods will be forwarded\n",
            TRANSLATOR_WIDTH, TRANSLATOR_HEIGHT);
    fflush(stderr);
    return 1;
}

/* Put the frame on screen.
 *
 * pgraph_d3d11_flush() submits whatever geometry was still batched and counts
 * the frame, but it does not present: the translator draws into a device it
 * did not create and does not own the swap chain. So the host presents, which
 * is also where the window has to be pumped and the counters read. Without
 * this every frame is rendered correctly and then discarded, which looks
 * exactly like a renderer that does nothing. */
void d3d11_translator_frame_end(void)
{
    IDirect3DDevice8 *dev;

    if (!s_ready)
        return;
    dev = xbox_GetD3DDevice();
    if (dev) {
        capture_backbuffer(dev);
        dev->lpVtbl->Present(dev, NULL, NULL, NULL, NULL);
    }
    d3d11_translator_pump();
    d3d11_translator_report();
}

/* Save what was actually rendered, straight out of the back buffer.
 *
 * Needed because the alternative is screenshotting the desktop, which catches
 * whatever else is on it. This reads only our own render target, so it is
 * bounded to the thing being tested, and it is also what the golden-image
 * comparison in docs/02-test-plan.md needs.
 *
 * Writes a 24-bit BMP, which needs no library and which anything opens. Set
 * RECOMP_TRANS_SHOT=<path> and the next presented frame lands there. */
static void capture_backbuffer(IDirect3DDevice8 *dev)
{
    const char *path = getenv("RECOMP_TRANS_SHOT");
    IDirect3DSurface8 *surf = NULL;
    D3DLOCKED_RECT lr;
    FILE *f;
    uint32_t w = TRANSLATOR_WIDTH, h = TRANSLATOR_HEIGHT;
    uint32_t row = ((w * 3) + 3) & ~3u;
    uint8_t hdr[54];
    uint32_t y, x, size;
    extern unsigned d3d8_GetRenderScale(void);
    uint32_t sc = d3d8_GetRenderScale();

    char named[512];
    /* The frames the caller asked for, ascending. One frame writes to the path
     * as given; a list ("1300,1900,2600") writes one file per frame with the
     * frame number before the extension, so a single run shows when the
     * picture changes. The first few frames are cleared and nothing else,
     * because the title is still loading, so frame zero says nothing. */
    static uint32_t want[16];
    static int nwant = -1, next;
    static uint32_t seen;
    /* Or by time: RECOMP_TRANS_SHOT_SECS=150,165.5 takes the first frame
     * presented after each point, in seconds since process start (or since
     * RECOMP_SCRIPT_ANCHOR's file open) -- the clock
     * RECOMP_PAD_SCRIPT uses. Frame numbers drift by hundreds between runs, so
     * a frame list cannot be aimed at the screen a scripted press leads to.
     * Files are named <stem>-<secs>s<ext>. An "@file#N" entry puts the times
     * after it on xbox_FileOpenSeconds's clock instead, as in RECOMP_PAD_SCRIPT:
     * RECOMP_TRANS_SHOT_SECS=20,@main.mus#1,3,10. */
    static double want_secs[16];
    static char want_base[16][64];
    static int by_secs;
    double now_secs = 0.0;

    if (!path || !*path)
        return;
    if (nwant < 0) {
        const char *s = getenv("RECOMP_TRANS_SHOT_FRAME");
        const char *t = getenv("RECOMP_TRANS_SHOT_SECS");
        nwant = 0;
        if (t && *t) {
            by_secs = 1;
            s = t;
        }
        while (s && *s && nwant < 16) {
            char *end;
            if (by_secs && *s == '@') {
                size_t n = strcspn(s + 1, ",");
                char base[64];
                int k;
                snprintf(base, sizeof base, "%.*s", (int)n, s + 1);
                for (k = nwant; k < 16; k++)
                    strcpy(want_base[k], base);
                {
                    /* A watch starts at its first query: make it now. */
                    extern double xbox_FileOpenSeconds(const char *spec);
                    (void)xbox_FileOpenSeconds(base);
                }
                s += 1 + n;
                s = (*s == ',') ? s + 1 : "";
                continue;
            }
            if (by_secs)
                want_secs[nwant++] = strtod(s, &end);
            else
                want[nwant++] = (uint32_t)strtoul(s, &end, 0);
            s = (*end == ',') ? end + 1 : "";
        }
    }
    if (by_secs) {
        extern double xbox_ScriptSeconds(void);   /* honours RECOMP_SCRIPT_ANCHOR */
        extern double xbox_FileOpenSeconds(const char *spec);
        if (next >= nwant)
            return;
        now_secs = want_base[next][0] ? xbox_FileOpenSeconds(want_base[next])
                                      : xbox_ScriptSeconds();
        if (now_secs < 0.0 || now_secs < want_secs[next])
            return;
    } else if (nwant > 0 && (next >= nwant || seen++ < want[next])) {
        return;
    }
    if (nwant > 1 || by_secs) {
        const char *dot = strrchr(path, '.');
        int stem = dot ? (int)(dot - path) : (int)strlen(path);
        if (by_secs)
            snprintf(named, sizeof(named), "%.*s-%gs%s", stem, path, want_secs[next],
                     dot ? dot : "");
        else
            snprintf(named, sizeof(named), "%.*s-%u%s", stem, path, seen - 1,
                     dot ? dot : "");
        path = named;
    }
    if (FAILED(dev->lpVtbl->GetBackBuffer(dev, 0, 0, &surf)) || !surf)
        return;
    memset(&lr, 0, sizeof(lr));
    if (FAILED(surf->lpVtbl->LockRect(surf, &lr, NULL, 0)) || !lr.pBits) {
        fprintf(stderr, "[TRANS] could not lock the back buffer\n");
        return;
    }

    f = fopen(path, "wb");
    if (f) {
        size = 54 + row * h;
        memset(hdr, 0, sizeof(hdr));
        hdr[0] = 'B'; hdr[1] = 'M';
        hdr[2] = (uint8_t)size; hdr[3] = (uint8_t)(size >> 8);
        hdr[4] = (uint8_t)(size >> 16); hdr[5] = (uint8_t)(size >> 24);
        hdr[10] = 54; hdr[14] = 40;
        hdr[18] = (uint8_t)w; hdr[19] = (uint8_t)(w >> 8);
        hdr[22] = (uint8_t)h; hdr[23] = (uint8_t)(h >> 8);
        hdr[26] = 1; hdr[28] = 24;
        fwrite(hdr, 1, sizeof(hdr), f);
        /* BMP rows run bottom to top. At a render scale above 1 the back
         * buffer is that many times the title's size, and each pixel written
         * is the mean of its sc x sc block -- what the window shows. */
        for (y = 0; y < h; y++) {
            uint32_t written = 0;
            /* The runtime's swap chain is R8G8B8A8 (d3d8_device.c), so the
             * locked bytes run R, G, B, A and a BMP wants B, G, R. Written in
             * the locked order, every capture had red and blue swapped -- skin
             * blue, a blue jersey orange, the Xbox B button blue -- while the
             * window was right. */
            for (x = 0; x < w; x++) {
                uint32_t sum[3] = { 0, 0, 0 }, i, j, c;
                for (j = 0; j < sc; j++) {
                    const uint8_t *src = (const uint8_t *)lr.pBits
                                       + (size_t)((h - 1 - y) * sc + j) * lr.Pitch;
                    for (i = 0; i < sc; i++)
                        for (c = 0; c < 3; c++)
                            sum[c] += src[(x * sc + i) * 4 + c];
                }
                for (c = 0; c < 3; c++) {
                    /* The title's gamma ramp is applied at presentation,
                     * after this read; apply it here so a capture is what
                     * the window shows (recomp_manual.c). */
                    extern uint8_t g_recomp_gamma[3][256];
                    extern int g_recomp_gamma_on;
                    sum[c] /= sc * sc;
                    if (g_recomp_gamma_on)
                        sum[c] = g_recomp_gamma[c][sum[c] & 0xFF];
                }
                fputc((int)sum[2], f);   /* B */
                fputc((int)sum[1], f);   /* G */
                fputc((int)sum[0], f);   /* R */
                written += 3;
            }
            while (written++ < row)
                fputc(0, f);
        }
        fclose(f);
        fprintf(stderr, "[TRANS] captured the back buffer to %s\n", path);
        {
            /* And, with RECOMP_PB_BATCH_DUMP=shot, the next frame's batches. */
            extern void nv2a_pb_request_dump_next(void);
            nv2a_pb_request_dump_next();
        }
        if (++next >= nwant)
            _putenv_s("RECOMP_TRANS_SHOT", "");   /* every requested frame taken */
    }
    surf->lpVtbl->UnlockRect(surf);
    fflush(stderr);
}

/* Kept for its callers: the window's own thread pumps it now (window_thread
 * above), and a PeekMessage here, on the executor's thread, could only ever
 * see that thread's windows. */
void d3d11_translator_pump(void)
{
}

/* What the translator actually did, which is the only way to tell "no methods
 * arrived" from "methods arrived and were all ignored" from "it drew and the
 * result is off screen". Called on a timer from the host so a run reports
 * without needing the title to exit. */
void d3d11_translator_report(void)
{
    static PgraphD3D11Stats prev;
    PgraphD3D11Stats st;

    if (!s_ready)
        return;
    pgraph_d3d11_get_stats(&st);
    if (memcmp(&st, &prev, sizeof(st)) == 0)
        return;
    prev = st;
    fprintf(stderr, "[TRANS] frames %u  draws %u  vertices %u  "
                    "methods handled %u ignored %u  clears %u\n",
            st.frames, st.draw_calls, st.vertices_submitted,
            st.methods_handled, st.methods_ignored, st.clears);
    fflush(stderr);
}
