#include "pc_launcher_home.h"
#include "pc_ui_theme.h"
#include "pc_ui_actions.h"
#include "pc_mods.h"
#include "pc_ui_internal.h"
#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#ifndef DEFJAM_VERSION
#define DEFJAM_VERSION "dev"
#endif
#if defined(DEFJAM_APP)
const char *pc_app_game_version();
float pc_app_beside_play_width();
void pc_app_beside_play(float width, float height);
#endif

// <data>/last-error.txt: the game's last fatal message (host_fatal in src/main.c). On a Steam
// Deck or a Mac the dialog can go unseen, so Home repeats it until the player dismisses it.
static std::string last_error(bool dismiss = false)
{
    static bool loaded = false;
    static std::string text;
    auto path = std::filesystem::u8path(pcui::folder_path(pcui::Folder::Data)) / "last-error.txt";
    std::error_code error;
    if (dismiss) { std::filesystem::remove(path, error); text.clear(); return text; }
    if (loaded) return text;
    loaded = true;
    if (!std::filesystem::is_regular_file(path, error) || std::filesystem::file_size(path, error) > 8192) return text;
    std::ifstream input(path, std::ios::binary);
    text.assign(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    while (!text.empty() && (text.back() == '\n' || text.back() == '\r')) text.pop_back();
    return text;
}

UiHomeResult ui_launcher_home(float width, float height, const char *focus)
{
    UiHomeResult r;
    float s = ImGui::GetStyle().FontScaleMain;
    bool poster = width >= 950 * s && height >= 390 * s;
    if (poster) {
        float left = width * .30f;
        ImGui::BeginChild("hero", ImVec2(left, 0), ImGuiChildFlags_None,
                          ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoBackground);
        auto start = ImGui::GetCursorScreenPos();
        pcui::brickwork(start, ImVec2(left, height), s);
        ImGui::TextWrapped("NEW YORK / 2004 / RECOMPILED");
        pcui::poster(ImVec2(start.x, start.y + 45 * s), ImVec2(left - 10 * s, 290 * s), s);
        ImGui::EndChild();
        ImGui::SameLine(0, 20 * s);
    }
    ImGui::BeginChild("home tasks", ImVec2(0, 0), ImGuiChildFlags_None, ImGuiWindowFlags_NoBackground);
    pcui::heading("READY TO PLAY", 26 * s);
#if defined(DEFJAM_APP)
    ImGui::TextDisabled("Game v%s", pc_app_game_version());
#else
    ImGui::TextDisabled("Game v%s", DEFJAM_VERSION);
#endif
    if (pcui::mod_recovery_needed())
        ImGui::TextWrapped("Play is unavailable until an interrupted mod installation is recovered. Open Mods to fix it.");
    else if (pcui::mod_busy()) ImGui::TextWrapped("Finishing a mod operation. Play will be available when it finishes.");
    {
        std::string stopped = last_error();
        if (!stopped.empty()) {
            ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.5f, 0.45f, 1.0f));
            ImGui::TextWrapped("The game stopped with an error last time:");
            ImGui::PopStyleColor();
            ImGui::TextWrapped("%s", stopped.c_str());
            if (ImGui::SmallButton("Dismiss")) last_error(true);
            ui_target("Dismiss error");
        }
    }
    const char *labels[] = {"Settings", "Controls", "Mods", "Songs", "Help"};
    const char *targets[] = {"Settings", "Configure", "Mods", "Songs", "Help"};
    int routes[] = {1, 2, 3, 5, 4};
    if (ImGui::BeginTable("destinations", 2, ImGuiTableFlags_SizingStretchSame)) {
        for (int i = 0; i < 5; ++i) {
            ImGui::TableNextColumn();
            if (pcui::navigation_button(labels[i], ImVec2(-1, 44 * s))) r.route = routes[i];
            ui_target(targets[i]);
            if (i == 0) ui_target("Advanced"); // old automation alias
            if (focus && !strcmp(focus, targets[i])) ImGui::SetKeyboardFocusHere(-1);
        }
        ImGui::EndTable();
    }
    ImGui::Separator();
    ui_home_fields();
    ImGui::Separator();
    ui_home_devices();
    ImGui::EndChild();
    return r;
}
