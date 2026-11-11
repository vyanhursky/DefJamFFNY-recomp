#include "fighter_fatal.h"
#include <stdio.h>
#include <stdlib.h>

void host_fatal(const char *message); /* host.h; declared here so native tests link a stub. */
static int s_dialog = 1;

void defjam_fighter_fatal_dialog(int enabled) { s_dialog = enabled; }

void defjam_fighter_fatal(const char *area, const char *message) {
    char text[1024];
    if (!message) message = "unknown reason";
    if (area && *area) fprintf(stderr, "[FIGHTERS] %s stopped: %s\n", area, message);
    else fprintf(stderr, "[FIGHTERS] stopped: %s\n", message);
    fflush(stderr);
    if (s_dialog) {
        snprintf(text, sizeof text,
                 "Fighter Mod Support stopped the game.\n\n%s\n\nOpen Mods > Fighters in the launcher to check the fighter packs, "
                 "then start the game again.", message);
        host_fatal(text);
    }
    exit(1);
}
