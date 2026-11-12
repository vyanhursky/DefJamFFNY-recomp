/* Stands in for the host error dialog in native fighter tests, and lets them see it was asked for. */
#include <stdio.h>
void host_fatal(const char *message) { fprintf(stderr, "[HOST_FATAL] %s\n", message); }
