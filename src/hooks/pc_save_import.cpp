// Launcher save import: native pickers, a shell-free helper process and a small INI result.
// The app uses its verified payload's Python; source builds may select DEFJAM_SAVE_PYTHON.
#define _CRT_SECURE_NO_WARNINGS
#include "pc_save_import.h"
#include "pc_ui_actions.h"
#include "pc_ui_model.h"
#if defined(DEFJAM_APP)
#include "app/app.h"
#endif
#include <cstdlib>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <map>
#include <mutex>
#if defined(_WIN32)
#include <windows.h>
#include <commdlg.h>
#include <shlobj.h>
#else
#include <SDL3/SDL.h>
#include <spawn.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
extern char **environ;
#endif
#ifndef DEFJAM_SAVE_SOURCE_DIR
#define DEFJAM_SAVE_SOURCE_DIR "."
#endif

namespace pcui {
static SaveImportView view;
static bool running = false;
static fs::path job;
static std::mutex picker_mutex;
static std::string picked;
static bool picked_ready = false;
#if defined(_WIN32)
static HANDLE process = nullptr;
static std::wstring wide(const std::string &s) {
    int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s.data(), (int)s.size(), nullptr, 0);
    std::wstring w(n, 0);
    if (n) MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s.data(), (int)s.size(), w.data(), n);
    return w;
}
static std::wstring quote(const std::string &s) {
    std::wstring out = L"\""; size_t slashes = 0;
    for (wchar_t c : wide(s)) {
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
static void pick(const std::string &path) {
    std::lock_guard<std::mutex> lock(picker_mutex);
    picked = path; picked_ready = !path.empty();
}
void save_import_choose(bool folder) {
#if defined(_WIN32)
    if (folder) {
        HRESULT initialized = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
        BROWSEINFOW info = {};
        info.hwndOwner = GetActiveWindow();
        info.lpszTitle = L"Choose a Def Jam save folder";
        info.ulFlags = BIF_RETURNONLYFSDIRS | BIF_USENEWUI;
        PIDLIST_ABSOLUTE item = SHBrowseForFolderW(&info);
        if (item) {
            wchar_t path[MAX_PATH];
            if (SHGetPathFromIDListW(item, path)) pick(path_utf8(fs::path(path)));
            CoTaskMemFree(item);
        }
        if (SUCCEEDED(initialized)) CoUninitialize();
    } else {
        wchar_t path[32768] = {};
        OPENFILENAMEW info = {}; info.lStructSize = sizeof info;
        info.hwndOwner = GetActiveWindow(); info.lpstrFile = path; info.nMaxFile = 32768;
        info.lpstrFilter = L"Save exports\0*.zip;*.max;*.cbs;*.sps;*.xps;*.psu;*.psv\0All files\0*.*\0\0";
        info.lpstrTitle = L"Choose an Xbox or PS2 save export";
        info.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
        if (GetOpenFileNameW(&info)) pick(path_utf8(fs::path(path)));
    }
#else
    auto done = [](void *, const char *const *files, int) { if (files && files[0]) pick(files[0]); };
    if (folder) SDL_ShowOpenFolderDialog(done, nullptr, nullptr, nullptr, false);
    else {
        static const SDL_DialogFileFilter filters[] = {
            {"Save exports", "zip;max;cbs;sps;xps;psu;psv"}, {"All files", "*"}};
        SDL_ShowOpenFileDialog(done, nullptr, nullptr, filters, 2, nullptr, false);
    }
#endif
}
bool save_import_take(std::string &path) {
    std::lock_guard<std::mutex> lock(picker_mutex);
    if (!picked_ready) return false;
    path = picked; picked_ready = false; return true;
}
bool save_import_busy() { return running; }
const SaveImportView &save_import_view() { return view; }
void save_import_clear() { if (!running) view = {}; }
static bool fail(const std::string &message) { view = {}; view.status = message; view.failed = true; return false; }
bool save_import_start(const std::string &source_path, bool options, bool replace, bool apply) {
    if (running || source_path.empty()) return false;
    if (apply && (view.token.empty() || view.count == 0)) return false;
    std::error_code error;
    auto source = fs::current_path();
#if defined(DEFJAM_APP)
    if (!app::payload().empty()) source = app::payload() / "source";
#endif
    if (!fs::is_regular_file(source / "scripts/save-import.py", error)) source = fs::u8path(DEFJAM_SAVE_SOURCE_DIR);
    auto helper = source / "scripts/save-import.py";
    if (!fs::is_regular_file(helper, error)) return fail("The save importer is missing. Repair this installation and try again.");
    auto python = source.parent_path() /
#if defined(_WIN32)
        "python/python.exe";
#else
        "python/bin/python3";
#endif
    std::string interpreter;
    if (fs::is_regular_file(python, error)) interpreter = path_utf8(python);
    else {
        const char *dev = getenv("DEFJAM_SAVE_PYTHON");
        if (dev && *dev) interpreter = dev;
        else if (getenv("DEFJAM_INSTALL_DIR")) return fail("The save importer is unavailable. Repair this installation and try again.");
        else interpreter =
#if defined(_WIN32)
            "python.exe";
#else
            "python3";
#endif
    }
    // Each process/job owns its result, so two launcher windows cannot share stale previews.
    auto temp = fs::temp_directory_path(error);
    if (error) return fail("Could not find a temporary folder for save import.");
    auto tick = std::chrono::steady_clock::now().time_since_epoch().count();
    job = temp / ("defjam-save-import-" + std::to_string(
#if defined(_WIN32)
        GetCurrentProcessId()
#else
        getpid()
#endif
        ) + "-" + std::to_string(tick));
    if (!fs::create_directory(job, error)) return fail("Could not create a temporary folder for save import.");
#if !defined(_WIN32)
    fs::permissions(job, fs::perms::owner_all, fs::perm_options::replace, error);
    if (error) { fs::remove(job, error); return fail("Could not protect the save import result folder."); }
#endif
    std::vector<std::string> args = {interpreter, "-B", path_utf8(helper), source_path,
        "--save-dir", folder_path(Folder::Saves), "--report", path_utf8(job / "result.ini")};
    if (options) args.push_back("--include-options");
    if (replace) args.push_back("--force");
    if (apply) args.insert(args.end(), {"--expect", view.token});
    else args.push_back("--dry-run");
    bool started = false;
#if defined(_WIN32)
    std::wstring command;
    for (auto &arg : args) { if (!command.empty()) command += L' '; command += quote(arg); }
    STARTUPINFOW startup = {}; startup.cb = sizeof startup;
    PROCESS_INFORMATION child = {};
    started = CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW,
                             nullptr, nullptr, &startup, &child) != 0;
    if (started) { CloseHandle(child.hThread); process = child.hProcess; }
#else
    std::vector<char *> argv;
    for (auto &arg : args) argv.push_back(arg.data()); argv.push_back(nullptr);
    posix_spawnattr_t attr; posix_spawnattr_init(&attr);
    posix_spawn_file_actions_t files; posix_spawn_file_actions_init(&files);
#if defined(__APPLE__)
    posix_spawnattr_setflags(&attr, POSIX_SPAWN_CLOEXEC_DEFAULT);
#elif defined(__GLIBC__) && __GLIBC_PREREQ(2,34)
    posix_spawn_file_actions_addclosefrom_np(&files, 3);
#else
    long limit = sysconf(_SC_OPEN_MAX); if (limit < 0) limit = 1024;
    for (int fd = 3; fd < limit; fd++) if (fcntl(fd, F_GETFD) >= 0) posix_spawn_file_actions_addclose(&files, fd);
#endif
    started = posix_spawnp(&process, interpreter.c_str(), &files, &attr, argv.data(), environ) == 0;
    posix_spawn_file_actions_destroy(&files); posix_spawnattr_destroy(&attr);
#endif
    if (!started) { fs::remove_all(job, error); return fail("Could not start the save importer. Repair the app, or check Python in a source build."); }
    running = true;
    view = {}; view.status = apply ? "Importing saves..." : "Checking saves...";
    return true;
}
void save_import_poll() {
    if (!running) return;
    bool complete = false, ok = false;
#if defined(_WIN32)
    DWORD code;
    if (GetExitCodeProcess(process, &code) && code != STILL_ACTIVE) {
        complete = true; ok = code == 0; CloseHandle(process); process = nullptr;
    }
#else
    int code = 0; pid_t result = waitpid(process, &code, WNOHANG);
    if (result == process || (result < 0 && errno != EINTR)) {
        complete = true; ok = result == process && WIFEXITED(code) && WEXITSTATUS(code) == 0; process = -1;
    }
#endif
    if (!complete) return;
    running = false;
    std::map<std::string, std::map<std::string, std::string>> values;
    std::error_code error;
    auto result_file = job / "result.ini";
    if (!fs::is_symlink(result_file, error) && fs::is_regular_file(result_file, error) && fs::file_size(result_file, error) <= 65536) {
        std::ifstream input(result_file); std::string section, line;
        while (std::getline(input, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.size() > 8192) break;
            if (!line.empty() && line.front() == '[' && line.back() == ']') section = line.substr(1, line.size() - 2);
            else { auto at = line.find('='); if (at != std::string::npos) values[section][line.substr(0, at)] = line.substr(at + 1); }
        }
    }
    view = {}; view.status = values["import"]["message"]; view.failed = !ok;
    if (view.status.empty()) { view.status = "The save importer stopped without a result. Check the launcher log and try again."; view.failed = true; }
    if (ok && values["import"]["status"] == "preview") {
        auto token = values["import"]["token"];
        if (token.size() == 64 && token.find_first_not_of("0123456789abcdef") == std::string::npos) view.token = token;
        view.count = std::max(0, std::min(256, atoi(values["import"]["count"].c_str())));
    }
    for (int i = 0; i < 256; i++) {
        auto it = values.find("profile." + std::to_string(i));
        if (it == values.end()) break;
        view.rows.push_back({it->second["name"], it->second["platform"], it->second["action"]});
    }
    fprintf(stderr, "[SAVE-IMPORT] %s\n", view.status.c_str());
    fs::remove_all(job, error);
}
} // namespace pcui
