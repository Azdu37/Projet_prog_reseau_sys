#ifndef PROTOCOL_NET_H
#define PROTOCOL_NET_H

/*
 * protocol.h (c_network) — Logique de protocole réseau
 *
 * V1 : traitement des messages MSG_STATE_UPDATE reçus.
 * V2 : ajoutera MSG_OWN_REQUEST / GRANT / DENY (ownership).
 *
 * NE PAS CONFONDRE avec shared/protocol.h qui définit les structures.
 */

#include "../shared/protocol.h"

/* ─────────────────────────────────────────────
 * Traitement des messages entrants
 * ───────────────────────────────────────────── */

/**
 * proto_handle_incoming - Applique un message reçu à l'état local.
 *
 *   V1 : si MSG_STATE_UPDATE → met à jour local_state->units[msg->unit_id]
 *
 * @param msg          Le message reçu depuis le réseau
 * @param local_state  L'état local à mettre à jour (écrit ensuite en shm)
 */
void proto_handle_incoming(const NetMessage *msg, GameState *local_state);

#endif /* PROTOCOL_NET_H */
