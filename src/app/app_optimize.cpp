// Disk maintenance uses the same verified setup payload and installed data on every OS.
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <vector>

#include <SDL3/SDL.h>
#include "imgui.h"
#include "app.h"
#include "app_os.h"
#include "pc_ui_actions.h"
#include "pc_ui_internal.h"

namespace app {
namespace {
namespace fs = std::filesystem;
struct Optimization {
    os::Process process;
    fs::path scratch, answer, cancel, log;
    bool active = false, applying = false, cancelling = false;
    bool supported = false, ready = false;
    unsigned long long started = 0;
    std::string message;
} g_optimization;

void begin(bool apply)
{
    auto &job = g_optimization;
    job.active = true;
    job.applying = apply;
    job.cancelling = false;
    job.ready = false;
    job.message.clear();
    std::error_code ec;
    fs::create_directories(log_dir(), ec);
    if (ec) { job.message = "Could not prepare disk optimization: " + ec.message(); return; }
    job.scratch = log_dir() / (".disk-optimization-" +
        std::to_string(os::process_id()) + "-" + std::to_string(SDL_GetTicks()));
    fs::create_directories(job.scratch, ec);
    if (ec) { job.message = "Could not prepare disk optimization: " + ec.message(); return; }
    job.answer = job.scratch / "result.json";
    job.cancel = job.scratch / "cancel";
    job.log = log_dir() / ("disk-optimization-" + std::to_string(SDL_GetTicks()) + ".log");
    std::vector<std::string> args = {"--compact-save-images", "--install-dir", install().root.string(),
        "--optimization-result", job.answer.string(), "--cancel-file", job.cancel.string(), "--log", job.log.string()};
    if (apply) args.push_back("--apply-compaction");
    unlock_install();
    if (!spawn_engine(args, &job.process, &job.message)) {
        lock_install();
        fs::remove_all(job.scratch, ec);
    }
    job.started = SDL_GetTicks();
}

void poll_optimization()
{
    auto &job = g_optimization;
    if (!job.process.id) return;
    int code = os::finished(job.process);
    if (code < 0) return;
    auto answer = json_values(os::read_shared(job.answer));
    job.supported = answer["apply_supported"] == "true";
    job.ready = code == 0 && answer["kind"] == "disk-optimization-v1" && answer["status"] == "ready";
    job.message = answer["message"];
    if (job.message.empty()) job.message = "Disk optimization stopped. Open the log for details.";
    if (!lock_install()) {
        job.ready = false;
        job.message += " Close other copies of the game before returning to the launcher.";
    }
    std::error_code ec;
    fs::remove_all(job.scratch, ec);
}
} // namespace

bool disk_optimization_completed()
{
    auto marker = json_values(os::read_shared(install().data / "disk-optimization.json"));
    return marker["kind"] == "disk-optimization-v1" && marker["status"] == "complete";
}

void screen_open_optimization()
{
    if (!install().installed || screen_busy()) return;
    g_optimization = Optimization();
    begin(false); // Inspect first. No automatic compaction after an update or button press.
}

bool optimization_busy() { return g_optimization.process.id != 0; }

void optimization_request_cancel()
{
    if (!optimization_busy() || g_optimization.cancelling) return;
    std::ofstream marker(g_optimization.cancel);
    marker << "cancel";
    marker.close();
    if (!marker) {
        g_optimization.message = "Could not request cancellation. Try Cancel again or wait for optimization to finish.";
        return;
    }
    g_optimization.message.clear();
    g_optimization.cancelling = true;
}

bool optimization_screen_draw(float width, float height, UiResult *)
{
    auto &job = g_optimization;
    if (!job.active) return false;
    poll_optimization();
    page_begin(width, height, "OPTIMIZE DISK USAGE");
    if (optimization_busy()) {
        ImGui::TextWrapped("%s", job.cancelling ? "Stopping disk optimization..." :
            job.applying ? "Optimizing save images. Keep this window open until it finishes." : "Checking disk usage...");
        ImGui::TextDisabled("%u seconds elapsed", unsigned((SDL_GetTicks() - job.started) / 1000));
        if (!job.message.empty()) ImGui::TextWrapped("%s", job.message.c_str());
    } else {
        ImGui::TextWrapped("%s", job.message.c_str());
    }
    page_actions();
    if (optimization_busy()) {
        ImGui::BeginDisabled(job.cancelling);
        if (ImGui::Button("Cancel") || back_pressed()) optimization_request_cancel();
        ui_target("optimization.cancel");
        ImGui::EndDisabled();
    } else {
        if (job.ready && job.supported) {
            if (ImGui::Button("Optimize now")) begin(true);
            ui_target("optimization.apply");
            ImGui::SameLine();
        }
        if (ImGui::Button("Back") || back_pressed()) {
            if (lock_install()) job.active = false;
            else job.message = "Close other copies of the game before returning to the launcher.";
        }
        ui_target("optimization.back");
    }
    ImGui::SameLine();
    if (ImGui::Button("Open log")) pcui::open_path(job.log.string(), true);
    page_end();
    return true;
}
} // namespace app
