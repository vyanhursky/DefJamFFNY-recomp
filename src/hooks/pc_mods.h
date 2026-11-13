#pragma once
#ifdef __cplusplus
#include <map>
#include <string>
#include <vector>
namespace pcui {
struct ModRow {
    std::string id, name, authors, description, installed, latest, load_after, channel, category;
    unsigned long long bytes = 0;
    bool compatible = false, revoked = false, update = false;
};
struct ManagedMod {
    std::string folder, name, version; bool rollback = false;
    std::string category; bool enabled = false; unsigned fighters = 0;
};
struct ModView {
    std::string message, catalogue;
    std::vector<ModRow> catalogue_mods;
    std::map<std::string, ManagedMod> installed;
};
bool mod_start(const std::string &command, const std::string &id = "");
bool mod_poll(); // true after a job completed; caller refreshes local inventory
bool mod_busy();
bool mod_prerelease();
void mod_set_prerelease(bool enabled);
// The language pack folder the launcher has chosen (empty for none). Fighter builds started from
// the Mods screen are composed for it, so Play finds a matching manifest. The caller reads the
// setting; this module never does (its unit-test driver has no settings).
void mod_set_language(const std::string &pack);
void mod_cancel();
const ModView &mod_view();
const std::string &mod_status();
float mod_fraction();      // 0..1 while a job reports bytes, -1 when it only reports steps
bool mod_failed();         // the job that just ended did not succeed
int mod_elapsed();         // whole seconds since the running job started
const std::string &mod_command(); // the command of the running or last job, e.g. "install-local"
bool mod_recovery_needed();
}
extern "C" {
#endif
/* Acquire a shared data-root lock for the lifetime of the game. Refuse an
 * incomplete transaction or an active installer, including --no-launcher. */
int pc_mods_game_lock(void);
int pc_mods_needs_recovery(void);
/* Load the fighter manifest before Play (rebuilding it first when stale). */
int pc_fighters_prepare(const char *language);
const char *pc_fighters_error(void);
#ifdef __cplusplus
}
#endif
