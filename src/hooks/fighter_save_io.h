#ifndef DEFJAM_FIGHTER_SAVE_IO_H
#define DEFJAM_FIGHTER_SAVE_IO_H
#include <stdint.h>
#define FIGHTER_SAVE_IO_FILES 16u
#define FIGHTER_SAVE_IO_MAX (0x8Cu + 0x5904u)
typedef struct FighterSaveFile {
    uint32_t handle, used, total;
    int active, failed;
    uint8_t bytes[FIGHTER_SAVE_IO_MAX];
} FighterSaveFile;
typedef struct FighterSaveIO { FighterSaveFile files[FIGHTER_SAVE_IO_FILES]; } FighterSaveIO;
/* Only synchronous full WriteFile returns qualify. An unexpected seek or a
 * short/failed write poisons that attempt until its handle is closed. */
int fighter_save_io_write(FighterSaveIO *io, uint32_t handle, const uint8_t *data,
                          uint32_t size, uint32_t written, int success);
void fighter_save_io_seek(FighterSaveIO *io, uint32_t handle);
/* 1 = complete successful MC02 close; 0 = unrelated; -1 = failed/incomplete.
 * Returned bytes remain owned by io until its next write on this slot. */
int fighter_save_io_close(FighterSaveIO *io, uint32_t handle, int success,
                          const uint8_t **bytes, uint32_t *size);
#endif
