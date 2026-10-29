// Add to Steam (Windows; design §7): Maintenance's Steam section adds the app to the player's Steam
// library as a non-Steam game that starts the game directly (--play), with the library artwork, and
// removes it again.
//
// The work is setup/engine.py --steam (setup/steam_shortcuts.py), run from the app's payload like the
// update check: it answers in a moment, in a JSON file this reads when it exits. Steam rewrites its
// list of games when it exits, so the list is changed only while Steam is closed. When Steam is
// running the section asks first, then the engine closes Steam (steam.exe -shutdown), makes the
// change and starts Steam again (--close-steam). Exit 4 means Steam was running and was not to be
// closed; 2 means it could not be done, and the message says why.

#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>

#include <filesystem>
#include <map>
#include <string>
#include <vector>

#include "imgui.h"

#include "app.h"
#include "app_os.h"
#include "pc_ui_actions.h"
#include "pc_ui_internal.h"

namespace fs = std::filesystem;

namespace app
{
namespace
{

struct Steam
{
    os::Process process;
    std::string action;                 // the request in flight: status, add or remove
    bool asked = false;                 // the status has been asked for since the page opened
    bool known = false;                 // an answer has arrived
    std::string root, user, message, details;
    bool running = false, added = false;
    bool confirm = false;               // asking whether Steam may be closed
    std::string confirm_action;
} g_steam;

fs::path folder() { return os::user_base() / "DefJamRecompiled"; }
fs::path answer_file() { return folder() / "steam-answer.json"; }

void ask(const std::string &action, bool close)
{
    std::error_code ec;
    fs::create_directories(folder(), ec);
    fs::remove(answer_file(), ec);
    std::vector<std::string> args = {"--steam", action, "--app-program", program().string(), "--steam-record",
                                     (folder() / "steam.json").string(), "--steam-result", answer_file().string()};
    if (!install().root.empty()) args.insert(args.end(), {"--install-dir", install().root.string()});
    if (close) args.push_back("--close-steam");
    std::string error;
    if (!spawn_engine(args, &g_steam.process, &error)) {
        g_steam.known = true;
        g_steam.message = error;
        return;
    }
    g_steam.action = action;
    fprintf(stderr, "[APP] steam: %s%s\n", action.c_str(), close ? " (closing Steam)" : "");
}

void poll()
{
    if (!g_steam.process.id) return;
    int code = os::finished(g_steam.process);
    if (code < 0) return;
    auto values = json_values(os::read_shared(answer_file()));
    g_steam.known = true;
    g_steam.root = values["steam"];
    g_steam.user = values["user"];
    g_steam.running = values["running"] == "true";
    g_steam.added = values["added"] == "true";
    g_steam.message = values.count("message") ? values["message"] : (code ? "Steam could not be changed" : "");
    g_steam.details = g_steam.action == "status" ? "" : values["details"];
    fprintf(stderr, "[APP] steam: %s exit %d; %s; %s\n", g_steam.action.c_str(), code,
            g_steam.added ? "in the library" : "not in the library", g_steam.message.c_str());
    if (code == 4) {                    // Steam started meanwhile: ask again
        g_steam.confirm = true;
        g_steam.confirm_action = g_steam.action;
        g_steam.details.clear();
    }
    g_steam.action.clear();
}

void request(const std::string &action)
{
    g_steam.details.clear();
    if (g_steam.running) {
        g_steam.confirm = true;
        g_steam.confirm_action = action;
    } else {
        ask(action, false);
    }
}

} // namespace

void steam_section()
{
    poll();
    if (!g_steam.asked) {
        g_steam.asked = true;
        ask("status", false);
    }
    ImGui::SeparatorText("Steam");
    bool busy = g_steam.process.id != 0;
    if (!g_steam.known) {
        ImGui::TextDisabled("Looking for Steam...");
        return;
    }
    if (g_steam.root.empty()) {
        ImGui::TextWrapped("%s", g_steam.message.empty() ? "Steam is not installed on this computer."
                                                         : g_steam.message.c_str());
        return;
    }
    std::string owner = g_steam.user.empty() ? "your" : g_steam.user + "'s";
    if (g_steam.added)
        ImGui::TextWrapped("In %s Steam library, with its artwork. Steam starts the game directly, with Steam "
                           "Input and the Steam overlay.", owner.c_str());
    else
        ImGui::TextWrapped("Adds the game to %s Steam library as a non-Steam game, with its library artwork, so "
                           "Steam starts it directly, with Steam Input and the Steam overlay.", owner.c_str());
    if (g_steam.confirm) {
        ImGui::TextWrapped("Steam is running. It has to be closed while the game is %s, because it rewrites its "
                           "list of games when it exits. It is started again afterwards.",
                           g_steam.confirm_action == "add" ? "added" : "removed");
        ImGui::BeginDisabled(busy);
        if (ImGui::Button("Close Steam and continue")) {
            g_steam.confirm = false;
            ask(g_steam.confirm_action, true);
        }
        ui_target("steam.close");
        ImGui::SameLine();
        if (ImGui::Button("Cancel##steam")) g_steam.confirm = false;
        ui_target("steam.cancel");
        ImGui::EndDisabled();
    } else {
        ImGui::BeginDisabled(busy);
        if (g_steam.added) {
            if (ImGui::Button("Remove from Steam")) request("remove");
            ui_target("steam.remove");
        } else {
            if (ImGui::Button("Add to Steam")) request("add");
            ui_target("steam.add");
        }
        ImGui::EndDisabled();
    }
    if (busy && g_steam.action != "status")
        ImGui::TextDisabled(g_steam.running ? "Closing Steam and changing its library..." : "Changing Steam's library...");
    else if (!g_steam.details.empty())
        ImGui::TextWrapped("%s", g_steam.details.c_str());
    else if (!g_steam.message.empty() && !g_steam.added && g_steam.action.empty() && g_steam.user.empty())
        ImGui::TextWrapped("%s", g_steam.message.c_str());
}

void steam_section_reset()
{
    if (!g_steam.process.id) g_steam.asked = false;     // ask again (Steam may have started or stopped)
    g_steam.confirm = false;
}

bool steam_busy() { return g_steam.process.id != 0; }

} // namespace app
