/*
 * test_ipc — Test standalone de la couche IPC
 * Usage : ./test_ipc [ecrire|lire] [peer_id]
 */

#include "ipc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void afficher(const GameState *s)
{
    printf("magic=0x%08X  peer=%d  tick=%u  unites=%d\n",
           s->magic, s->my_peer_id, s->tick, s->unit_count);
    for (int i = 0; i < s->unit_count; i++) {
        const UnitState *u = &s->units[i];
        const char *origin = (u->owner_peer == s->my_peer_id) ? "" : " << RESEAU";
        printf("  [%d] team=%d peer=%d pos=(%.1f,%.1f) hp=%d/%d %s%s%s\n",
               u->id, u->team, u->owner_peer, u->x, u->y, u->hp, u->hp_max,
               u->alive ? "vivant" : "mort", u->dirty ? " DIRTY" : "", origin);
    }
}

int main(int argc, char *argv[])
{
    const char *mode = (argc > 1) ? argv[1] : "ecrire";
    int peer_id = (argc > 2) ? atoi(argv[2]) : 0;

    if (ipc_init(SHM_NAME, SEM_WRITE_NAME, SEM_READ_NAME, 0) < 0) {
        fprintf(stderr, "SHM non disponible (lancer ./c_net d'abord)\n");
        return 1;
    }

    if (strcmp(mode, "lire") == 0) {
        GameState s = {0};
        ipc_read_state(&s);
        afficher(&s);
    } else {
        GameState s = {0};
        s.magic = PROTOCOL_MAGIC;
        s.version = PROTOCOL_VERSION;
        s.my_peer_id = (uint8_t)peer_id;
        s.unit_count = 3;
        s.units[0] = (UnitState){.id=0, .team=peer_id, .owner_peer=peer_id,
                                 .alive=1, .dirty=1, .x=5, .y=3, .hp=100, .hp_max=100};
        s.units[1] = (UnitState){.id=1, .team=peer_id, .owner_peer=peer_id,
                                 .alive=1, .dirty=1, .x=7, .y=2, .hp=60, .hp_max=60};
        s.units[2] = (UnitState){.id=2, .team=peer_id, .owner_peer=peer_id,
                                 .alive=1, .dirty=1, .x=9, .y=4, .hp=80, .hp_max=80};
        ipc_write_state(&s);
        printf("Ecrit %d unites dans la SHM.\n", s.unit_count);
    }

    ipc_close();
    return 0;
}
