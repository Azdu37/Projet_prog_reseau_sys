/*
 * test_ipc.c — Test standalone de la couche IPC
 *
 * Simule ce que Python ferait :
 *   1. Crée la shm
 *   2. Écrit un GameState bidon (3 unités)
 *   3. Le relit et affiche le résultat
 *   4. Ferme proprement
 *
 * Usage : gcc -Wall -g -I../shared -o test_ipc test_ipc.c ipc.c -lrt -lpthread
 *         ./test_ipc
 */

#include <stdio.h>
#include <string.h>
#include "ipc.h"

int main(void)
{
    printf("=== Test IPC V1 ===\n\n");

    /* ── Création de la shm (mode créateur) ── */
    if (ipc_init(SHM_NAME, SEM_WRITE_NAME, SEM_READ_NAME, 1) < 0) {
        fprintf(stderr, "Échec ipc_init\n");
        return 1;
    }

    /* ── Écriture d'un état bidon ─────────── */
    GameState state = {0};
    state.magic      = PROTOCOL_MAGIC;
    state.version    = PROTOCOL_VERSION;
    state.my_peer_id = 0;
    state.tick       = 42;
    state.unit_count = 3;

    /* Unité 0 : chevalier de l'équipe A */
    state.units[0] = (UnitState){
        .id         = 0,
        .team       = 0,
        .owner_peer = 0,
        .alive      = 1,
        .dirty      = 1,
        .x          = 5.0f,
        .y          = 3.0f,
        .hp         = 100,
        .hp_max     = 100,
    };

    /* Unité 1 : archer de l'équipe A */
    state.units[1] = (UnitState){
        .id         = 1,
        .team       = 0,
        .owner_peer = 0,
        .alive      = 1,
        .dirty      = 1,
        .x          = 7.0f,
        .y          = 2.0f,
        .hp         = 60,
        .hp_max     = 60,
    };

    /* Unité 2 : chevalier de l'équipe B (PC B) */
    state.units[2] = (UnitState){
        .id         = 2,
        .team       = 1,
        .owner_peer = 1,   /* appartient à PC B en V2 */
        .alive      = 1,
        .dirty      = 0,
        .x          = 10.0f,
        .y          = 8.0f,
        .hp         = 80,
        .hp_max     = 100,
    };

    printf("Écriture du GameState (tick=%d, %d unités)...\n",
           state.tick, state.unit_count);
    if (ipc_write_state(&state) < 0) {
        fprintf(stderr, "Échec ipc_write_state\n");
        ipc_close();
        return 1;
    }

    /* ── Relecture ────────────────────────── */
    GameState readback = {0};
    if (ipc_read_state(&readback) < 0) {
        fprintf(stderr, "Échec ipc_read_state\n");
        ipc_close();
        return 1;
    }

    printf("\nLecture shm:\n");
    printf("  magic   = 0x%08X %s\n", readback.magic,
           readback.magic == PROTOCOL_MAGIC ? "(OK)" : "(ERREUR!)");
    printf("  version = %d\n",  readback.version);
    printf("  tick    = %d\n",  readback.tick);
    printf("  unités  = %d\n\n", readback.unit_count);

    for (int i = 0; i < readback.unit_count; i++) {
        UnitState *u = &readback.units[i];
        printf("  Unité %d : team=%d owner=%d x=%.1f y=%.1f hp=%d/%d alive=%d dirty=%d\n",
               u->id, u->team, u->owner_peer,
               u->x, u->y, u->hp, u->hp_max,
               u->alive, u->dirty);
    }

    /* ── Fermeture ────────────────────────── */
    ipc_close();
    printf("\n=== Test IPC terminé avec succès ===\n");
    return 0;
}
