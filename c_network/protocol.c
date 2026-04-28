#include "protocol.h"
#include <string.h>

void proto_handle_incoming(const NetMessage *msg, GameState *state)
{
    if (!msg || !state || msg->magic != PROTOCOL_MAGIC) return;
    if (msg->type != MSG_STATE_UPDATE) return;
    if (msg->sender_id == state->my_peer_id) return;

    uint16_t uid = msg->unit_id;
    if (uid >= MAX_UNITS) return;

    UnitState *u = &state->units[uid];

    if (u->hp_max == 0 && uid >= state->unit_count)
        state->unit_count = uid + 1;

    if (u->owner_peer == state->my_peer_id && u->hp_max > 0) {
        /* Notre unite : accepter uniquement les baisses de HP */
        if (msg->unit.hp < u->hp) {
            u->hp = msg->unit.hp;
            u->alive = (u->hp > 0) ? 1 : 0;
        }
    } else {
        /* Unite distante : mise a jour complete */
        u->id = msg->unit.id;
        u->team = msg->unit.team;
        u->owner_peer = msg->unit.owner_peer;
        u->alive = msg->unit.alive;
        u->x = msg->unit.x;
        u->y = msg->unit.y;
        u->hp = msg->unit.hp;
        u->hp_max = msg->unit.hp_max;
    }
    u->dirty = 0;
}
