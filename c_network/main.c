/*
 * main.c — Point d'entrée du processus C réseau (V3 : handshake)
 *
 * Usage :
 *   ./c_net <mon_peer_id> <ip_pair1>[:id[:port]] [<ip_pair2> ...]
 *
 * Exemple (PC A = peer 0, PC B = peer 1) :
 *   Sur PC A : ./c_net 0 192.168.1.2
 *   Sur PC B : ./c_net 1 192.168.1.1
 *
 * Séquence de démarrage :
 *   1. Init IPC + réseau
 *   2. Boucle HANDSHAKE : envoie MSG_HELLO toutes les 500ms,
 *      traite les MSG_HELLO / MSG_READY entrants,
 *      jusqu'à proto_handshake_done() == 1.
 *      Écrit both_ready=1 dans la SHM pour signaler Python.
 *   3. Boucle JEUX normale (60 Hz).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

#include "ipc.h"
#include "network.h"
#include "protocol.h"

/* ── Gestion SIGINT ─────────────────────────────────────────────────────────── */
static volatile int g_running = 1;

static void handle_sigint(int sig)
{
    (void)sig;
    printf("\n[main] Arret demande...\n");
    g_running = 0;
}

/* ── Broadcast des unités dirty ─────────────────────────────────────────────── */
static void broadcast_dirty_units(GameState *state)
{
    for (int i = 0; i < state->unit_count; i++) {
        UnitState *u = &state->units[i];

        if (u->dirty == 1) {
            net_broadcast_state_update(u, state->my_peer_id);
            u->dirty = 0;
        }
        else if (u->dirty == 2) {
            printf("[main] Envoi requete propriete pour unite %d\n", u->id);
            NetMessage msg;
            memset(&msg, 0, sizeof(msg));
            msg.magic     = PROTOCOL_MAGIC;
            msg.type      = MSG_OWN_REQUEST;
            msg.sender_id = state->my_peer_id;
            msg.unit_id   = u->id;
            net_broadcast(&msg);
            u->dirty = 0;
        }
    }
}

/* ── main ───────────────────────────────────────────────────────────────────── */
int main(int argc, char *argv[])
{
    if (argc < 3) {
        fprintf(stderr,
            "Usage: %s <mon_peer_id> <ip_pair1> [<ip_pair2> ...]\n"
            "Exemple: %s 0 192.168.1.2\n",
            argv[0], argv[0]);
        return 1;
    }

    uint8_t my_peer_id = (uint8_t)atoi(argv[1]);
    printf("[main] Demarrage — peer_id=%d\n", my_peer_id);

    /* ── Port ───────────────────────────────────────────────────────────────── */
    uint16_t port = NET_PORT;
    char *port_env = getenv("NET_PORT");
    if (port_env) port = (uint16_t)atoi(port_env);
    printf("[main] Port local : %d\n", port);

    /* ── IPC ────────────────────────────────────────────────────────────────── */
    char *shm_name = SHM_NAME;
    char *sem_w    = SEM_WRITE_NAME;
    char *sem_r    = SEM_READ_NAME;
    if (getenv("SHM_NAME")) shm_name = getenv("SHM_NAME");
    if (getenv("SEM_W"))    sem_w    = getenv("SEM_W");
    if (getenv("SEM_R"))    sem_r    = getenv("SEM_R");

    if (ipc_init(shm_name, sem_w, sem_r, 1) < 0) {
        fprintf(stderr, "[main] Erreur IPC\n");
        return 1;
    }

    /* ── Réseau ─────────────────────────────────────────────────────────────── */
    if (net_init(port) < 0) {
        ipc_close();
        return 1;
    }

    int nb_pairs = argc - 2;
    for (int i = 2; i < argc; i++) {
        char   *arg        = argv[i];
        char   *colon      = strchr(arg, ':');
        uint8_t peer_id;
        uint16_t peer_port = port;
        char    ip[64];

        if (colon) {
            size_t ip_len = (size_t)(colon - arg);
            if (ip_len >= sizeof(ip)) ip_len = sizeof(ip) - 1;
            strncpy(ip, arg, ip_len);
            ip[ip_len] = '\0';

            char *next_colon = strchr(colon + 1, ':');
            if (next_colon) {
                peer_id   = (uint8_t)atoi(colon + 1);
                peer_port = (uint16_t)atoi(next_colon + 1);
            } else {
                peer_id = (uint8_t)atoi(colon + 1);
            }
        } else {
            strncpy(ip, arg, sizeof(ip) - 1);
            ip[sizeof(ip)-1] = '\0';
            peer_id = (uint8_t)(i - 1);
            if (peer_id == my_peer_id) peer_id = 0;
        }

        if (net_add_peer(ip, peer_port, peer_id) < 0)
            fprintf(stderr, "[main] Impossible d'ajouter le pair %s\n", ip);
        else
            printf("[main] Pair ajoute : %s:%d (ID=%d)\n", ip, peer_port, peer_id);
    }

    /* Informe le module protocol du nombre de pairs à attendre */
    proto_set_expected_peers(nb_pairs);

    signal(SIGINT, handle_sigint);

    /* ════════════════════════════════════════════════════════════════════════
     * PHASE 1 — HANDSHAKE
     * On attend que tous les pairs soient prêts avant de lancer le jeu.
     * ════════════════════════════════════════════════════════════════════════ */
    printf("[main] === Phase HANDSHAKE : attente des %d pair(s)... ===\n", nb_pairs);

    GameState local_state;
    NetMessage incoming;

    /* Initialise l'état local depuis la SHM (Python a peut-être déjà écrit) */
    ipc_read_state(&local_state);
    local_state.my_peer_id  = my_peer_id;
    local_state.both_ready  = 0;
    ipc_write_state(&local_state);

    /* Envoie immédiatement un premier HELLO */
    proto_send_hello(my_peer_id);

    long hello_timer = 0;   /* compteur en ms pour renvoyer HELLO si besoin */

    while (g_running && !proto_handshake_done()) {

        /* Re-envoyer MSG_HELLO toutes les 500 ms (UDP peu fiable) */
        hello_timer += 16;
        if (hello_timer >= 500) {
            hello_timer = 0;
            proto_send_hello(my_peer_id);
        }

        /* Traite tous les messages UDP entrants */
        int ret;
        while ((ret = net_recv(&incoming)) == 1) {
            proto_handle_incoming(&incoming, &local_state);
        }
        if (ret < 0) {
            fprintf(stderr, "[main] Erreur reseau pendant handshake\n");
            break;
        }

        /* Écrit l'état dans la SHM pour que Python voie both_ready */
        local_state.my_peer_id = my_peer_id;
        ipc_write_state(&local_state);

        usleep(16000);   /* ~60 Hz */
    }

    if (!proto_handshake_done()) {
        fprintf(stderr, "[main] Handshake interrompu.\n");
        net_close();
        ipc_close();
        return 1;
    }

    /* S'assure que both_ready=1 est bien dans la SHM */
    ipc_read_state(&local_state);
    local_state.both_ready = 1;
    ipc_write_state(&local_state);
    printf("[main] both_ready=1 ecrit dans la SHM — Python peut demarrer.\n");

    /* ════════════════════════════════════════════════════════════════════════
     * PHASE 2 — BOUCLE DE JEU (60 Hz)
     * ════════════════════════════════════════════════════════════════════════ */
    printf("[main] === Boucle de jeu demarree (Ctrl+C pour arreter) ===\n");

    while (g_running) {

        /* 1. Lit l'état écrit par Python */
        if (ipc_read_state(&local_state) < 0) {
            fprintf(stderr, "[main] Erreur lecture SHM\n");
            break;
        }
        local_state.my_peer_id = my_peer_id;

        /* 2. Envoie les unités dirty */
        broadcast_dirty_units(&local_state);

        /* 3. Reçoit les messages entrants */
        int ret;
        while ((ret = net_recv(&incoming)) == 1) {
            proto_handle_incoming(&incoming, &local_state);
        }
        if (ret < 0) {
            fprintf(stderr, "[main] Erreur reseau\n");
            break;
        }

        /* Maintient both_ready=1 pour Python (robustesse) */
        local_state.both_ready = 1;

        /* 4. Réécrit dans la SHM */
        if (ipc_write_state(&local_state) < 0) {
            fprintf(stderr, "[main] Erreur ecriture SHM\n");
            break;
        }

        usleep(16000);
    }

    printf("[main] Fermeture propre\n");
    net_close();
    ipc_close();
    return 0;
}
