// The app's own updates (docs/research/unified-app-design-2026-10-26.md §4, D215).
//
// 1. Check. When the app starts, unless [launcher] check_updates is off, the setup engine looks on
//    GitHub for the newest stable release whose app is newer than this app's setup payload
//    (engine.py --check-app-update, setup/releases.py newest_app). An answer is kept for twelve
//    hours, and a check that fails says nothing. Home then shows the newer version.
// 2. Download. Update runs engine.py --stage-app: the release's app is downloaded and used only
//    after its GitHub digest, its checksum file, its provenance and the setup payload inside it
//    agree (releases.select_app). It is unpacked beside this app, hidden, on the same volume.
// 3. Swap. This bundle is renamed aside and the verified one renamed into its place; a failure
//    renames it back. The window closes and the new app is started in this process with
//    --updated. The new app removes the old bundle.
// 4. Build. The new app carries the new release's setup payload. Home offers to build it (after an
//    update it asks at once): a Clean Update of the installed game, while Play keeps the previous
//    build until the new one is activated.
//
// Only an app in a macOS bundle replaces itself for now; any other copy (a development build)
// points to the release page instead.

#define _CRT_SECURE_NO_WARNINGS
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include <SDL3/SDL.h>

#include "imgui.h"

extern "C" {
#include "recomp_settings.h"
}
#include "app.h"
#include "pc_ui_actions.h"
#include "pc_ui_internal.h"
#include "pc_ui_theme.h"

namespace fs = std::filesystem;

namespace app
{
namespace
{

const long long k_check_seconds = 12 * 60 * 60;

enum class Check
{
    Idle,
    Running,
    Done
};

enum class Stage
{
    None,
    Confirm,        // what the update does, and Download and update
    Downloading,
    Failed,
    NotBundle       // this copy cannot replace itself: the release page
};

Check g_check = Check::Idle;
pid_t g_check_pid = 0;
fs::path g_check_file;
std::string g_tag, g_version, g_url;    // the newer app, when there is one

Stage g_stage = Stage::None;
pid_t g_stage_pid = 0;
fs::path g_staged, g_scratch, g_status, g_cancel, g_log;
std::string g_line, g_error;
unsigned long long g_started_ms = 0;
bool g_cancelling = false, g_leave = false;

fs::path cache_dir()
{
    const char *home = getenv("HOME");
#if defined(__APPLE__)
    return home ? fs::path(home) / "Library/Caches/DefJamRecompiled" : fs::path();
#else
    const char *cache = getenv("XDG_CACHE_HOME");
    if (cache && *cache) return fs::path(cache) / "DefJamRecompiled";
    return home ? fs::path(home) / ".cache/DefJamRecompiled" : fs::path();
#endif
}

} // namespace

fs::path bundle_path()
{
    fs::path p = app::program();
    fs::path contents = p.parent_path().parent_path();
    if (p.parent_path().filename() != "MacOS" || contents.filename() != "Contents" ||
        contents.parent_path().extension() != ".app")
        return {};
    return contents.parent_path();
}

namespace
{

fs::path bundle() { return bundle_path(); }

fs::path beside(const fs::path &bundle, const char *suffix)
{
    return bundle.parent_path() / ("." + bundle.filename().string() + suffix);
}

std::map<std::string, std::string> read_keys(const fs::path &path)
{
    std::map<std::string, std::string> keys;
    std::ifstream f(path);
    std::string line;
    while (std::getline(f, line)) {
        size_t eq = line.find('=');
        if (eq != std::string::npos) keys[line.substr(0, eq)] = line.substr(eq + 1);
    }
    return keys;
}

std::string read_line(const fs::path &path)
{
    std::ifstream f(path);
    std::string line;
    std::getline(f, line);
    return line;
}

void take_answer(std::map<std::string, std::string> &keys)
{
    g_tag = g_version = g_url = "";
    if (keys.count("version") && app::newer(keys["version"], app::payload_version())) {
        g_tag = keys["tag"];
        g_version = keys["version"];
        g_url = keys["url"];
        fprintf(stderr, "[APP] update: v%s is available (%s)\n", g_version.c_str(), g_url.c_str());
    }
}

void start_check()
{
    g_check = Check::Done;
    if (!recomp_settings_get("launcher", "check_updates", 1) || app::payload().empty()) return;
    std::error_code ec;
    fs::create_directories(cache_dir(), ec);
    g_check_file = cache_dir() / "app-update.txt";
    auto keys = read_keys(g_check_file);
    long long checked = keys.count("checked") ? atoll(keys["checked"].c_str()) : 0;
    if (keys["current"] == app::payload_version() && time(nullptr) - checked < k_check_seconds) {
        take_answer(keys);
        return;
    }
    std::string error;
    fs::path result = g_check_file.string() + ".new";
    fs::remove(result, ec);
    if (!spawn_engine({"--check-app-update", result.string(), "--log", (app::log_dir() / "update-check.log").string()},
                      &g_check_pid, &error)) {
        fprintf(stderr, "[APP] update check: %s\n", error.c_str());
        return;
    }
    g_check = Check::Running;
}

void poll_check()
{
    if (g_check != Check::Running) return;
    int status = 0;
    if (waitpid(g_check_pid, &status, WNOHANG) != g_check_pid) return;
    g_check = Check::Done;
    g_check_pid = 0;
    fs::path result = g_check_file.string() + ".new";
    std::error_code ec;
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fprintf(stderr, "[APP] update check failed (see update-check.log); nothing shown\n");
        fs::remove(result, ec);
        return;
    }
    auto keys = read_keys(result);
    {
        std::ofstream out(result, std::ios::app);
        out << "checked=" << (long long)time(nullptr) << "\n";
    }
    fs::rename(result, g_check_file, ec);
    take_answer(keys);
}

void start_download()
{
    fs::path here = bundle();
    if (here.empty()) {
        g_stage = Stage::NotBundle;
        return;
    }
    std::error_code ec;
    g_staged = beside(here, ".update");
    fs::remove_all(g_staged, ec);                       // a download an earlier run left unfinished
    if (access(here.parent_path().c_str(), W_OK) != 0) {
        g_error = "This app cannot be replaced where it is (" + here.parent_path().string() +
                  " is not writable). Download v" + g_version + " from the release page instead.";
        g_stage = Stage::Failed;
        return;
    }
    char stamp[32];
    time_t now = time(nullptr);
    strftime(stamp, sizeof stamp, "%Y%m%d-%H%M%S", localtime(&now));
    g_scratch = fs::temp_directory_path(ec) / ("DefJamRecompiled-update-" + std::to_string(getpid()) + "-" + stamp);
    fs::create_directories(g_scratch, ec);
    g_status = g_scratch / "status.txt";
    g_cancel = g_scratch / "cancel";
    fs::create_directories(app::log_dir(), ec);
    g_log = app::log_dir() / ("update-" + std::string(stamp) + ".log");
    g_line.clear();
    g_error.clear();
    g_cancelling = false;
    fprintf(stderr, "[APP] update: downloading %s into %s, log %s\n", g_tag.c_str(), g_staged.c_str(), g_log.c_str());
    if (!spawn_engine({"--stage-app", g_tag, "--stage-dir", g_staged.string(), "--status-file", g_status.string(),
                       "--cancel-file", g_cancel.string(), "--log", g_log.string()},
                      &g_stage_pid, &g_error)) {
        g_stage = Stage::Failed;
        return;
    }
    g_started_ms = SDL_GetTicks();
    g_stage = Stage::Downloading;
}

// The verified bundle into this one's place. On success the new program is set to start when the
// window closes, and the window is asked to close.
void swap()
{
    fs::path here = bundle(), old = beside(here, ".old");
    std::error_code ec;
    fs::remove_all(old, ec);
    fs::rename(here, old, ec);
    if (ec) {
        g_error = "This app could not be moved aside (" + ec.message() + "). Nothing was changed.";
        g_stage = Stage::Failed;
        return;
    }
    fs::rename(g_staged, here, ec);
    if (ec) {
        std::error_code back;
        fs::rename(old, here, back);
        g_error = "The new app could not be put in place (" + ec.message() + "). This version is still installed.";
        g_stage = Stage::Failed;
        return;
    }
    fprintf(stderr, "[APP] update: v%s is in place at %s; starting it\n", g_version.c_str(), here.c_str());
    auto &next = app::relaunch();
    next = {(here / "Contents/MacOS/defjam_app").string()};
    for (const std::string &a : app::arguments())
        if (a != "--updated") next.push_back(a);
    next.push_back("--updated");
    g_leave = true;
}

void poll_download()
{
    if (g_stage != Stage::Downloading) return;
    std::string line = read_line(g_status);
    if (!line.empty()) g_line = line;
    int status = 0;
    if (waitpid(g_stage_pid, &status, WNOHANG) != g_stage_pid) return;
    g_stage_pid = 0;
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : 4;
    line = read_line(g_status);
    if (!line.empty()) g_line = line;
    std::error_code ec;
    fs::remove_all(g_scratch, ec);
    fprintf(stderr, "[APP] update: download ended, exit %d (%s)\n", code, g_line.c_str());
    if (code == 0) {
        swap();
        return;
    }
    fs::remove_all(g_staged, ec);
    g_error = code == 6 ? "The update was cancelled. Nothing was changed." : g_line.empty() ? "The update stopped." : g_line;
    g_stage = Stage::Failed;
}

std::string elapsed(unsigned long long ms)
{
    char text[32];
    snprintf(text, sizeof text, "%u:%02u", (unsigned)(ms / 60000), (unsigned)(ms / 1000 % 60));
    return text;
}

} // namespace

void update_cleanup()
{
    fs::path here = bundle();
    if (here.empty()) return;
    std::error_code ec;
    if (fs::exists(beside(here, ".old"), ec)) {
        fs::remove_all(beside(here, ".old"), ec);
        fprintf(stderr, "[APP] update: removed the previous app\n");
    }
}

bool update_busy() { return g_stage_pid != 0; }

void update_request_cancel()
{
    if (!g_stage_pid || g_cancelling) return;
    std::ofstream(g_cancel) << "cancel";
    g_cancelling = true;
}

bool update_screen_draw(float width, float height, UiResult *result)
{
    if (g_check == Check::Idle) start_check();
    poll_check();
    poll_download();
    if (g_leave) {
        result->leave = true;                           // main starts the new app when the window closes
        page_begin(width, height, "UPDATED");
        ImGui::TextWrapped("Starting Def Jam Recompiled v%s...", g_version.c_str());
        ImGui::End();
        return true;
    }
    switch (g_stage) {
    case Stage::None: return false;
    case Stage::Confirm:
        page_begin(width, height, "UPDATE THE APP");
        ImGui::TextWrapped("Def Jam Recompiled v%s is available; this app is v%s.", g_version.c_str(),
                           app::payload_version().c_str());
        ImGui::TextWrapped("The new app is downloaded from the project's GitHub release and checked against the "
                           "release's checksums before it replaces this one. Your game, saves and settings stay as "
                           "they are. Afterwards the app offers to build v%s.", g_version.c_str());
        ImGui::Spacing();
        if (pcui::play_button("DOWNLOAD AND UPDATE", ImVec2(ImGui::GetFontSize() * 15, ImGui::GetFrameHeight() * 1.8f), 24))
            start_download();
        ui_target("update.download");
        ImGui::SameLine();
        if (ImGui::Button("What's new")) pcui::open_path(g_url);
        ImGui::SameLine();
        if (ImGui::Button("Not now")) g_stage = Stage::None;
        ui_target("update.not-now");
        ImGui::End();
        return true;
    case Stage::Downloading:
        page_begin(width, height, "UPDATING THE APP");
        ImGui::TextWrapped("%s", g_cancelling ? "Cancelling..." : g_line.empty() ? "Starting..." : g_line.c_str());
        ImGui::TextDisabled("%s elapsed", elapsed(SDL_GetTicks() - g_started_ms).c_str());
        ImGui::Spacing();
        ImGui::BeginDisabled(g_cancelling);
        if (ImGui::Button("Cancel")) update_request_cancel();
        ui_target("update.cancel");
        ImGui::EndDisabled();
        ImGui::End();
        return true;
    case Stage::Failed:
        page_begin(width, height, "UPDATE STOPPED");
        ImGui::TextWrapped("%s", g_error.c_str());
        ImGui::Spacing();
        if (ImGui::Button("Back")) g_stage = Stage::None;
        ui_target("update.back");
        if (!g_url.empty()) {
            ImGui::SameLine();
            if (ImGui::Button("Release page")) pcui::open_path(g_url);
        }
        if (!g_log.empty()) {
            ImGui::SameLine();
            if (ImGui::Button("Open log")) pcui::open_path(g_log.string(), true);
        }
        ImGui::End();
        return true;
    case Stage::NotBundle:
        page_begin(width, height, "UPDATE THE APP");
        ImGui::TextWrapped("This copy of the app is not an installed application (a development build), so it "
                           "cannot replace itself. Get v%s from the release page.", g_version.c_str());
        ImGui::Spacing();
        if (ImGui::Button("Release page")) pcui::open_path(g_url);
        ImGui::SameLine();
        if (ImGui::Button("Back")) g_stage = Stage::None;
        ImGui::End();
        return true;
    }
    return false;
}

} // namespace app

// One line on Home, above the launcher's own: a newer app to download, or this app's version of the
// game to build. Drawn inside the launcher's Home (pc_ui.cpp, DEFJAM_APP).
void pc_app_home_notice()
{
    using namespace app;
    const Install &in = install();
    if (in.installed && newer(payload_version(), in.version)) {
        ImGui::TextColored(pcui::gold(), "v%s is ready to build; your game is v%s.", payload_version().c_str(),
                           in.version.c_str());
        ImGui::SameLine();
        if (ImGui::SmallButton("Build update")) start_update_build();
        ui_target("home.build-update");
    } else if (!g_version.empty()) {
        ImGui::TextColored(pcui::gold(), "Def Jam Recompiled v%s is available.", g_version.c_str());
        ImGui::SameLine();
        if (ImGui::SmallButton("Update")) g_stage = Stage::Confirm;
        ui_target("home.update");
        ImGui::SameLine();
        if (ImGui::SmallButton("What's new")) pcui::open_path(g_url);
    }
}
