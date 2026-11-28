// Windows: the app installs itself (D215; docs/research/unified-app-design-2026-10-26.md §3.4).
//
// The released program, DefJamRecompiled-<version>-windows-x64.exe, carries the setup payload ZIP as
// resource 101 with its SHA-256 built in (DEFJAM_APP_PAYLOAD_SHA256), as DefJamSetup.exe does. The
// app lives in a folder of its own, its home: the program and, beside it, payload\ (unpacked from
// that resource), %LOCALAPPDATA%\Programs\DefJamRecompiled unless the player chose another. The
// chosen home is recorded in %LOCALAPPDATA%\DefJamRecompiled\location.json, so any other copy (the
// download, opened again) finds it. A home the install page makes holds everything (k_portable_marker):
// the game in game\ and the data and saves in data\, and the page's choices start the first setup in the
// installed copy (--first-setup). It adds one desktop shortcut; no Start-menu entry. A home an earlier
// release made keeps its game and data where its first-run screen put them.
//
// When the app starts without --payload:
//   - a program without the resource (a development build) does nothing here;
//   - the copy in its home makes sure payload\ is the one built into it (payload.sha256 records it),
//     unpacking it again when it is missing or another build's;
//   - another copy (the download) hands over to the copy in the home: it first replaces that copy
//     when it is a newer release, then starts it with the same arguments and exits;
//   - with no home yet, the window opens on "Install Def Jam Recompiled": an empty folder and the
//     game copy, checked (not Program Files, not a synced, network or FAT drive, short enough, the
//     copy outside the folder), then the program copied there, its payload unpacked, the home
//     recorded, the desktop shortcut made, and the installed copy started on its first setup.
// Replacing files in a home follows the update's rule (app_update.cpp): renamed aside to .old one
// by one, each step undone if a later one fails; the started copy removes the .old files.

#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <bcrypt.h>

#include <stdio.h>
#include <string.h>

#include <algorithm>
#include <atomic>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include <SDL3/SDL.h>

#include "imgui.h"

#include "app.h"
#include "app_os.h"
#include "pc_ui_actions.h"
#include "pc_ui_internal.h"
#include "pc_ui_theme.h"

namespace fs = std::filesystem;

namespace app
{
namespace
{

const char *k_program = "DefJamRecompiled.exe";

// The longest install folder, in UTF-16 units. Inside it the build needs game\versions\<version>-attempt-<id>
// to fit setup/engine.py's WINDOWS_VERSION_ROOT_MAX, and Upscaled Original Textures need 188 more
// (data\hd-work\...) to fit Windows' 259. The default folder is 69 with the longest user name.
// tests/unit/test_setup_paths.py checks all three.
const size_t k_install_folder_max = 70;

fs::path default_home() { return os::user_base() / "Programs" / "DefJamRecompiled"; }
fs::path location_file() { return os::user_base() / "DefJamRecompiled" / "location.json"; }

// {"app": "<home>"}: written here, so only that one string needs reading back.
fs::path recorded_home()
{
    std::ifstream in(location_file(), std::ios::binary);
    std::stringstream text;
    text << in.rdbuf();
    std::string s = text.str();
    size_t at = s.find("\"app\"");
    if (at == std::string::npos || (at = s.find('"', s.find(':', at) + 1)) == std::string::npos) return {};
    std::string value;
    for (size_t i = at + 1; i < s.size() && s[i] != '"'; i++) {
        if (s[i] == '\\' && i + 1 < s.size()) i++;
        value += s[i];
    }
    return value.empty() ? fs::path() : fs::path(value);
}

bool record_home(const fs::path &home)
{
    std::error_code ec;
    fs::create_directories(location_file().parent_path(), ec);
    std::string escaped;
    for (char c : home.string()) {
        if (c == '\\' || c == '"') escaped += '\\';
        escaped += c;
    }
    fs::path pending = location_file().string() + ".pending";
    {
        std::ofstream out(pending, std::ios::binary);
        out << "{\"app\": \"" << escaped << "\"}\n";
        if (!out) return false;
    }
    fs::rename(pending, location_file(), ec);
    return !ec;
}

fs::path home() { fs::path h = recorded_home(); return h.empty() ? default_home() : h; }

bool same_folder(const fs::path &a, const fs::path &b)
{
    std::error_code ec;
    return fs::equivalent(a, b, ec);
}

// ---- the payload built into the program -----------------------------------------------------------

#if defined(DEFJAM_APP_PAYLOAD_SHA256)
const char *k_payload_sha256 = DEFJAM_APP_PAYLOAD_SHA256;
#else
const char *k_payload_sha256 = nullptr;
#endif

bool embedded(const unsigned char **bytes, DWORD *size)
{
    if (!k_payload_sha256) return false;
    HRSRC resource = FindResourceW(nullptr, MAKEINTRESOURCEW(101), MAKEINTRESOURCEW(10));  // RT_RCDATA
    if (!resource) return false;
    HGLOBAL loaded = LoadResource(nullptr, resource);
    *bytes = (const unsigned char *)LockResource(loaded);
    *size = SizeofResource(nullptr, resource);
    return *bytes && *size;
}

std::string sha256(const unsigned char *bytes, DWORD size)
{
    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    unsigned char value[32];
    std::string out;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0) {
        if (BCryptCreateHash(alg, &hash, nullptr, 0, nullptr, 0, 0) >= 0 &&
            BCryptHashData(hash, (PUCHAR)bytes, size, 0) >= 0 && BCryptFinishHash(hash, value, sizeof value, 0) >= 0) {
            static const char digits[] = "0123456789abcdef";
            for (unsigned char c : value) { out += digits[c >> 4]; out += digits[c & 15]; }
        }
        if (hash) BCryptDestroyHash(hash);
        BCryptCloseAlgorithmProvider(alg, 0);
    }
    return out;
}

std::string read_first_line(const fs::path &path)
{
    std::ifstream in(path);
    std::string line;
    std::getline(in, line);
    return line;
}

// Unpack the built-in payload into `dest` (which must not exist). "" when done, else why not.
std::string unpack_payload(const fs::path &dest)
{
    const unsigned char *bytes;
    DWORD size;
    if (!embedded(&bytes, &size)) return "This program carries no setup files.";
    if (sha256(bytes, size) != k_payload_sha256) return "This program's setup files are damaged. Download it again.";
    std::error_code ec;
    fs::path zip = fs::temp_directory_path(ec) / ("DefJamRecompiled-payload-" + std::to_string(os::process_id()) + ".zip");
    {
        std::ofstream out(zip, std::ios::binary);
        out.write((const char *)bytes, size);
        if (!out) return "The setup files could not be written to " + zip.parent_path().string() + " (is the disk full?).";
    }
    fs::create_directories(dest, ec);
    // Windows' own tar (Windows 10 1803 and later) reads ZIP files; PowerShell's Expand-Archive otherwise.
    wchar_t system[MAX_PATH];
    GetSystemDirectoryW(system, MAX_PATH);
    os::Process unpack;
    std::string error;
    int code = -1;
    fs::path tar = fs::path(system) / "tar.exe";
    if (fs::is_regular_file(tar, ec) && os::start({tar.string(), "-xf", zip.string(), "-C", dest.string()}, nullptr, &unpack, &error))
        code = os::wait(unpack);
    if (code != 0) {
        fs::remove_all(dest, ec);
        fs::create_directories(dest, ec);
        os::set_env("DEFJAM_APP_UNPACK_ZIP", zip.string());
        os::set_env("DEFJAM_APP_UNPACK_TO", dest.string());
        if (os::start({(fs::path(system) / "WindowsPowerShell/v1.0/powershell.exe").string(), "-NoProfile", "-NonInteractive",
                       "-Command", "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath $env:DEFJAM_APP_UNPACK_ZIP "
                                   "-DestinationPath $env:DEFJAM_APP_UNPACK_TO"}, nullptr, &unpack, &error))
            code = os::wait(unpack);
        os::unset_env("DEFJAM_APP_UNPACK_ZIP");
        os::unset_env("DEFJAM_APP_UNPACK_TO");
    }
    fs::remove(zip, ec);
    if (code != 0 || !fs::is_regular_file(dest / "manifest.json", ec)) {
        fs::remove_all(dest, ec);
        return "The setup files could not be unpacked into " + dest.string() + ".";
    }
    return "";
}

// Put this program and its payload into `folder` (the home): new copies first, then each renamed in,
// the old ones aside to .old (removed by the copy that starts next), every step undone if one fails.
std::string place_into(const fs::path &folder, bool program_too)
{
    std::error_code ec;
    fs::create_directories(folder, ec);
    if (!os::writable(folder)) return "Files cannot be created in " + folder.string() + ".";
    fs::path program = folder / k_program, payload = folder / "payload";
    fs::remove_all(folder / "payload.new", ec);
    std::string why = unpack_payload(folder / "payload.new");
    if (!why.empty()) return why;
    if (program_too) {
        fs::remove(program.string() + ".new", ec);
        if (!CopyFileW(os::program().wstring().c_str(), (program.wstring() + L".new").c_str(), FALSE)) {
            fs::remove_all(folder / "payload.new", ec);
            return "The app could not be copied to " + folder.string() + ".";
        }
    }
    fs::remove(program.string() + ".old", ec);
    fs::remove_all(folder / "payload.old", ec);
    std::vector<std::pair<fs::path, fs::path>> steps, done;
    if (program_too && fs::exists(program, ec)) steps.push_back({program, program.string() + ".old"});
    if (fs::exists(payload, ec)) steps.push_back({payload, folder / "payload.old"});
    if (program_too) steps.push_back({program.string() + ".new", program});
    steps.push_back({folder / "payload.new", payload});
    for (const auto &step : steps) {
        // Antivirus scanners open freshly unpacked files for a moment, and Windows refuses to rename
        // a folder while any file in it is open ("Access is denied"): retry for a few seconds.
        for (int attempt = 0; attempt < 40; ++attempt) {
            fs::rename(step.first, step.second, ec);
            if (!ec) break;
            Sleep(250);
        }
        if (ec) {
            fprintf(stderr, "[APP] could not rename %s to %s: %s\n", step.first.string().c_str(),
                    step.second.string().c_str(), ec.message().c_str());
            std::error_code back;
            for (auto it = done.rbegin(); it != done.rend(); ++it) fs::rename(it->second, it->first, back);
            fs::remove_all(folder / "payload.new", back);
            fs::remove(program.string() + ".new", back);
            return "The app could not be put in place in " + folder.string() + " (" + ec.message() + ").";
        }
        done.push_back(step);
    }
    std::ofstream(folder / "payload.sha256") << k_payload_sha256 << "\n";
    return "";
}

// Why a folder will not do as the app's home, or "".
std::string folder_problem(const fs::path &folder)
{
    std::string text = folder.string();
    if (folder.empty() || !folder.is_absolute()) return "Choose a full folder path.";
    if (text.size() > 150) return "Choose a shorter folder path.";
    std::string lower = text;
    for (char &c : lower) c = (char)tolower((unsigned char)c);
    for (const char *name : {"ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"}) {
        const char *value = getenv(name);
        std::string v = value ? value : "";
        for (char &c : v) c = (char)tolower((unsigned char)c);
        if (!v.empty() && lower.rfind(v, 0) == 0)
            return "Program Files needs administrator rights to change. Choose a folder of your own.";
    }
    for (const char *name : {"OneDrive", "OneDriveConsumer", "OneDriveCommercial"}) {
        const char *value = getenv(name);
        std::string v = value ? value : "";
        for (char &c : v) c = (char)tolower((unsigned char)c);
        if (!v.empty() && lower.rfind(v, 0) == 0) return "Choose a folder outside OneDrive: syncing gets in the way of updates.";
    }
    std::wstring root = folder.root_path().wstring();
    UINT kind = GetDriveTypeW(root.c_str());
    if (kind == DRIVE_REMOTE) return "Choose a folder on this computer, not on a network drive.";
    wchar_t fs_name[MAX_PATH] = {};
    if (GetVolumeInformationW(root.c_str(), nullptr, 0, nullptr, nullptr, nullptr, fs_name, MAX_PATH) &&
        _wcsicmp(fs_name, L"NTFS") != 0 && _wcsicmp(fs_name, L"ReFS") != 0)
        return "Choose a folder on an NTFS drive (this one is FAT or exFAT).";
    return "";
}

// ---- the install page ---------------------------------------------------------------------------------
// One page, one folder: the player chooses an empty folder and their copy of the game, and the app
// puts everything in that folder (the app and payload\, the game in game\, the dump copy, saves and
// settings in data\), adds a desktop shortcut, and starts the installed copy, which sets the game up
// at once (--first-setup). The folder can be moved or copied whole.

bool g_page = false;
bool g_retry_update = false;    // the installed copy could not be updated: only the folder, tried again
char g_folder[1024];
char g_dump[2048];
int g_experience = 1;
bool g_hd = false;              // Upscaled Original Textures, generated during setup (Modern only)
std::string g_error;
std::atomic<bool> g_working(false), g_finished(false);
std::mutex g_result_lock;
std::string g_result;

enum class Pick { None, Folder, Dump };
std::mutex g_pick_lock;
std::string g_picked;
Pick g_has_pick = Pick::None;

void SDLCALL picked_folder(void *, const char *const *files, int)
{
    std::lock_guard<std::mutex> hold(g_pick_lock);
    if (files && files[0]) {
        g_picked = files[0];
        g_has_pick = Pick::Folder;
    }
}

void SDLCALL picked_dump(void *, const char *const *files, int)
{
    std::lock_guard<std::mutex> hold(g_pick_lock);
    if (files && files[0]) {
        g_picked = files[0];
        g_has_pick = Pick::Dump;
    }
}

// What a folder holds that this app did not put there (the first such name), or "" when it is empty,
// missing, or a folder the install page made before (an attempt that stopped, or Install again).
std::string foreign_entry(const fs::path &folder)
{
    std::error_code ec;
    if (!fs::exists(folder, ec)) return "";
    if (fs::is_regular_file(folder / k_portable_marker, ec)) return "";
    static const char *ours[] = {k_program, "payload", "payload.new", "payload.old", "payload.sha256",
                                 "play.lock", "setup.lock", "desktop.ini"};
    for (auto it = fs::directory_iterator(folder, ec); !ec && it != fs::directory_iterator(); it.increment(ec)) {
        std::string name = it->path().filename().string();
        bool known = false;
        for (const char *o : ours) known = known || _stricmp(name.c_str(), o) == 0;
        if (!known) return name;
    }
    return "";
}

bool inside(const fs::path &outer, const fs::path &inner)
{
    std::error_code ec;
    fs::path a = fs::weakly_canonical(outer, ec), b = fs::weakly_canonical(inner, ec);
    for (fs::path p = b; !p.empty(); p = p.parent_path()) {
        if (_wcsicmp(p.wstring().c_str(), a.wstring().c_str()) == 0) return true;
        if (p == p.parent_path()) break;
    }
    return false;
}

// Why the page's choices will not do, or "".
std::string choices_problem(const fs::path &folder, const fs::path &dump)
{
    std::string why = folder_problem(folder);
    if (!why.empty()) return why;
    if (g_retry_update) return "";                  // an older home, which may be longer, only gets updated
    size_t length = folder.wstring().size();
    if (length > k_install_folder_max)
        return "Choose a shorter folder path: this one has " + std::to_string(length) + " characters, and the game "
               "can be built in at most " + std::to_string(k_install_folder_max) + ".";
    std::error_code ec;
    if (fs::exists(folder, ec) && !fs::is_directory(folder, ec)) return folder.string() + " is a file, not a folder.";
    std::string other = foreign_entry(folder);
    if (!other.empty())
        return "That folder is not empty (it holds \"" + other + "\"). Choose an empty folder, or add a new "
               "folder name at the end of the path: it is created.";
    if (dump.empty()) return "Choose your copy of the game: a disc image (.iso) or an extracted folder.";
    if (!dump.is_absolute()) return "Choose your game copy with a full path.";
    if (!fs::exists(dump, ec)) return "Your game copy was not found: " + dump.string();
    if (fs::is_directory(dump, ec) && !fs::is_regular_file(dump / "default.xbe", ec))
        return "That folder is not an extracted Xbox game: it has no default.xbe. Choose the folder that holds "
               "default.xbe, or the disc image.";
    if (inside(folder, dump)) return "Your game copy is inside the install folder. Choose a folder elsewhere to install in.";
    if (inside(dump, folder)) return "The install folder is inside your game copy. Choose a folder elsewhere to install in.";
    return "";
}

void start_install()
{
    fs::path folder = fs::path(std::string(g_folder));
    fs::path dump = fs::path(std::string(g_dump));
    g_error = choices_problem(folder, dump);
    if (!g_error.empty()) return;
    bool fresh = !g_retry_update;
    g_working = true;
    g_finished = false;
    std::thread([folder, fresh] {
        std::string why = place_into(folder, true);
        if (why.empty() && !record_home(folder)) why = "The app's location could not be recorded in " + location_file().string() + ".";
        if (why.empty() && fresh) {
            std::ofstream marker(folder / k_portable_marker, std::ios::binary | std::ios::trunc);
            marker << "Def Jam Recompiled keeps everything in this folder: the app, the game (game\\) and your "
                      "game data, saves and settings (data\\). Move or copy the whole folder.\n";
            if (!marker) why = "Files cannot be created in " + folder.string() + ".";
        }
        if (why.empty() && fresh) {
            // Not needed to play (the app is in the folder), so a failure is only logged.
            fs::path desktop = os::desktop_folder();
            std::string error;
            std::error_code ec;
            if (!desktop.empty() && fs::is_directory(desktop, ec) &&
                os::make_shortcut(desktop / k_shortcut_name, folder / k_program, &error))
                fprintf(stderr, "[APP] desktop shortcut: %s\n", (desktop / k_shortcut_name).string().c_str());
            else
                fprintf(stderr, "[APP] desktop shortcut not made (%s)\n", error.empty() ? "no desktop folder" : error.c_str());
        }
        std::lock_guard<std::mutex> hold(g_result_lock);
        g_result = why;
        g_finished = true;
    }).detach();
}

} // namespace

Placement place_app(std::string *error)
{
    const unsigned char *bytes;
    DWORD size;
    if (!embedded(&bytes, &size)) return Placement::Development;
    fs::path me = os::program(), here = me.parent_path(), h = home();
    std::error_code ec;
    if (same_folder(here, h)) return Placement::Installed;
    // A one-folder install that was moved or copied here: this is the installed copy now. The desktop
    // shortcut follows when it pointed at a program that is no longer there.
    if (fs::is_regular_file(here / k_portable_marker, ec) && _wcsicmp(me.filename().wstring().c_str(), L"DefJamRecompiled.exe") == 0) {
        fprintf(stderr, "[APP] this folder holds the app now (it was in %s)\n", h.string().c_str());
        record_home(here);
        fs::path link = os::desktop_folder() / k_shortcut_name, was = os::shortcut_target(link);
        std::string error;
        if (!was.empty() && !fs::exists(was, ec) && os::make_shortcut(link, me, &error))
            fprintf(stderr, "[APP] desktop shortcut now points at %s\n", me.string().c_str());
        return Placement::Installed;
    }
    fs::path installed = h / k_program;
    if (!fs::is_regular_file(installed, ec)) {
        snprintf(g_folder, sizeof g_folder, "%s", h.string().c_str());
        snprintf(g_dump, sizeof g_dump, "%s", first_run().dump.c_str());   // --dump, when given
        g_page = true;
        return Placement::NeedsInstall;
    }
    // A newer release opened from wherever it was downloaded updates the installed copy first.
    std::stringstream text;
    {
        // Closed before the payload folder is renamed: Windows refuses to rename a folder while a
        // file in it is open ("Access is denied").
        std::ifstream manifest(h / "payload/manifest.json", std::ios::binary);
        text << manifest.rdbuf();
    }
    std::string s = text.str(), theirs;
    size_t at = s.find("\"version\"");
    if (at != std::string::npos && (at = s.find('"', s.find(':', at) + 1)) != std::string::npos)
        theirs = s.substr(at + 1, s.find('"', at + 1) - at - 1);
    // Another build of the same version (the next beta, or the release after its betas) replaces it
    // too: payload.sha256 records which payload the installed copy carries.
    bool other = theirs == DEFJAM_VERSION && read_first_line(h / "payload.sha256") != k_payload_sha256;
    if (newer(DEFJAM_VERSION, theirs) || other) {
        fprintf(stderr, "[APP] updating the installed app in %s from v%s to v%s%s\n", h.string().c_str(), theirs.c_str(),
                DEFJAM_VERSION, other ? " (another build of the same version)" : "");
        std::string why = place_into(h, true);
        if (!why.empty()) {
            g_error = "Could not update the installed app: " + why + " Retry installation below. The existing copy was kept.";
            g_retry_update = true;
            snprintf(g_folder, sizeof g_folder, "%s", h.string().c_str());
            g_page = true; return Placement::NeedsInstall;
        }
    }
    auto &next = relaunch();
    next = {installed.string()};
    for (const std::string &a : arguments()) next.push_back(a);
    fprintf(stderr, "[APP] handing over to the installed app: %s\n", installed.string().c_str());
    (void)error;
    return Placement::HandOver;
}

bool ensure_payload(std::string *error)
{
    fs::path folder = os::program().parent_path();
    std::error_code ec;
    if (fs::is_regular_file(folder / "payload/manifest.json", ec) &&
        read_first_line(folder / "payload.sha256") == k_payload_sha256)
        return true;
    fprintf(stderr, "[APP] unpacking the setup files this app carries into %s\n", (folder / "payload").string().c_str());
    std::string why = place_into(folder, false);
    if (!why.empty()) *error = why;
    return why.empty();
}

bool install_screen_draw(float width, float height, UiResult *result)
{
    if (!g_page) return false;
    {
        std::lock_guard<std::mutex> hold(g_pick_lock);
        if (g_has_pick == Pick::Folder) {
            // A chosen empty folder is used as it is; any other gets a folder of the app's own in it.
            fs::path chosen = fs::path(g_picked);
            std::error_code ec;
            bool empty = !fs::exists(chosen, ec) || fs::is_empty(chosen, ec) || foreign_entry(chosen).empty();
            snprintf(g_folder, sizeof g_folder, "%s", (empty ? chosen : chosen / "DefJamRecompiled").string().c_str());
            g_error.clear();
        } else if (g_has_pick == Pick::Dump) {
            snprintf(g_dump, sizeof g_dump, "%s", g_picked.c_str());
            g_error.clear();
        }
        g_has_pick = Pick::None;
    }
    if (g_finished.exchange(false)) {
        g_working = false;
        std::lock_guard<std::mutex> hold(g_result_lock);
        if (g_result.empty()) {
            fs::path installed = fs::path(std::string(g_folder)) / k_program;
            fprintf(stderr, "[APP] installed the app in %s\n", g_folder);
            auto &next = relaunch();
            next = {installed.string()};
            for (const std::string &a : arguments()) next.push_back(a);
            if (!g_retry_update)
                next.insert(next.end(), {"--first-setup", g_experience ? "1" : "0", g_experience && g_hd ? "1" : "0",
                                         std::string(g_dump)});
            result->leave = true;
        } else {
            g_error = g_result;
            fprintf(stderr, "[APP] installing the app: %s\n", g_error.c_str());
        }
    }
    page_begin(width, height, "INSTALL DEF JAM RECOMPILED");
    float pad = ImGui::GetStyle().FramePadding.x * 2, gap = ImGui::GetStyle().ItemSpacing.x;
    ImGui::BeginDisabled(g_working);
    if (g_retry_update) {
        ImGui::TextWrapped("The app installed in the folder below could not be updated. Close anything using that "
                           "folder, then try again.");
    } else {
        ImGui::TextWrapped("Choose an empty folder and your USA Xbox copy of Def Jam: Fight for NY. Everything goes in "
                           "that folder: the app, the game it builds from your copy, and your saves and settings. "
                           "Move or copy the whole folder to take the game elsewhere.");
    }
    ImGui::Spacing();
    ImGui::TextUnformatted("Install folder");
    float folder_button = ImGui::CalcTextSize("CHOOSE FOLDER...").x + pad;
    ImGui::SetNextItemWidth(std::max(120.0f, ImGui::GetContentRegionAvail().x - folder_button - gap));
    if (ImGui::InputText("##home", g_folder, sizeof g_folder)) g_error.clear();
    ui_target("install.folder");
    ImGui::SameLine();
    if (ImGui::Button("CHOOSE FOLDER...")) SDL_ShowOpenFolderDialog(picked_folder, nullptr, nullptr, g_folder[0] ? g_folder : nullptr, false);
    ui_target("install.choose-folder");
    if (!g_retry_update) {
        ImGui::Spacing();
        ImGui::TextUnformatted("Your game copy (disc image or extracted folder)");
        float image_button = ImGui::CalcTextSize("SELECT ISO...").x + pad;
        float dir_button = ImGui::CalcTextSize("SELECT FOLDER...").x + pad;
        ImGui::SetNextItemWidth(std::max(120.0f, ImGui::GetContentRegionAvail().x - image_button - dir_button - gap * 2));
        if (ImGui::InputText("##dump", g_dump, sizeof g_dump)) g_error.clear();
        ui_target("install.dump");
        ImGui::SameLine();
        if (ImGui::Button("SELECT ISO...")) {
            static const SDL_DialogFileFilter images[] = {{"Disc images", "iso;xiso"}, {"All files", "*"}};
            SDL_ShowOpenFileDialog(picked_dump, nullptr, nullptr, images, 2, nullptr, false);
        }
        ui_target("install.choose-image");
        ImGui::SameLine();
        if (ImGui::Button("SELECT FOLDER...")) SDL_ShowOpenFolderDialog(picked_dump, nullptr, nullptr, nullptr, false);
        ui_target("install.choose-dump-folder");
        ImGui::Spacing();
        ImGui::TextUnformatted("Experience");
        ImGui::RadioButton("Modern (recommended): widescreen, sharper 2x graphics", &g_experience, 1);
        ui_target("install.modern");
        ImGui::RadioButton("Original: 4:3, 480p, as on the console", &g_experience, 0);
        ui_target("install.original");
        ImGui::Spacing();
        // As the first run's step 3 offered it: only with Modern, which uses them.
        ImGui::BeginDisabled(!g_experience);
        bool hd = g_experience && g_hd;
        if (ImGui::Checkbox("Upscaled Original Textures (optional)", &hd)) g_hd = hd;
        ui_target("install.hd");
        ImGui::EndDisabled();
        ImGui::TextWrapped(g_experience
            ? "Generates higher-resolution versions of the original textures from your game copy on this PC. Adds "
              "several minutes and 15 GiB of working space. You can also do this later in Mods. Downloadable texture "
              "packs are in Mods after setup."
            : "Upscaled Original Textures go with Modern. Downloadable texture packs are in Mods after setup.");
        ImGui::Spacing();
        ImGui::TextDisabled("A Def Jam Recompiled shortcut is added to your desktop. Building takes several minutes; "
                            "the compiler it needs comes with the app.");
    }
    ImGui::EndDisabled();
    ImGui::Spacing();
    if (!g_error.empty()) ImGui::TextColored(ImVec4(1, 0.45f, 0.4f, 1), "%s", g_error.c_str());
    if (g_working) ImGui::TextDisabled("Copying the app into the folder...");
    page_actions();
    ImGui::BeginDisabled(g_working || !g_folder[0] || (!g_retry_update && !g_dump[0]));
    if (pcui::play_button(g_retry_update ? "TRY AGAIN" : "INSTALL", ImVec2(ImGui::GetFontSize() * 10, ImGui::GetFrameHeight() * 1.8f), 26))
        start_install();
    ui_target("install.start");
    ImGui::EndDisabled();
    ImGui::SameLine();
    ImGui::BeginDisabled(g_working);
    if (ImGui::Button("Quit")) result->leave = true;
    ui_target("Quit");
    ImGui::EndDisabled();
    page_end();
    return true;
}

bool install_busy() { return g_working; }

} // namespace app
