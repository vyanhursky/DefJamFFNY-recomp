#define _CRT_SECURE_NO_WARNINGS
#include "pc_mods.h"
#include "pc_settings.h"
#include "recomp_settings.h"
#if defined(DEFJAM_APP)
#include "app/app.h"
#endif
#include "pc_ui_model.h"
#include "pc_ui_actions.h"
#include "../patches/fighter_config.h"
#include <algorithm>
#include <cstdlib>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <chrono>
#include <thread>
#include <set>
#include <fstream>
#include <iterator>
#if defined(_WIN32)
#include <windows.h>
#else
#include <spawn.h>
#include <sys/wait.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
extern char **environ;
#endif
#ifndef DEFJAM_VERSION
#define DEFJAM_VERSION "0.0.0"
#endif
#ifndef DEFJAM_MOD_SOURCE_DIR
#define DEFJAM_MOD_SOURCE_DIR "."
#endif

namespace pcui {
static ModView view;
static std::string status;
static bool running = false;
static float job_fraction = -1.0f; // 0..1 while the helper reports bytes, -1 when it only reports steps
static bool job_failed = false;     // the last job ended badly (shown in red beside the button that started it)
static std::string job_command;
static std::chrono::steady_clock::time_point job_started;
static std::string enable_after_install;
static bool testing_versions = false;
static fs::path job_root;
static std::string fighter_language;
static std::map<std::string, std::string> fighter_config; // [environment] of the loaded manifest
#if defined(_WIN32)
static HANDLE process = nullptr;
static std::wstring wide(const std::string &s) {
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s.data(), (int)s.size(), nullptr, 0);
    std::wstring result(count, 0);
    if (count) MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s.data(), (int)s.size(), result.data(), count);
    return result;
}
static std::wstring quote(const std::wstring &s) {
    std::wstring out = L"\""; size_t slashes = 0;
    for (wchar_t c : s) {
        if (c == L'\\') { slashes++; continue; }
        out.append(slashes * (c == L'"' ? 2 : 1), L'\\'); slashes = 0;
        if (c == L'"') out += L'\\';
        out += c;
    }
    out.append(slashes * 2, L'\\'); return out + L'"';
}
#else
static pid_t process = -1;
#endif
static fs::path root() { return fs::u8path(folder_path(Folder::Data)) / "mod-manager"; }
static std::map<std::string, std::map<std::string, std::string>> projection(const fs::path &path) {
    std::map<std::string, std::map<std::string, std::string>> result;
    std::error_code error;
    if (fs::is_symlink(path, error) || !fs::is_regular_file(path, error) || fs::file_size(path, error) > 8 * 1024 * 1024) return result;
    std::ifstream input(path);
    std::string section, line;
    for (unsigned count = 0; count < 100000 && std::getline(input, line); count++) {
        if (line.size() > 8192) return {};
        if (!line.empty() && line.front() == '[' && line.back() == ']') section = line.substr(1, line.size()-2);
        else { auto split = line.find('='); if (split != std::string::npos) result[section][line.substr(0,split)] = line.substr(split+1); }
    }
    return result;
}
static void read_view() {
    ModView next;
    auto saved = projection(root() / "view.ini");
    next.message = saved["manager"]["message"];
    next.catalogue = saved["manager"]["catalogue"];
    for (auto &entry : saved) {
        auto &row = entry.second;
        if (entry.first.rfind("catalogue.",0) == 0) {
            ModRow mod;
            mod.id = row["id"]; mod.name = row["name"]; mod.authors = row["authors"]; mod.description = row["description"];
            mod.installed = row["installed"]; mod.latest = row["latest"]; mod.load_after = row["load_after"]; mod.channel = row["channel"];
            mod.category = row["category"];
            mod.bytes = strtoull(row["bytes"].c_str(), nullptr, 10);
            mod.compatible = row["compatible"] == "1"; mod.revoked = row["revoked"] == "1"; mod.update = row["update"] == "1";
            if (pack_name(mod.id)) next.catalogue_mods.push_back(mod);
        } else if (entry.first.rfind("installed.",0) == 0 && pack_name(row["folder"])) {
            next.installed[row["folder"]] = {row["folder"], row["name"], row["version"], row["rollback"] == "1",
                row["category"], row["enabled"] == "1", (unsigned)strtoul(row["fighters"].c_str(), nullptr, 10)};
        }
    }
    view = std::move(next);
}
bool mod_busy() { return running; }
bool mod_prerelease() { return testing_versions; }
void mod_set_prerelease(bool enabled) { if (!running) testing_versions = enabled; }
void mod_set_language(const std::string &pack) {
    if (running) return;
    fighter_language = !pack.empty() && pack_name(pack) ? path_utf8(fs::u8path(folder_path(Folder::Mods)) / fs::u8path(pack)) : "";
}
static void show_fighter_notice() {
    std::error_code error;
    auto folder = fs::u8path(folder_path(Folder::Data)) / "fighter-state";
    auto notice = folder / "notice.txt";
    if (fs::is_symlink(notice, error) || !fs::is_regular_file(notice, error) || fs::file_size(notice, error) > 4096) return;
    std::ifstream input(notice);
    std::string text((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    input.close();
    while (!text.empty() && (text.back() == '\n' || text.back() == '\r')) text.pop_back();
    if (text.empty()) return;
    status = text;
    fs::rename(notice, folder / "notice-shown.txt", error);
}
const ModView &mod_view() { static bool loaded = false; if (!loaded) { read_view(); show_fighter_notice(); loaded = true; } return view; }
const std::string &mod_status() { return status; }
float mod_fraction() { return running ? job_fraction : -1.0f; }
int mod_elapsed() { return running ? (int)std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - job_started).count() : 0; }
bool mod_failed() { return !running && job_failed; }
const std::string &mod_command() { return job_command; }
bool mod_recovery_needed() { std::error_code error; return fs::exists(root() / "journal.json", error); }
void mod_cancel() {
    if (!running) return;
    std::ofstream cancel(job_root / "cancel"); cancel << "cancel\n";
    status = "Cancelling; the previous installation will be kept.";
}
bool mod_start(const std::string &requested, const std::string &id) {
    std::string command = requested == "install-enable" ? "install" : requested;
    if (running) return false;
    if (command != "status" && command != "refresh" && command != "install" && command != "remove" && command != "rollback" && command != "recover"
        && command != "install-local" && command != "fighter-enable" && command != "fighter-disable" && command != "fighter-prepare") return false;
    if (!id.empty() && command != "install-local" && !pack_name(id)) return false;
    const char *override_root = getenv("RECOMP_TEXTURE_ROOT");
    if (override_root && *override_root && command != "status" && command != "refresh" && command != "fighter-prepare") {
        status = "Managed installs use the data folder's mods directory; unset RECOMP_TEXTURE_ROOT first."; return false;
    }
    std::error_code error;
    auto source = fs::current_path();
#if defined(DEFJAM_APP)
    if (!app::payload().empty()) source = app::payload() / "source";
#endif
    if (!fs::is_regular_file(source / "setup/mods.py", error)) source = fs::u8path(DEFJAM_MOD_SOURCE_DIR);
    auto script = source / "setup/mods.py";
    auto python = source.parent_path() /
#if defined(_WIN32)
        "python/python.exe";
#else
        "python/bin/python3";
#endif
    if (!fs::is_regular_file(script, error)) { status = "This installation has no mod helper; local mods still work."; return false; }
    std::string interpreter;
    if (fs::is_regular_file(python,error)) interpreter = path_utf8(python);
    else {
        const char *dev = getenv("DEFJAM_MOD_PYTHON");
        if (dev && *dev) interpreter = dev;
        else if (getenv("DEFJAM_INSTALL_DIR")) { status = "Bundled Python is missing; repair this installation to use catalogue downloads."; return false; }
        else interpreter =
#if defined(_WIN32)
            "python.exe";
#else
            "python3";
#endif
    }
    job_root = root();
    if (fs::is_symlink(job_root,error)) { status = "Refusing a symlinked manager directory."; return false; }
    fs::create_directories(job_root,error);
    if (error) { status = "Could not create mod-manager state directory."; return false; }
    fs::remove(job_root / "cancel",error);
    fs::remove(job_root / "progress.ini",error);
    std::string runtime = DEFJAM_VERSION;
#if defined(DEFJAM_APP)
    if (app::install().installed) runtime = app::install().version;
#endif
    // App helpers import directly from the verified payload. Keep its exact
    // inventory immutable so using Mods cannot make the next Repair reject it.
    std::vector<std::string> args = {interpreter, "-B", path_utf8(script), command, "--data-dir", folder_path(Folder::Data), "--runtime", runtime,
                                   "--cancel-file", path_utf8(job_root / "cancel")};
#if defined(DEFJAM_MOD_WIDE)
    args.insert(args.end(), {"--capability", "wide-v1"});
#endif
    // Language mods (src/hooks/pc_language.c): every build with this launcher loads them.
    args.insert(args.end(), {"--capability", "language-v1"});
    args.insert(args.end(), {"--capability", "fighters-v1", "--game-dir", path_utf8(fs::current_path() / "game")});
    if (testing_versions) args.push_back("--prerelease");
    if (!id.empty()) args.insert(args.end(), {command == "install-local" ? "--archive" : "--id",id});
    // Fighter builds are composed for the chosen language: set by the launcher before a Mods
    // command (mod_set_language) and by pc_fighters_prepare before Play. A status or refresh
    // never builds, so it needs none.
    if (command != "status" && command != "refresh" && !fighter_language.empty())
        args.insert(args.end(), {"--language-pack", fighter_language});
#if defined(_WIN32)
    std::wstring cmd;
    for (auto &arg : args) { if (!cmd.empty()) cmd += L' '; cmd += quote(wide(arg)); }
    STARTUPINFOW startup = {}; startup.cb = sizeof startup;
    PROCESS_INFORMATION child = {};
    if (!CreateProcessW(nullptr,cmd.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&child)) {
        status = "Could not start mod helper."; return false;
    }
    CloseHandle(child.hThread); process = child.hProcess;
#else
    std::vector<char *> argv;
    for (auto &arg : args) argv.push_back(arg.data()); argv.push_back(nullptr);
    posix_spawnattr_t attr; posix_spawnattr_init(&attr);
    posix_spawn_file_actions_t files; posix_spawn_file_actions_init(&files);
#if defined(__APPLE__)
    posix_spawnattr_setflags(&attr, POSIX_SPAWN_CLOEXEC_DEFAULT);
#elif defined(__GLIBC__) && __GLIBC_PREREQ(2,34)
    posix_spawn_file_actions_addclosefrom_np(&files,3);
#else
    long limit = sysconf(_SC_OPEN_MAX); if (limit < 0) limit = 1024;
    for (int fd=3;fd<limit;fd++) if (fcntl(fd,F_GETFD)>=0) posix_spawn_file_actions_addclose(&files,fd);
#endif
    int result = posix_spawnp(&process,interpreter.c_str(),&files,&attr,argv.data(),environ);
    posix_spawn_file_actions_destroy(&files); posix_spawnattr_destroy(&attr);
    if (result) { status = "Could not start mod helper: " + std::to_string(result); return false; }
#endif
    enable_after_install = requested == "install-enable" ? id : "";
    job_command = command; job_fraction = -1.0f; job_failed = false; job_started = std::chrono::steady_clock::now();
    running = true; status = command == "install-local" ? "Starting the install..." : "Working on mods..."; return true;
}
bool mod_poll() {
    if (!running) return false;
    auto progress = projection(job_root / "progress.ini");
    if (!progress["progress"]["message"].empty()) {
        status = progress["progress"]["message"];
        auto done = progress["progress"]["done"], total = progress["progress"]["total"];
        job_fraction = -1.0f;
        if (total != "0" && !total.empty()) {
            double have = strtod(done.c_str(), nullptr), all = strtod(total.c_str(), nullptr);
            if (all > 0) {
                job_fraction = (float)(have < all ? have / all : 1.0);
                char sizes[64]; snprintf(sizes, sizeof sizes, " (%.1f of %.1f MB)", have / 1048576.0, all / 1048576.0);
                status += sizes;
            }
        }
    }
    bool complete = false, ok = false;
#if defined(_WIN32)
    DWORD code;
    if (GetExitCodeProcess(process,&code) && code != STILL_ACTIVE) { complete = true; ok = code == 0; CloseHandle(process); process = nullptr; }
#else
    int code = 0; pid_t result = waitpid(process,&code,WNOHANG);
    if (result == process || (result < 0 && errno != EINTR)) { complete = true; ok = result == process && WIFEXITED(code) && WEXITSTATUS(code) == 0; process = -1; }
#endif
    if (!complete) return false;
    running = false; job_fraction = -1.0f; job_failed = !ok; read_view();
    if (ok) status = view.message.empty() ? "Mod inventory refreshed." : view.message;
    else if (progress["progress"]["message"].empty()) status = "Mod helper failed. Local packs are unchanged; see the launcher log.";
    if (ok && !enable_after_install.empty()) {
        auto managed = view.installed.find(enable_after_install);
        if (managed != view.installed.end() && managed->second.category == "fighters") {
            // Fighter activation validates resources and publishes its own
            // ledger transaction. It must never enter the texture-pack setting.
            auto id = enable_after_install;
            enable_after_install.clear();
            if (!mod_start("fighter-enable", id))
                status = "Installed, but the fighter pack could not be enabled. Open Fighters and retry.";
            return true;
        }
        char selected[RECOMP_SETTING_TEXT_MAX], language[RECOMP_SETTING_TEXT_MAX];
        recomp_settings_get_text("textures", "packs", selected, sizeof selected, "");
        recomp_settings_get_text("language", "pack", language, sizeof language, "");
        auto packs = inventory(fs::u8path(folder_path(Folder::Mods)), selected, language);
        auto pack = std::find_if(packs.begin(), packs.end(), [&](const Pack &p) { return p.name == enable_after_install && p.problem.empty(); });
        if (pack != packs.end()) {
            auto selection = recomp_settings_find(pack->language ? "language" : "textures", pack->language ? "pack" : "packs");
            auto enabled = recomp_settings_find("textures", "enabled");
            if ((selection && selection->source == RECOMP_SETTING_FROM_ENV) ||
                (!pack->language && enabled && enabled->source == RECOMP_SETTING_FROM_ENV)) {
                status = "Installed. A launch environment override prevents enabling this mod; remove it and enable in Installed.";
            } else {
                if (pack->language) recomp_settings_set_text("language", "pack", pack->name.c_str());
                else {
                    // A newly installed texture mod goes last (highest priority). Updates preserve order.
                    Pack chosen = *pack;
                    packs.erase(pack); chosen.selected = true; packs.push_back(chosen);
                    auto text = selected_packs(packs);
                    if (text.size() >= sizeof selected) {
                        status = "Installed but not enabled: the pack list is full. Manage selections in Installed.";
                        enable_after_install.clear(); return true;
                    }
                    recomp_settings_set_text("textures", "packs", text.c_str());
                    recomp_settings_set("textures", "enabled", 1);
                }
                status = pc_settings_save_checked() ? "Installed, but settings could not be saved. Enable the mod again in Installed."
                                                    : "Installed and enabled for the next game launch. Review texture conflicts in Installed if needed.";
            }
        } else status = "Download finished, but the installed pack could not be enabled. Open Installed to inspect its status.";
    }
    enable_after_install.clear();
    return true;
}

} // namespace pcui

// The manifest's [environment] is the only fighter configuration normal Play
// reads; the inherited environment is ignored (src/patches/fighter_config.h).
static const char *fighter_lookup(const char *name) {
    auto found = pcui::fighter_config.find(name);
    return found == pcui::fighter_config.end() || found->second.empty() ? nullptr : found->second.c_str();
}
extern "C" const char *pc_fighters_error(void) { return pcui::status.c_str(); }

namespace pcui {
// Size and modification time (nanoseconds since 1970), as Python's os.stat reports them.
static bool file_stamp(const std::string &path, unsigned long long &size, long long &mtime) {
#if defined(_WIN32)
    WIN32_FILE_ATTRIBUTE_DATA data;
    if (!GetFileAttributesExW(wide(path).c_str(), GetFileExInfoStandard, &data)
        || (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) return false;
    size = (unsigned long long)data.nFileSizeHigh << 32 | data.nFileSizeLow;
    long long ticks = (long long)((unsigned long long)data.ftLastWriteTime.dwHighDateTime << 32 | data.ftLastWriteTime.dwLowDateTime);
    mtime = (ticks - 116444736000000000LL) * 100;
#else
    struct stat info;
    if (stat(path.c_str(), &info) || !S_ISREG(info.st_mode)) return false;
    size = (unsigned long long)info.st_size;
#if defined(__APPLE__)
    mtime = (long long)info.st_mtimespec.tv_sec * 1000000000LL + info.st_mtimespec.tv_nsec;
#else
    mtime = (long long)info.st_mtim.tv_sec * 1000000000LL + info.st_mtim.tv_nsec;
#endif
#endif
    return true;
}

static std::string runtime_version() {
    std::string runtime = DEFJAM_VERSION;
#if defined(DEFJAM_APP)
    if (app::install().installed) runtime = app::install().version;
#endif
    return runtime;
}

// Read mod-manager/fighter-manifest.ini and check it still describes the files
// on disk. The bytes behind it were verified when the cache was written; a
// changed size or time on any input means rebuild, not hash.
static bool fighter_manifest(std::map<std::string, std::string> &config, std::string &why) {
    auto manifest = projection(root() / "fighter-manifest.ini");
    if (manifest["manifest"]["schema"] != "1") { why = "no compiled fighter manifest"; return false; }
    if (manifest["manifest"]["runtime"] != runtime_version()) { why = "the game was updated"; return false; }
    // Python writes the path through pathlib, which may spell separators differently.
    auto same_path = [](const std::string &a, const std::string &b) {
        return a.empty() || b.empty() ? a == b : fs::u8path(a).lexically_normal() == fs::u8path(b).lexically_normal();
    };
    if (!same_path(manifest["manifest"]["language"], fighter_language)) { why = "the language pack changed"; return false; }
    for (auto &entry : manifest["inputs"]) {
        auto &value = entry.second;
        auto first = value.find('|'), second = first == std::string::npos ? first : value.find('|', first + 1);
        unsigned long long size = 0; long long mtime = 0;
        if (second == std::string::npos) { why = "the fighter manifest is malformed"; return false; }
        auto path = value.substr(second + 1);
        if (!file_stamp(path, size, mtime) || std::to_string(size) != value.substr(0, first)
            || std::to_string(mtime) != value.substr(first + 1, second - first - 1)) {
            why = "a fighter pack or cache file changed: " + path; return false;
        }
    }
    if (manifest["inputs"].empty() || manifest["environment"].empty()) { why = "the fighter manifest is empty"; return false; }
    config = manifest["environment"];
    for (auto &entry : config)
        if (entry.first.rfind("RECOMP_FIGHTER_", 0) != 0) { why = "the fighter manifest has an unknown setting"; return false; }
    return true;
}

static bool fighters_enabled() {
    read_view();
    for (auto &entry : view.installed) if (entry.second.category == "fighters" && entry.second.enabled) return true;
    return false;
}
} // namespace pcui

static bool fighter_ui_texture_pack(const std::string &name, const char *language) {
    using namespace pcui;
    if (name.empty()) return true;
    if (name.size()!=35 || name.rfind("fighter-ui-",0)!=0 || name.substr(11).find_first_not_of("0123456789abcdef")!=std::string::npos) {
        status="The fighter manifest names an invalid UI texture pack."; return false;
    }
    std::error_code error;
    auto mods=fs::weakly_canonical(fs::u8path(folder_path(Folder::Mods)),error);
    auto folder=mods/fs::u8path(name);
    if (error || fs::is_symlink(folder,error) || !fs::is_directory(folder,error)
        || fs::weakly_canonical(folder,error)!=folder || error || fs::is_symlink(folder/"manifest.ini",error)
        || !fs::is_regular_file(folder/"manifest.ini",error)) {
        status="The verified Fighter UI texture cache is missing or redirected."; return false;
    }
    const char *existing_root=getenv("RECOMP_TEXTURE_ROOT");
    if (existing_root && *existing_root && (!fs::equivalent(fs::u8path(existing_root),mods,error) || error)) {
        status="Fighter UI textures require the managed mods directory; clear the external texture-root override."; return false;
    }
    const char *selected=getenv("RECOMP_TEXTURE_PACKS");std::string packs=selected?selected:"";
    bool present=false;std::istringstream stream(packs);std::string part;
    while (std::getline(stream,part,';')) if (part==name) present=true;
    if (!present) {if (!packs.empty()) packs+=';';packs+=name;}
    if (packs.size()+(language&&*language?strlen(language)+1:0)>=1024) {
        status="Fighter UI textures exceed the native texture-pack list budget."; return false;
    }
    auto root_text=path_utf8(mods);
#if defined(_WIN32)
    if (_putenv_s("RECOMP_TEXTURE_ROOT",root_text.c_str()) || _putenv_s("RECOMP_TEXTURE_PACKS",packs.c_str())) return false;
#else
    if (setenv("RECOMP_TEXTURE_ROOT",root_text.c_str(),1) || setenv("RECOMP_TEXTURE_PACKS",packs.c_str(),1)) return false;
#endif
    fprintf(stderr,"[FIGHTERS] HD UI texture layer active: %s\n",name.c_str());
    return true;
}

// Before the XBE loads. With no fighter pack enabled this does nothing and the
// game behaves as v1.1.1. Python runs only when the manifest is missing or
// stale (or the beta.1/beta.2 store still has to move back into save/); a
// fresh manifest starts the game with no helper process at all.
extern "C" int pc_fighters_prepare(const char *language) {
    using namespace pcui;
    // Explicit isolated diagnostics keep their own environment.
    if (getenv("RECOMP_FIGHTER_RESEARCH_SOD")) return 1;
    // Inherited diagnostic switches must not affect normal play.
#if defined(_WIN32)
    char **environment = _environ;
#else
    char **environment = environ;
#endif
    std::vector<std::string> inherited;
    for (char **p = environment; p && *p; ++p) {
        std::string item(*p);
        if (item.rfind("RECOMP_FIGHTER_", 0) == 0) inherited.push_back(item.substr(0, item.find('=')));
    }
    for (auto &key : inherited) {
#if defined(_WIN32)
        _putenv_s(key.c_str(), "");
#else
        unsetenv(key.c_str());
#endif
    }
    std::error_code error;
    auto data = fs::u8path(folder_path(Folder::Data));
    bool move_saves = fs::exists(data / "mod-manager/fighter-profiles/head.json", error)
        && !fs::exists(data / "fighter-state/migrated.json", error);
    bool wanted = fighters_enabled();
    if (!wanted && !move_saves) return 1;
    if (language && *language && !pack_name(language)) { status = "Invalid language pack folder. Choose an installed language before Play."; return 0; }
    fighter_language = language && *language ? path_utf8(fs::u8path(folder_path(Folder::Mods)) / fs::u8path(language)) : "";
    std::map<std::string, std::string> config;
    std::string why;
    if (move_saves || (wanted && !fighter_manifest(config, why))) {
        fprintf(stderr, "[FIGHTERS] preparing fighter packs before Play: %s\n",
                move_saves ? "fighter-era saves move back into save/" : why.c_str());
        if (!mod_start("fighter-prepare")) return 0;
        for (int i = 0; running; ++i) {
            if (i > 60000) { status = "Fighter preparation timed out. Your saves were not changed."; return 0; }
            mod_poll();
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        if (mod_failed()) { fprintf(stderr, "[FIGHTERS] preparation failed: %s\n", status.c_str()); return 0; }
        wanted = fighters_enabled();
        if (wanted && !fighter_manifest(config, why)) {
            status = "Fighter packs were prepared but their manifest does not match: " + why;
            fprintf(stderr, "[FIGHTERS] %s\n", status.c_str()); return 0;
        }
    }
    if (!wanted) return 1;
    if (!fighter_ui_texture_pack(config["RECOMP_FIGHTER_UI_TEXTURE_PACK"], language)) return 0;
    fighter_config = std::move(config);
    defjam_fighter_config_install(fighter_lookup);
    fprintf(stderr, "[FIGHTERS] fighter manifest loaded: %zu settings, saves stay in save/\n", fighter_config.size());
    return 1;
}

extern "C" int pc_mods_needs_recovery(void) { return pcui::mod_recovery_needed() ? 1 : 0; }

extern "C" int pc_mods_game_lock(void) {
    // No manager state means no managed packs/transactions yet. Create the shared
    // lock anyway so a later CLI installer cannot race a game launched manually.
    auto root = std::filesystem::u8path(pcui::folder_path(pcui::Folder::Data)) / "mod-manager";
    std::error_code error;
    if (std::filesystem::is_symlink(root,error)) return 0;
    std::filesystem::create_directories(root,error);
    if (error || std::filesystem::exists(root / "journal.json",error)) {
        fprintf(stderr,"[MODS] Incomplete mod transaction; open Mods to recover before playing.\n"); return 0;
    }
    auto path = root / "runtime.lock";
    if (std::filesystem::is_symlink(path,error)) return 0;
#if defined(_WIN32)
    static HANDLE lock = INVALID_HANDLE_VALUE;
    lock = CreateFileW(path.c_str(),GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if (lock == INVALID_HANDLE_VALUE) return 0;
    OVERLAPPED overlapped = {};
    if (!LockFileEx(lock,LOCKFILE_FAIL_IMMEDIATELY,0,1,0,&overlapped)) { CloseHandle(lock); lock = INVALID_HANDLE_VALUE; return 0; }
#else
    static int lock = -1;
    lock = open(path.c_str(),O_RDWR|O_CREAT|O_CLOEXEC,0600);
    if (lock < 0 || flock(lock,LOCK_SH|LOCK_NB)) { if (lock >= 0) close(lock); lock = -1; return 0; }
#endif
    // Recheck after acquiring the lock: an installer may have crashed between
    // the first journal check and this acquisition.
    if (std::filesystem::exists(root / "journal.json",error)) {
#if defined(_WIN32)
        CloseHandle(lock); lock = INVALID_HANDLE_VALUE;
#else
        close(lock); lock = -1;
#endif
        return 0;
    }
    return 1;
}
