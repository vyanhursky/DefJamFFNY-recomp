#define _CRT_SECURE_NO_WARNINGS
#include "pc_mods.h"
#include "pc_settings.h"
#include "recomp_settings.h"
#if defined(DEFJAM_APP)
#include "app/app.h"
#endif
#include "pc_ui_model.h"
#include "pc_ui_actions.h"
#include <cstdlib>
#include <cerrno>
#include <cstdio>
#include <sstream>
#include <chrono>
#include <thread>
#include <set>
#if defined(_WIN32)
#include <windows.h>
#else
#include <spawn.h>
#include <sys/wait.h>
#include <sys/file.h>
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
static std::string enable_after_install;
static bool testing_versions = false;
static fs::path job_root;
static std::string fighter_data, fighter_language;
static fs::path fighter_ready, fighter_stop;
static bool fighter_active = false;
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
const ModView &mod_view() { static bool loaded = false; if (!loaded) { read_view(); loaded = true; } return view; }
const std::string &mod_status() { return status; }
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
        && command != "install-local" && command != "fighter-enable" && command != "fighter-disable" && command != "fighter-session") return false;
    if (!id.empty() && command != "install-local" && !pack_name(id)) return false;
    const char *override_root = getenv("RECOMP_TEXTURE_ROOT");
    if (override_root && *override_root && command != "status" && command != "refresh" && command != "fighter-session") {
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
    std::vector<std::string> args = {interpreter, path_utf8(script), command, "--data-dir", folder_path(Folder::Data), "--runtime", runtime,
                                   "--cancel-file", path_utf8(job_root / "cancel")};
#if defined(DEFJAM_MOD_WIDE)
    args.insert(args.end(), {"--capability", "wide-v1"});
#endif
    // Language mods (src/hooks/pc_language.c): every build with this launcher loads them.
    args.insert(args.end(), {"--capability", "language-v1"});
    args.insert(args.end(), {"--capability", "fighters-v1", "--game-dir", path_utf8(fs::current_path() / "game")});
    if (testing_versions) args.push_back("--prerelease");
    if (!id.empty()) args.insert(args.end(), {command == "install-local" ? "--archive" : "--id",id});
    if (command == "fighter-session") {
#if defined(_WIN32)
        auto pid = GetCurrentProcessId();
#else
        auto pid = getpid();
#endif
        args.insert(args.end(), {"--parent-pid", std::to_string(pid)});
        if (!fighter_language.empty()) args.insert(args.end(), {"--language-pack", fighter_language});
    }
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
    running = true; status = "Working on mods..."; return true;
}
bool mod_poll() {
    if (!running) return false;
    auto progress = projection(job_root / "progress.ini");
    if (!progress["progress"]["message"].empty()) {
        status = progress["progress"]["message"];
        auto done = progress["progress"]["done"], total = progress["progress"]["total"];
        if (total != "0" && !total.empty()) status += " (" + done + " / " + total + " bytes)";
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
    running = false; read_view();
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

extern "C" void pc_fighters_finish(void) {
    using namespace pcui;
    if (!fighter_active) return;
    { std::ofstream stop(fighter_stop); stop << "complete\n"; }
    for (int i=0; i<1000 && running; ++i) {
        mod_poll(); std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    auto result = projection(fighter_ready)["session"];
    if (running || result["state"] != "complete")
        fprintf(stderr, "[FIGHTERS] Profile supervisor did not acknowledge a clean exit: %s. Last committed generation retained.\n", result["detail"].c_str());
    else fprintf(stderr, "[FIGHTERS] managed profile session completed\n");
    fighter_active = false;
}

extern "C" const char *pc_fighters_data_root(void) {
    return pcui::fighter_active ? pcui::fighter_data.c_str() : nullptr;
}
extern "C" const char *pc_fighters_error(void) { return pcui::status.c_str(); }

extern "C" int pc_fighters_healthy(void) {
    using namespace pcui;
    if (!fighter_active) return 1;
    std::error_code error;
    auto heartbeat = fs::last_write_time(fs::u8path(fighter_data).parent_path() / "journal/supervisor.json", error);
    return !error && fs::file_time_type::clock::now() - heartbeat < std::chrono::seconds(10)
        && projection(fighter_ready)["session"]["state"] == "ready";
}

extern "C" int pc_fighters_prepare(const char *language) {
    using namespace pcui;
    // Explicit isolated diagnostics retain their own supervisor and environment.
    if (getenv("RECOMP_FIGHTER_RESEARCH_SOD")) return 1;
    // Managed Play gets its entire runtime contract from the verified helper.
    // Inherited diagnostic switches must not affect normal profile saves.
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
    if (!fs::exists(root() / "state.json", error) && !fs::exists(root() / "fighter-adoption.json", error)) return 1;
#if defined(_WIN32)
    auto pid = GetCurrentProcessId();
#else
    auto pid = getpid();
#endif
    fighter_ready = root() / ("fighter-session-" + std::to_string(pid) + ".ini");
    fighter_stop = root() / ("fighter-session-" + std::to_string(pid) + ".stop");
    if (fs::is_symlink(fighter_ready,error) || fs::is_symlink(fighter_stop,error)) return 0;
    fs::remove(fighter_ready,error); fs::remove(fighter_stop,error);
    if (language && *language && !pack_name(language)) { status = "Invalid language pack folder. Choose an installed language before Play."; return 0; }
    fighter_language = language && *language ? path_utf8(fs::u8path(folder_path(Folder::Mods)) / fs::u8path(language)) : "";
    if (!mod_start("fighter-session")) return 0;
    for (int i=0; i<30000; ++i) {
        auto ready = projection(fighter_ready);
        auto state = ready["session"]["state"];
        if (state == "unused") {
            while (running) { mod_poll(); std::this_thread::sleep_for(std::chrono::milliseconds(10)); }
            return 1;
        }
        if (state == "ready") {
            auto path = fs::u8path(ready["session"]["data_root"]);
            auto expected = fs::weakly_canonical(root() / "fighter-sessions", error);
            auto identity = path_utf8(path.parent_path().filename());
            if (error || path.filename() != "fighter-runtime-probe" || !fs::is_directory(path,error)
                || ready["session"]["parent_pid"] != std::to_string(pid) || identity.size() != 32
                || identity.find_first_not_of("0123456789abcdef") != std::string::npos
                || fs::weakly_canonical(path,error) != expected / identity / "fighter-runtime-probe" || error) {
                status = "Fighter supervisor returned an invalid private save workspace."; return 0;
            }
            fighter_data = path_utf8(path);
            static const std::set<std::string> allowed = {
                "NAMES", "BINDINGS", "RESEARCH_SOD", "RESEARCH_SCREENS", "NAMES_PROBE", "IMMUTABLE_REUSE", "WINDOW",
                "RESEARCH_MODELS", "RESEARCH_MODELS_SHA256", "RESEARCH_ENTITIES", "RESEARCH_ENTITIES_SHA256",
                "RESEARCH_CINEMATICS", "RESEARCH_CINEMATICS_SHA256", "RESEARCH_LANGUAGE_BASE", "RESEARCH_SCREENS_SHA256",
                "MOTION", "MOTION_SHA256", "MOTION_BINDINGS", "ANIMATIONS", "ANIMATIONS_SHA256", "ANIMATION_BINDINGS",
                "VOICES", "VOICES_SHA256", "VOICE_BINDINGS", "AI", "AI_SHA256", "AI_BINDINGS",
                "FINISHERS", "FINISHERS_SHA256", "FINISHER_BINDINGS", "CINEMATIC_BANKS", "CINEMATIC_BANKS_SHA256",
                "CINEMATIC_BINDINGS", "BLAZIN_BINDINGS", "SAVE_JOURNAL", "UNLOCKS",
                "TAGS", "TAGS_SHA256", "CAMERAS", "CAMERAS_SHA256", "TIMELINE_BINDINGS", "FILM_PROOFS"
            };
            for (auto &entry : ready["environment"]) {
                if (entry.first.rfind("RECOMP_FIGHTER_",0) != 0 || !allowed.count(entry.first.substr(15))) {
                    status = "Fighter supervisor returned an unsupported runtime setting."; return 0;
                }
#if defined(_WIN32)
                if (_putenv_s(entry.first.c_str(),entry.second.c_str())) return 0;
#else
                if (setenv(entry.first.c_str(),entry.second.c_str(),1)) return 0;
#endif
            }
            fighter_active = true; atexit(pc_fighters_finish);
            fprintf(stderr,"[FIGHTERS] managed profile session ready: %s\n",fighter_data.c_str());
            return 1;
        }
        if (state == "failed") { status = ready["session"]["detail"]; fprintf(stderr,"[FIGHTERS] launch refused: %s\n",status.c_str()); return 0; }
        mod_poll();
        if (!running) {
            // Publication may have completed between the first read and waitpid.
            if (projection(fighter_ready)["session"]["state"] == "unused") return 1;
            auto detail = projection(fighter_ready)["session"]["detail"];
            if (!detail.empty()) status = detail;
            fprintf(stderr,"[FIGHTERS] supervisor exited before launch: %s\n",status.c_str()); return 0;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    status = "Fighter preparation timed out; original profiles preserved.";
    fprintf(stderr,"[FIGHTERS] %s\n",status.c_str());
    return 0;
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
