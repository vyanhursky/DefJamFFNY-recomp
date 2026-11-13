// Rolling backup of the player's saves, taken once per launch before the game
// starts. Every player gets it, with or without mods: the save files are a
// few hundred kilobytes, and a bad write or a bad mod can then be undone from
// the launcher's data folder.
//
//   <data>/save-backups/<YYYYMMDD-HHMMSS>/UserData/...      copy of save/UserData
//   <data>/save-backups/<YYYYMMDD-HHMMSS>/fighter-state/... copy of the unlock sidecar
//
// The last three are kept. A launch whose saves equal the newest backup adds
// none, so repeated starts do not push a good backup out. The large partition
// images under save/ are caches the game rebuilds and are not copied.
#include <algorithm>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {
const int kKeep = 3;
const std::uintmax_t kMaxBytes = 64u << 20; // refuse to copy a save area this large

bool same_file(const fs::path &a, const fs::path &b) {
    std::error_code error;
    if (fs::file_size(a, error) != fs::file_size(b, error) || error) return false;
    std::ifstream left(a, std::ios::binary), right(b, std::ios::binary);
    return std::equal(std::istreambuf_iterator<char>(left), std::istreambuf_iterator<char>(),
                      std::istreambuf_iterator<char>(right), std::istreambuf_iterator<char>());
}

// Relative paths of every regular file under folder, sorted.
std::vector<fs::path> files(const fs::path &folder, std::uintmax_t &bytes) {
    std::vector<fs::path> result;
    std::error_code error;
    if (!fs::is_directory(folder, error)) return result;
    for (fs::recursive_directory_iterator it(folder, error), end; !error && it != end; it.increment(error)) {
        if (it->is_symlink(error)) { it.disable_recursion_pending(); continue; }
        if (it->is_regular_file(error)) { result.push_back(fs::relative(it->path(), folder, error)); bytes += it->file_size(error); }
    }
    std::sort(result.begin(), result.end());
    return result;
}

bool same_tree(const fs::path &a, const fs::path &b) {
    std::uintmax_t ignored = 0;
    auto left = files(a, ignored), right = files(b, ignored);
    if (left != right) return false;
    for (auto &name : left) if (!same_file(a / name, b / name)) return false;
    return true;
}

std::string stamp() {
    std::time_t now = std::time(nullptr);
    std::tm local{};
#if defined(_WIN32)
    localtime_s(&local, &now);
#else
    localtime_r(&now, &local);
#endif
    char text[32];
    std::strftime(text, sizeof text, "%Y%m%d-%H%M%S", &local);
    return text;
}
} // namespace

extern "C" void pc_save_backup(void) {
    std::error_code error;
    const char *env = std::getenv("DEFJAM_DATA");
    if (!env || !*env) return; // the save root is then the runtime's own default, not ours to manage
    fs::path data = fs::u8path(env);
    fs::path saves = data / "save" / "UserData", sidecar = data / "fighter-state";
    std::uintmax_t bytes = 0;
    if (files(saves, bytes).empty()) return;
    files(sidecar, bytes);
    if (bytes > kMaxBytes) { std::fprintf(stderr, "[SAVES] save area is %ju bytes; rolling backup skipped\n", bytes); return; }
    fs::path root = data / "save-backups";
    if (fs::is_symlink(root, error)) return;
    fs::create_directories(root, error);
    std::vector<fs::path> existing;
    for (fs::directory_iterator it(root, error), end; !error && it != end; it.increment(error))
        if (it->is_directory(error) && !it->is_symlink(error) && it->path().filename().string().size() == 15) existing.push_back(it->path());
    std::sort(existing.begin(), existing.end());
    if (!existing.empty() && same_tree(saves, existing.back() / "UserData") && same_tree(sidecar, existing.back() / "fighter-state")) {
        std::fprintf(stderr, "[SAVES] saves unchanged since backup %s\n", existing.back().filename().string().c_str());
        return;
    }
    fs::path target = root / stamp(), partial = root / (target.filename().string() + ".partial");
    if (fs::exists(target, error)) return;
    fs::remove_all(partial, error);
    error.clear();
    fs::create_directories(partial / "UserData", error);
    if (!error) fs::copy(saves, partial / "UserData", fs::copy_options::recursive, error);
    if (!error && fs::is_directory(sidecar)) {
        fs::create_directories(partial / "fighter-state", error);
        if (!error) fs::copy(sidecar, partial / "fighter-state", fs::copy_options::recursive, error);
    }
    if (!error) fs::rename(partial, target, error);
    if (error) {
        std::fprintf(stderr, "[SAVES] rolling backup failed: %s\n", error.message().c_str());
        fs::remove_all(partial, error);
        return;
    }
    existing.push_back(target);
    while ((int)existing.size() > kKeep) { fs::remove_all(existing.front(), error); existing.erase(existing.begin()); }
    std::fprintf(stderr, "[SAVES] backed up save/UserData to %s (keeping the last %d)\n", target.string().c_str(), kKeep);
}
