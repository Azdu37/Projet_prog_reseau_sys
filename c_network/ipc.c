#define _POSIX_C_SOURCE 200809L

#include "ipc.h"

#include <errno.h>
#include <fcntl.h>
#include <semaphore.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

struct ipc_context_s {
    int shm_fd;
    sem_t *state_sem;
    mbai_game_state_t *state;
    size_t state_size;
};

static void ipc_initialize_state(mbai_game_state_t *state,
                                 uint32_t local_peer_id,
                                 uint32_t map_width,
                                 uint32_t map_height)
{
    memset(state, 0, sizeof(*state));
    state->magic = MBAI_PROTOCOL_MAGIC;
    state->version = MBAI_PROTOCOL_VERSION;
    state->header_size = (uint32_t)offsetof(mbai_game_state_t, units);
    state->total_size = (uint32_t)sizeof(*state);
    state->unit_count = 0u;
    state->max_units = MBAI_MAX_UNITS;
    state->map_width = map_width;
    state->map_height = map_height;
    state->local_peer_id = local_peer_id;
}

static int ipc_open_shared_memory(int *out_fd, int *out_created)
{
    int shm_fd = shm_open(MBAI_SHM_NAME, O_CREAT | O_EXCL | O_RDWR, 0666);
    if (shm_fd >= 0) {
        *out_fd = shm_fd;
        *out_created = 1;
        return 0;
    }

    if (errno != EEXIST) {
        return -1;
    }

    shm_fd = shm_open(MBAI_SHM_NAME, O_RDWR, 0666);
    if (shm_fd < 0) {
        return -1;
    }

    *out_fd = shm_fd;
    *out_created = 0;
    return 0;
}

static int ipc_prepare_mapping(int shm_fd, size_t state_size, mbai_game_state_t **out_state)
{
    if (ftruncate(shm_fd, (off_t)state_size) != 0) {
        return -1;
    }

    void *mapped = mmap(NULL, state_size, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (mapped == MAP_FAILED) {
        return -1;
    }

    *out_state = (mbai_game_state_t *)mapped;
    return 0;
}

static int ipc_open_semaphore(sem_t **out_sem)
{
    sem_t *state_sem = sem_open(MBAI_STATE_SEM_NAME, O_CREAT, 0666, 1);
    if (state_sem == SEM_FAILED) {
        return -1;
    }

    *out_sem = state_sem;
    return 0;
}

int ipc_init(ipc_context_t **out_context,
             uint32_t local_peer_id,
             uint32_t map_width,
             uint32_t map_height)
{
    ipc_context_t *context = NULL;
    int created = 0;
    int locked = 0;

    if (out_context == NULL) {
        errno = EINVAL;
        return -1;
    }

    *out_context = NULL;

    context = (ipc_context_t *)calloc(1, sizeof(*context));
    if (context == NULL) {
        return -1;
    }

    context->shm_fd = -1;
    context->state_sem = NULL;
    context->state = NULL;
    context->state_size = sizeof(mbai_game_state_t);

    if (ipc_open_shared_memory(&context->shm_fd, &created) != 0) {
        goto error;
    }

    if (ipc_prepare_mapping(context->shm_fd, context->state_size, &context->state) != 0) {
        goto error;
    }

    if (ipc_open_semaphore(&context->state_sem) != 0) {
        goto error;
    }

    if (ipc_lock(context) != 0) {
        goto error;
    }
    locked = 1;

    if (created ||
        context->state->magic != MBAI_PROTOCOL_MAGIC ||
        context->state->version != MBAI_PROTOCOL_VERSION ||
        context->state->total_size != sizeof(mbai_game_state_t)) {
        ipc_initialize_state(context->state, local_peer_id, map_width, map_height);
    }

    if (ipc_unlock(context) != 0) {
        goto error;
    }
    locked = 0;

    *out_context = context;
    return 0;

error:
    {
        int saved_errno = errno;
        if (locked) {
            ipc_unlock(context);
        }
        ipc_close(context);
        errno = saved_errno;
    }
    return -1;
}

int ipc_lock(ipc_context_t *context)
{
    if (context == NULL || context->state_sem == NULL) {
        errno = EINVAL;
        return -1;
    }

    while (sem_wait(context->state_sem) == -1) {
        if (errno != EINTR) {
            return -1;
        }
    }

    return 0;
}

int ipc_unlock(ipc_context_t *context)
{
    if (context == NULL || context->state_sem == NULL) {
        errno = EINVAL;
        return -1;
    }

    return sem_post(context->state_sem);
}

mbai_game_state_t *ipc_get_state(ipc_context_t *context)
{
    if (context == NULL) {
        errno = EINVAL;
        return NULL;
    }

    return context->state;
}

void ipc_close(ipc_context_t *context)
{
    if (context == NULL) {
        return;
    }

    if (context->state != NULL) {
        munmap(context->state, context->state_size);
    }

    if (context->shm_fd >= 0) {
        close(context->shm_fd);
    }

    if (context->state_sem != NULL && context->state_sem != SEM_FAILED) {
        sem_close(context->state_sem);
    }

    free(context);
}

int ipc_unlink_all(void)
{
    int status = 0;

    if (shm_unlink(MBAI_SHM_NAME) != 0 && errno != ENOENT) {
        status = -1;
    }

    if (sem_unlink(MBAI_STATE_SEM_NAME) != 0 && errno != ENOENT) {
        status = -1;
    }

    return status;
}
