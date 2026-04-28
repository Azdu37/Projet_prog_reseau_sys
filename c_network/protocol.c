#include "protocol.h"
#include <stdio.h>
#include <string.h>

void proto_handle_incoming(const NetMessage *msg, GameState *local_state)
{
    if (!msg || !local_state) return;

    if (msg->magic != PROTOCOL_MAGIC) return;

    switch ((MsgType)msg->type) {
    case MSG_STATE_UPDATE: {
        if (msg->sender_id == local_state->my_peer_id) break;

        uint16_t uid = msg->unit_id;
        if (uid >= MAX_UNITS) break;

        UnitState *local_unit = &local_state->units[uid];

        if (local_unit->hp_max == 0 && uid >= local_state->unit_count) {
            local_state->unit_count = uid + 1;
        }

        if (local_unit->owner_peer == local_state->my_peer_id && local_unit->hp_max > 0) {
            /* NOTRE unité : on accepte les dégâts ET les requêtes de propriété */
            if (msg->unit.hp < local_unit->hp) {
                local_unit->hp    = msg->unit.hp;
                local_unit->alive = (local_unit->hp > 0) ? 1 : 0;
            }
            if (msg->unit.pending_request_from != 255) {
                local_unit->pending_request_from = msg->unit.pending_request_from;
            }
        } else {
            /* UNITÉ DISTANTE : Mise à jour complète de l'état réseau */
            local_unit->id                   = msg->unit.id;
            local_unit->team                 = msg->unit.team;
            local_unit->owner_peer           = msg->unit.owner_peer;
            local_unit->alive                = msg->unit.alive;
            local_unit->pending_request_from = msg->unit.pending_request_from;
            local_unit->x                    = msg->unit.x;
            local_unit->y                    = msg->unit.y;
            local_unit->hp                   = msg->unit.hp;
            local_unit->hp_max               = msg->unit.hp_max;
        }

        local_unit->dirty = 0;
        break;
    }
    default:
        break;
    }
}