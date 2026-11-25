#pragma once
#include <string>
#include <vector>
namespace pcui {
struct SaveImportRow { std::string name, platform, action; };
struct SaveImportView {
    std::string status, token;
    std::vector<SaveImportRow> rows;
    int count = 0;
    bool failed = false;
};
// Launcher only. The helper holds the game's runtime lock during every import.
bool save_import_start(const std::string &source, bool options, bool replace, bool apply);
void save_import_poll();
bool save_import_busy();
const SaveImportView &save_import_view();
void save_import_clear();
void save_import_choose(bool folder);
bool save_import_take(std::string &path);
}
