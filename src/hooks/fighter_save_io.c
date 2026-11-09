#include "fighter_save_io.h"
#include <string.h>

static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static FighterSaveFile *find(FighterSaveIO *io, uint32_t handle) {
    for (uint32_t i = 0; i < FIGHTER_SAVE_IO_FILES; ++i)
        if (io->files[i].active && io->files[i].handle == handle) return &io->files[i];
    return 0;
}
int fighter_save_io_write(FighterSaveIO *io, uint32_t handle, const uint8_t *data,
                          uint32_t size, uint32_t written, int success) {
    FighterSaveFile *file = find(io, handle);
    if (!file) {
        if (!data || size < 4 || memcmp(data, "20CM", 4)) return 0;
        for (uint32_t i = 0; i < FIGHTER_SAVE_IO_FILES; ++i)
            if (!io->files[i].active) { file = &io->files[i]; break; }
        if (!file) return -1;
        file->active = 1; file->failed = 0; file->handle = handle; file->used = file->total = 0;
        if (size < 16 || word(data + 8) != 0x40
            || (word(data + 12) != 0x1490 && word(data + 12) != 0x5904)
            || word(data + 4) != 0x8C + word(data + 12)) file->failed = 1;
        else file->total = word(data + 4);
    }
    if (!data || !success || written != size || file->failed || size > file->total - file->used) {
        file->failed = 1; return -1;
    }
    memcpy(file->bytes + file->used, data, size); file->used += size;
    return 1;
}
void fighter_save_io_seek(FighterSaveIO *io, uint32_t handle) {
    FighterSaveFile *file = find(io, handle);
    if (file) file->failed = 1;
}
int fighter_save_io_close(FighterSaveIO *io, uint32_t handle, int success,
                          const uint8_t **bytes, uint32_t *size) {
    FighterSaveFile *file = find(io, handle);
    if (!file) return 0;
    file->active = 0;
    if (!success || file->failed || file->used != file->total) return -1;
    *bytes = file->bytes; *size = file->used; return 1;
}
