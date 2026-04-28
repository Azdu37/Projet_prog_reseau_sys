/*
 * protocol.c - incoming network message handling
 *
 * V2 : Gestion intelligente des HP
 *   - Unités qu'on possède : accepte uniquement les baisses de HP (dégâts distants)
 *   - Unités distantes : accepte la mise à jour complète (position + HP)
 *   - Utilise unit_id comme index de slot pour cohérence avec Python
 */

#include "protocol.h"
#include <stdio.h>
#include <string.h>

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
        /* Ignore nos propres messages */
        if (msg->sender_id == local_state->my_peer_id) {
            break;
        }

        /* Utilise unit_id comme index de slot (cohérent avec Python) */
        uint16_t uid = msg->unit_id;
        if (uid >= MAX_UNITS) {
            fprintf(stderr, "[proto] unit_id %d hors limites\n", uid);
            break;
        }

        UnitState *local_unit = &local_state->units[uid];

        /* Si le slot est vide, on l'initialise */
        if (local_unit->hp_max == 0 && uid >= local_state->unit_count) {
            local_state->unit_count = uid + 1;
        }

        if (local_unit->owner_peer == local_state->my_peer_id && local_unit->hp_max > 0) {
            /*
             * NOTRE unité — l'adversaire nous signale des dégâts.
             * On accepte UNIQUEMENT si le HP reçu est inférieur (dégâts).
             */
            if (msg->unit.hp < local_unit->hp) {
                local_unit->hp    = msg->unit.hp;
                local_unit->alive = (local_unit->hp > 0) ? 1 : 0;
            }
        } else {
            /*
             * Unité DISTANTE — on accepte la mise à jour complète
             * (position, HP, alive).
             */
            local_unit->id         = msg->unit.id;
            local_unit->team       = msg->unit.team;
            local_unit->owner_peer = msg->unit.owner_peer;
            local_unit->alive      = msg->unit.alive;
            local_unit->x          = msg->unit.x;
            local_unit->y          = msg->unit.y;
            local_unit->hp         = msg->unit.hp;
            local_unit->hp_max     = msg->unit.hp_max;
        }

        /* Ne PAS remettre dirty=1, sinon on re-broadcast en boucle ! */
        local_unit->dirty = 0;
        break;
    }

    case MSG_OWN_REQUEST:
    case MSG_OWN_GRANT:
    case MSG_OWN_DENY:
        break;

    default:
        fprintf(stderr, "[proto] type de message inconnu: %d\n", msg->type);
        break;
    }
}
