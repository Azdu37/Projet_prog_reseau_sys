#include "protocol.h"
#include <string.h>

void proto_handle_incoming(const NetMessage *msg, GameState *state)
{
    if (!msg || !state || msg->magic != PROTOCOL_MAGIC) return;
    if (msg->sender_id == state->my_peer_id) return;

    uint16_t uid = msg->unit_id;
    if (uid >= MAX_UNITS) return;

    UnitState *u = &state->units[uid];

    if (msg->type == MSG_OWNERSHIP_REQUEST) {
        if (u->owner_peer == state->my_peer_id && u->lock_owner_peer == NO_PEER_ID) {
            u->pending_request_peer = msg->sender_id;
        }
        return;
    }

    if (msg->type != MSG_STATE_UPDATE) return;

    if (u->hp_max == 0 && uid >= state->unit_count)
        state->unit_count = uid + 1;

    if (msg->unit.version <= u->version)
        return;

    u->id = msg->unit.id;
    u->team = msg->unit.team;
    u->owner_peer = msg->unit.owner_peer;
    u->alive = msg->unit.alive;
    u->lock_owner_peer = msg->unit.lock_owner_peer;
    u->pending_request_peer = msg->unit.pending_request_peer;
    u->x = msg->unit.x;
    u->y = msg->unit.y;
    u->hp = msg->unit.hp;
    u->hp_max = msg->unit.hp_max;
    u->version = msg->unit.version;
    u->dirty = 0;
}
