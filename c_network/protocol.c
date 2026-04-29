/*
 * protocol.c — Gestion des messages réseau entrants
 *
 * V3 : Handshake deux phases avant le démarrage de la bataille.
 *
 *   Phase HELLO :
 *     - Dès que le processus C est prêt, il diffuse MSG_HELLO à tous les pairs.
 *     - Quand il reçoit MSG_HELLO d'un pair, il le mémorise et répond MSG_READY.
 *
 *   Phase READY :
 *     - Quand il a reçu MSG_HELLO de TOUS les pairs attendus (g_expected_peers),
 *       il passe both_ready=1 dans la SHM → Python peut lancer game_loop().
 *
 *   Pendant le handshake les messages MSG_STATE_UPDATE sont ignorés.
 */

#include "protocol.h"
#include "network.h"
#include <stdio.h>
#include <string.h>

/* ── État interne du handshake ─────────────────────────────────────────────── */
static int g_handshake_done   = 0;
static int g_peers_said_hello = 0;   /* bitmask des pairs dont on a reçu HELLO */
static int g_expected_peers   = 1;   /* nombre de pairs attendus (mis à jour par main) */

/* ── API publique ───────────────────────────────────────────────────────────── */

void proto_set_expected_peers(int n)
{
    g_expected_peers = n;
}

int proto_handshake_done(void)
{
    return g_handshake_done;
}

/* Diffuse MSG_HELLO à tous les pairs enregistrés */
void proto_send_hello(uint8_t my_peer_id)
{
    NetMessage msg;
    memset(&msg, 0, sizeof(msg));
    msg.magic     = PROTOCOL_MAGIC;
    msg.type      = MSG_HELLO;
    msg.sender_id = my_peer_id;
    msg.unit_id   = 0;
    net_broadcast(&msg);
    printf("[DEMO-SHAKE] Peer %d envoie HELLO\n", my_peer_id);
}

/* ── Traitement du handshake sur réception ──────────────────────────────────── */
static void handle_hello(const NetMessage *msg, GameState *state)
{
    if (!state->python_ready) {
        return;
    }

    int bit = (1 << msg->sender_id);
    if (g_peers_said_hello & bit) {
        /* Déjà vu, mais on renvoie quand même READY au cas où il n'aurait pas reçu */
        NetMessage reply;
        memset(&reply, 0, sizeof(reply));
        reply.magic     = PROTOCOL_MAGIC;
        reply.type      = MSG_READY;
        reply.sender_id = state->my_peer_id;
        net_send_to(msg->sender_id, &reply);
        return;
    }

    g_peers_said_hello |= bit;
    printf("[DEMO-SHAKE] Peer %d reçu HELLO de peer %d (%d/%d pairs)\n",
           state->my_peer_id, msg->sender_id, __builtin_popcount(g_peers_said_hello), g_expected_peers);

    /* Répondre avec MSG_READY */
    NetMessage reply;
    memset(&reply, 0, sizeof(reply));
    reply.magic     = PROTOCOL_MAGIC;
    reply.type      = MSG_READY;
    reply.sender_id = state->my_peer_id;
    net_send_to(msg->sender_id, &reply);
    printf("[DEMO-SHAKE] Peer %d envoie READY à peer %d\n", state->my_peer_id, msg->sender_id);

    /* Si tous les pairs attendus ont dit bonjour → go */
    if (__builtin_popcount(g_peers_said_hello) >= g_expected_peers) {
        g_handshake_done    = 1;
        state->both_ready   = 1;
        printf("[DEMO-SHAKE] ✓ Handshake complet (peer %d) ! La bataille commence.\n", state->my_peer_id);
    }
}

static void handle_ready(const NetMessage *msg, GameState *state)
{
    if (!state->python_ready) {
        return;
    }

    /*
     * MSG_READY = confirmation que l'autre a bien reçu notre HELLO.
     * Si pour une raison quelconque on n'avait pas encore enregistré
     * son HELLO (paquets dans le désordre), on le fait ici.
     */
    int bit = (1 << msg->sender_id);
    if (!(g_peers_said_hello & bit)) {
        g_peers_said_hello |= bit;
        printf("[DEMO-SHAKE] Peer %d reçu READY de peer %d (Hello implicite)\n",
               state->my_peer_id, msg->sender_id);
    }

    if (__builtin_popcount(g_peers_said_hello) >= g_expected_peers) {
        g_handshake_done    = 1;
        state->both_ready   = 1;
        printf("[DEMO-SHAKE] ✓ Handshake complet via READY (peer %d) !\n", state->my_peer_id);
    }
}

/* ── Traitement des messages de jeu ─────────────────────────────────────────── */
void proto_handle_incoming(const NetMessage *msg, GameState *local_state)
{
    if (!msg || !local_state) return;

    if (msg->magic != PROTOCOL_MAGIC) {
        fprintf(stderr, "[proto] magic invalide 0x%08X, ignore\n", msg->magic);
        return;
    }

    switch ((MsgType)msg->type) {

    /* ── Handshake ── */
    case MSG_HELLO:
        handle_hello(msg, local_state);
        return;

    case MSG_READY:
        handle_ready(msg, local_state);
        return;

    /* ── Messages de jeu : ignorés pendant le handshake ── */
    case MSG_STATE_UPDATE: {
        if (!g_handshake_done) return;

        if (msg->sender_id == local_state->my_peer_id) break;

        uint16_t uid = msg->unit_id;
        if (uid >= MAX_UNITS) {
            fprintf(stderr, "[proto] unit_id %d hors limites\n", uid);
            break;
        }

        UnitState *local_unit = &local_state->units[uid];

        if (local_unit->hp_max == 0 && uid >= local_state->unit_count)
            local_state->unit_count = uid + 1;

        if (local_unit->owner_peer == local_state->my_peer_id && local_unit->hp_max > 0) {
            if (msg->unit.hp < local_unit->hp) {
                printf("[DEMO-SYNC] Peer %d: reçu dégâts unite %d (%d → %d HP)\n",
                       local_state->my_peer_id, uid, local_unit->hp, msg->unit.hp);
                local_unit->hp    = msg->unit.hp;
                local_unit->alive = (local_unit->hp > 0) ? 1 : 0;
            }
        } else {
            printf("[DEMO-SYNC] Peer %d: reçu état unite %d @(%.1f,%.1f) owner=%d\n",
                   local_state->my_peer_id, uid, msg->unit.x, msg->unit.y, msg->unit.owner_peer);
            local_unit->id         = msg->unit.id;
            local_unit->team       = msg->unit.team;
            local_unit->owner_peer = msg->unit.owner_peer;
            local_unit->alive      = msg->unit.alive;
            local_unit->x          = msg->unit.x;
            local_unit->y          = msg->unit.y;
            local_unit->hp         = msg->unit.hp;
            local_unit->hp_max     = msg->unit.hp_max;
        }
        local_unit->dirty = 0;
        break;
    }

    case MSG_OWN_REQUEST: {
        if (!g_handshake_done) return;

        uint16_t uid = msg->unit_id;
        if (uid >= MAX_UNITS) break;

        UnitState *local_unit = &local_state->units[uid];

        if (local_unit->owner_peer == local_state->my_peer_id) {
            printf("[DEMO-OWN] ✓ Peer %d: ACCORDE propriété unite %d à peer %d\n",
                   local_state->my_peer_id, uid, msg->sender_id);
            local_unit->owner_peer = msg->sender_id;
            local_unit->dirty      = 0;

            NetMessage grant;
            memset(&grant, 0, sizeof(grant));
            grant.magic     = PROTOCOL_MAGIC;
            grant.type      = MSG_OWN_GRANT;
            grant.sender_id = local_state->my_peer_id;
            grant.unit_id   = uid;
            memcpy(&grant.unit, local_unit, sizeof(UnitState));
            net_send_to(msg->sender_id, &grant);
        } else {
            printf("[DEMO-OWN] ✗ Peer %d: REFUSE propriété unite %d (propriétaire: peer %d)\n",
                   local_state->my_peer_id, uid, local_unit->owner_peer);
        }
        break;
    }

    case MSG_OWN_GRANT: {
        if (!g_handshake_done) return;

        uint16_t uid = msg->unit_id;
        if (uid >= MAX_UNITS) break;

        UnitState *local_unit = &local_state->units[uid];
        printf("[DEMO-OWN] ✓ Peer %d: REÇOIT propriété unite %d de peer %d\n",
               local_state->my_peer_id, uid, msg->sender_id);
        memcpy(local_unit, &msg->unit, sizeof(UnitState));
        local_unit->owner_peer = local_state->my_peer_id;
        local_unit->dirty      = 1;
        break;
    }

    case MSG_OWN_DENY:
        break;

    default:
        fprintf(stderr, "[proto] type de message inconnu: %d\n", msg->type);
        break;
    }
}
