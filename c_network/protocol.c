/*
 * protocol.c — Traitement des messages réseau entrants
 *
 * V1 : seul MSG_STATE_UPDATE est géré.
 *      On met à jour l'unité concernée dans local_state
 *      uniquement si le message vient d'un autre pair
 *      (on ne s'écrase pas soi-même).
 *
 * V2 : on ajoutera ici MSG_OWN_REQUEST / GRANT / DENY.
 */

#include "protocol.h"
#include <stdio.h>
#include <string.h>

/* ─────────────────────────────────────────────
 * proto_handle_incoming
 * ───────────────────────────────────────────── */
void proto_handle_incoming(const NetMessage *msg, GameState *local_state)
{
    if (!msg || !local_state) return;

    /* Sanity checks */
    if (msg->magic != PROTOCOL_MAGIC) {
        fprintf(stderr, "[proto] magic invalide 0x%08X, ignoré\n", msg->magic);
        return;
    }
    if (msg->unit_id >= MAX_UNITS) {
        fprintf(stderr, "[proto] unit_id %d hors limites, ignoré\n", msg->unit_id);
        return;
    }

    switch ((MsgType)msg->type) {

    /* ── V1 : mise à jour d'état ─────────────────── */
    case MSG_STATE_UPDATE: {
        /* On ignore les updates qu'on a envoyées nous-mêmes */
        if (msg->sender_id == local_state->my_peer_id) break;

        UnitState *local_unit = &local_state->units[msg->unit_id];

        /* Copie les champs mis à jour (sans écraser notre dirty flag) */
        local_unit->id         = msg->unit.id;
        local_unit->team       = msg->unit.team;
        local_unit->owner_peer = msg->unit.owner_peer;
        local_unit->alive      = msg->unit.alive;
        local_unit->x          = msg->unit.x;
        local_unit->y          = msg->unit.y;
        local_unit->hp         = msg->unit.hp;
        local_unit->hp_max     = msg->unit.hp_max;
        /* dirty reste à 0 côté récepteur : c'est l'info distante */

        printf("[proto] unité %d mise à jour (peer %d) → x=%.1f y=%.1f hp=%d\n",
               msg->unit_id, msg->sender_id,
               msg->unit.x, msg->unit.y, msg->unit.hp);
        break;
    }

    /* ── V2 (pas encore implémenté) ─────────────── */
    case MSG_OWN_REQUEST:
    case MSG_OWN_GRANT:
    case MSG_OWN_DENY:
        printf("[proto] message V2 type=%d reçu, ignoré en V1\n", msg->type);
        break;

    default:
        fprintf(stderr, "[proto] type de message inconnu: %d\n", msg->type);
        break;
    }
}