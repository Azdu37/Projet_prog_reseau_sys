#ifndef MBAI_IPC_H
#define MBAI_IPC_H

/* Shared-memory IPC between the local C runtime and the Python engine. */

#include <stdint.h>

#include "protocol.h"

typedef struct ipc_context_s ipc_context_t;

/*
 * Create or attach to the shared battle snapshot and its synchronization
 * semaphore. The function allocates the context and returns it through
 * out_context.
 */
int ipc_init(ipc_context_t **out_context,
             uint32_t local_peer_id,
             uint32_t map_width,
             uint32_t map_height);

/* Enter or leave the critical section protecting the shared snapshot. */
int ipc_lock(ipc_context_t *context);
int ipc_unlock(ipc_context_t *context);

/* Return the mapped shared state owned by the context. */
mbai_game_state_t *ipc_get_state(ipc_context_t *context);

/* Unmap/close local resources for the context. Safe to call once. */
void ipc_close(ipc_context_t *context);

/* Remove the named semaphore and shared memory object from the system. */
int ipc_unlink_all(void);

#endif /* MBAI_IPC_H */
