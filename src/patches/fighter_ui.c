/* Retain the original UI texture-normalization operation while replacing its
 * unchecked512-entry model index with bounded batches of model pointers.
 * The table is private scratch: its indices never escape1813E0. Model/image
 * names and all APT identities remain unchanged. No pack supplies code.
 */
#include "fighter_ui.h"
#include "fighter_runtime.h"
#include "hooks/guest_call.h"
#include "host.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#define UI_BATCH 512u
#define UI_MODELS_MAX 16384u
extern void sub_0010A970(void);
extern void sub_001813E0_gen(void);

typedef struct FighterUIBatch {
    uint32_t context, count;
    const uint32_t *models;
    struct FighterUIBatch *previous;
} FighterUIBatch;
static RECOMP_TLS FighterUIBatch *s_batch;

static void ui_stop(const char *message) {
    fprintf(stderr, "[FIGHTERS] UI initialization stopped: %s\n", message);
    fflush(stderr);
    exit(1);
}

static uint32_t model_id(uint32_t model) {
    uint32_t name = MEM32(model + 0xB4), value = 0, digits = 0;
    if (!name) ui_stop("model has no numeric identity");
    while (MEM8(name)) {
        unsigned c = MEM8(name++);
        if (c < '0' || c > '9' || ++digits > 4)
            ui_stop("model identity exceeds the verified UI namespace");
        value = value * 10 + c - '0';
    }
    if (!digits) ui_stop("model identity is empty");
    return value;
}

static int compare_models(const void *a, const void *b) {
    uint32_t left = model_id(*(const uint32_t *)a), right = model_id(*(const uint32_t *)b);
    return (left > right) - (left < right);
}

int defjam_fighter_ui_model_batch(uint32_t context, uint32_t table, uint32_t capacity) {
    if (!s_batch) return 0;
    if (context != s_batch->context || capacity != UI_BATCH || s_batch->count > capacity)
        ui_stop("unexpected native model-table contract");
    memset((void *)XBOX_PTR(table), 0, capacity * sizeof(uint32_t));
    for (uint32_t i = 0; i < s_batch->count; ++i)
        MEM32(table + i * 4) = s_batch->models[i];
    return 1;
}

int defjam_fighter_ui_normalize(uint32_t context) {
    if (!defjam_fighter_research_active()) return 0;
    uint32_t module = MEM32(context + 0x94);
    if (!module) return 0;
    GuestRegs entry;
    guest_regs_save(&entry);
    /* Iterator outputs must be guest-addressable. Calls use stack below this
     * reserved area; no host pointer enters a native resource function. */
    g_esp -= 32;
    uint32_t scratch = g_esp;
    MEM32(scratch) = MEM32(scratch + 4) = 0;
    uint32_t args[3] = {0x002B7230u, scratch, scratch + 4}; /* Model type */
    uint32_t count = 0, allocated = UI_BATCH;
    uint32_t *models = (uint32_t *)malloc(allocated * sizeof(uint32_t));
    if (!models) ui_stop("model enumeration allocation failed");
    while (guest_call(sub_0010A970, module, 3, args) & 255u) {
        if (count == UI_MODELS_MAX) ui_stop("model enumeration exceeds its budget");
        if (count == allocated) {
            allocated *= 2;
            uint32_t *grown = (uint32_t *)realloc(models, allocated * sizeof(uint32_t));
            if (!grown) ui_stop("model enumeration allocation failed");
            models = grown;
        }
        uint32_t model = MEM32(scratch + 4);
        if (!model) ui_stop("model enumeration returned a null resource");
        (void)model_id(model);
        models[count++] = model;
    }
    /* Preserve the old table's ascending numeric-model visitation order. */
    qsort(models, count, sizeof(uint32_t), compare_models);
    for (uint32_t i = 1; i < count; ++i)
        if (model_id(models[i - 1]) == model_id(models[i]))
            ui_stop("duplicate numeric model identities");
    guest_regs_restore(&entry);
    FighterUIBatch batch = {context, 0, models, s_batch};
    s_batch = &batch;
    /* Invoke the unchanged native scalar/matrix operation for each batch.
     * Each model is visited once, including models with numeric IDs>=512.
     * Empty modules still execute the original callback once. */
    for (uint32_t first = 0; first < count || first == 0; first += UI_BATCH) {
        batch.models = models + first;
        batch.count = count - first < UI_BATCH ? count - first : UI_BATCH;
        guest_regs_restore(&entry);
        sub_001813E0_gen();
    }
    s_batch = batch.previous;
    if (count > UI_BATCH)
        fprintf(stderr, "[FIGHTERS] UI normalized %u models in %u batches\n",
                count, (count + UI_BATCH - 1) / UI_BATCH);
    free(models);
    return 1;
}
