#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ipc.h"

static void fill_demo_unit(mbai_unit_state_t *unit)
{
    unit->unit_id = 1u;
    unit->x = 10.0f;
    unit->y = 15.5f;
    unit->hp = 35.0f;
    unit->max_hp = 40.0f;
    unit->unit_type = (uint8_t)MBAI_UNIT_KNIGHT;
    unit->team_id = 'R';
    unit->network_owner_peer = 1u;
    unit->alive = 1u;
}

static void print_state(const mbai_game_state_t *state)
{
    printf("magic=0x%08X version=%u units=%u\n",
           state->magic,
           (unsigned int)state->version,
           (unsigned int)state->unit_count);

    if (state->unit_count == 0u) {
        puts("no units");
        return;
    }

    printf("unit0: id=%u type=%c team=%c pos=(%.1f, %.1f) hp=%.1f/%.1f owner=%u alive=%u\n",
           (unsigned int)state->units[0].unit_id,
           (char)state->units[0].unit_type,
           (char)state->units[0].team_id,
           state->units[0].x,
           state->units[0].y,
           state->units[0].hp,
           state->units[0].max_hp,
           (unsigned int)state->units[0].network_owner_peer,
           (unsigned int)state->units[0].alive);
}

int main(int argc, char **argv)
{
    ipc_context_t *context = NULL;
    mbai_game_state_t *state = NULL;
    const char *mode = (argc > 1) ? argv[1] : "write-demo";

    if (strcmp(mode, "cleanup") == 0) {
        if (ipc_unlink_all() != 0) {
            perror("ipc_unlink_all");
            return EXIT_FAILURE;
        }

        puts("IPC objects removed.");
        return EXIT_SUCCESS;
    }

    if (ipc_init(&context, 1u, 210u, 210u) != 0) {
        perror("ipc_init");
        return EXIT_FAILURE;
    }

    if (ipc_lock(context) != 0) {
        perror("ipc_lock");
        ipc_close(context);
        return EXIT_FAILURE;
    }

    state = ipc_get_state(context);
    if (state == NULL) {
        perror("ipc_get_state");
        ipc_unlock(context);
        ipc_close(context);
        return EXIT_FAILURE;
    }

    if (strcmp(mode, "write-demo") == 0) {
        state->local_peer_id = 1u;
        state->map_width = 210u;
        state->map_height = 210u;
        state->unit_count = 1u;
        fill_demo_unit(&state->units[0]);
        print_state(state);
    } else if (strcmp(mode, "read") == 0) {
        print_state(state);
    } else {
        fprintf(stderr, "unknown mode: %s\n", mode);
        ipc_unlock(context);
        ipc_close(context);
        return EXIT_FAILURE;
    }

    if (ipc_unlock(context) != 0) {
        perror("ipc_unlock");
        ipc_close(context);
        return EXIT_FAILURE;
    }

    ipc_close(context);
    return EXIT_SUCCESS;
}
