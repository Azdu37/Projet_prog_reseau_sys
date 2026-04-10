/*
 * protocol.c - incoming network message handling
 *
 * V1: only MSG_STATE_UPDATE is handled.
 *     We update the matching unit in local_state only when the
 *     message comes from another peer.
 */

#include "protocol.h"
#include <stdio.h>
#include <string.h>

static UnitState *find_or_append_unit_slot(GameState *local_state, uint16_t unit_id)
{
    int i;

    for (i = 0; i < local_state->unit_count; ++i) {
        if (local_state->units[i].id == unit_id) {
            return &local_state->units[i];
        }
    }

    if (local_state->unit_count >= MAX_UNITS) {
        return NULL;
    }

    UnitState *slot = &local_state->units[local_state->unit_count++];
    memset(slot, 0, sizeof(*slot));
    slot->id = (uint8_t)unit_id;
    return slot;
}

void proto_handle_incoming(const NetMessage *msg, GameState *local_state)
{
    if (!msg || !local_state) {
        return;
    }

    if (msg->magic != PROTOCOL_MAGIC) {
        fprintf(stderr, "[proto] magic invalide 0x%08X, ignore\n", msg->magic);
        return;
    }

    switch ((MsgType)msg->type) {
    case MSG_STATE_UPDATE: {
        UnitState *local_unit;

        if (msg->sender_id == local_state->my_peer_id) {
            break;
        }

        local_unit = find_or_append_unit_slot(local_state, msg->unit_id);
        if (!local_unit) {
            fprintf(stderr, "[proto] plus de place pour l'unite %d, ignoree\n", msg->unit_id);
            break;
        }

        local_unit->id = msg->unit.id;
        local_unit->team = msg->unit.team;
        local_unit->owner_peer = msg->unit.owner_peer;
        local_unit->alive = msg->unit.alive;
        local_unit->x = msg->unit.x;
        local_unit->y = msg->unit.y;
        local_unit->hp = msg->unit.hp;
        local_unit->hp_max = msg->unit.hp_max;
        local_unit->dirty = 0;

        printf("[proto] unite %d mise a jour (peer %d) -> x=%.1f y=%.1f hp=%d\n",
               msg->unit_id,
               msg->sender_id,
               msg->unit.x,
               msg->unit.y,
               msg->unit.hp);
        break;
    }

    case MSG_OWN_REQUEST:
    case MSG_OWN_GRANT:
    case MSG_OWN_DENY:
        printf("[proto] message V2 type=%d recu, ignore en V1\n", msg->type);
        break;

    default:
        fprintf(stderr, "[proto] type de message inconnu: %d\n", msg->type);
        break;
    }
}
