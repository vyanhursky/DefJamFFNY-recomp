#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(_WIN32)
#include <windows.h>
#endif

static DefjamFighterLookup s_lookup;

void defjam_fighter_config_install(DefjamFighterLookup lookup) { s_lookup = lookup; }

int defjam_fighter_managed(void) { return s_lookup != NULL; }

const char *defjam_fighter_env(const char *name) {
    if (s_lookup) return s_lookup(name);
    return getenv(name);
}

int defjam_fighter_trusted_cache(void) {
    const char *verify = getenv("RECOMP_FIGHTER_VERIFY_HASHES");
    return s_lookup && !(verify && *verify && strcmp(verify, "0"));
}

int defjam_fighter_file_present(const char *path, const char *sha256) {
    FILE *file = NULL;
    if (!path || !*path || strlen(path) >= 2048 || !sha256 || strlen(sha256) != 64) return 0;
    for (int i = 0; i < 64; ++i)
        if (!((sha256[i] >= '0' && sha256[i] <= '9') || (sha256[i] >= 'a' && sha256[i] <= 'f'))) return 0;
#if defined(_WIN32)
    {
        wchar_t wide[2048];
        if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, 2048)) file = _wfopen(wide, L"rb");
    }
#else
    file = fopen(path, "rb");
#endif
    if (!file) return 0;
    fclose(file);
    return 1;
}
