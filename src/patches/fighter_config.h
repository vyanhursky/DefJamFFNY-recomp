#ifndef DEFJAM_FIGHTER_CONFIG_H
#define DEFJAM_FIGHTER_CONFIG_H

/* Where the native fighter modules read their settings.
 *
 * Normal Play: the launcher loads mod-manager/fighter-manifest.ini once
 * (src/hooks/pc_mods.cpp) and installs a lookup; environment variables are
 * then ignored, so a stale RECOMP_FIGHTER_* in a shell or a Steam launch
 * option cannot change a player's run. Research and harness runs, which have
 * no manifest, keep reading the environment. */
#ifdef __cplusplus
extern "C" {
#endif

typedef const char *(*DefjamFighterLookup)(const char *name);

void defjam_fighter_config_install(DefjamFighterLookup lookup);
/* Nonzero once a launcher manifest was installed (normal Play). */
int defjam_fighter_managed(void);
/* The value of a RECOMP_FIGHTER_* setting, or NULL when it is not set. */
const char *defjam_fighter_env(const char *name);
/* A compiled cache file is usable. The bytes were verified when the cache
 * was written, and the launcher checked size and time stamps before Play, so
 * normal Play only checks the file exists. RECOMP_FIGHTER_VERIFY_HASHES=1
 * (and every research run) hashes it again with mod_file_matches, which the
 * including file gets from hooks/mod_sha256.h. */
int defjam_fighter_trusted_cache(void);
int defjam_fighter_file_present(const char *path, const char *sha256);
#define defjam_fighter_file_matches(path, sha256)     (defjam_fighter_trusted_cache() ? defjam_fighter_file_present((path), (sha256)) : mod_file_matches((path), (sha256)))

#ifdef __cplusplus
}
#endif

#endif
