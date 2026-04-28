/*
 * main.c — Point d'entrée du processus C réseau
 *
 * Usage :
 *   ./c_net <mon_peer_id> <ip_pair1> [<ip_pair2> ...]
 *
 * Exemple (PC A = peer 0, PC B = peer 1) :
 *   Sur PC A : ./c_net 0 192.168.1.2
 *   Sur PC B : ./c_net 1 192.168.1.1
 *
 * Boucle principale (V1) :
 *   1. Lit la shm (état Python local)
 *   2. Pour chaque unité dirty → broadcast UDP aux pairs
 *   3. Reçoit les messages UDP entrants → met à jour la shm
 *   4. Attend ~16ms (≈ 60 Hz)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

#include "ipc.h"
#include "network.h"
#include "protocol.h"

/* ─────────────────────────────────────────────
 * Gestion du signal SIGINT (Ctrl+C)
 * ───────────────────────────────────────────── */
static volatile int g_running = 1;

static void handle_sigint(int sig)
{
    (void)sig;
    printf("\n[main] Arrêt demandé...\n");
    g_running = 0;
}

/* ─────────────────────────────────────────────
 * Envoi de toutes les unités dirty aux pairs
 * ───────────────────────────────────────────── */
static void broadcast_dirty_units(GameState *state)
{
    for (int i = 0; i < state->unit_count; i++) {
        UnitState *u = &state->units[i];

        if (u->dirty == 1) {
            /* Envoi classique d'update d'état */
            net_broadcast_state_update(u, state->my_peer_id);
            u->dirty = 0;
        } 
        else if (u->dirty == 2) {
            /* Demande de propriété (V2) */
            printf("[main] Envoi requête propriété pour unité %d\n", u->id);
            NetMessage msg;
            msg.magic     = PROTOCOL_MAGIC;
            msg.type      = MSG_OWN_REQUEST;
            msg.sender_id = state->my_peer_id;
            msg.unit_id   = u->id;
            /* On l'envoie à tout le monde (ou au propriétaire connu) */
            net_broadcast(&msg);
            u->dirty = 0;
        }
    }
}

/* ─────────────────────────────────────────────
 * main
 * ───────────────────────────────────────────── */
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
    printf("[main] Démarrage — peer_id=%d\n", my_peer_id);

    /* ── Initialisation IPC ─────────────────── */
    char *shm_name = SHM_NAME;
    char *sem_w = SEM_WRITE_NAME;
    char *sem_r = SEM_READ_NAME;
    if (getenv("SHM_NAME")) shm_name = getenv("SHM_NAME");
    if (getenv("SEM_W")) sem_w = getenv("SEM_W");
    if (getenv("SEM_R")) sem_r = getenv("SEM_R");

    if (ipc_init(shm_name, sem_w, sem_r, 1) < 0) {
        fprintf(stderr, "[main] Erreur IPC (la shm Python est-elle lancée ?)\n");
        return 1;
    }

    /* ── Initialisation réseau ──────────────── */
    uint16_t port = NET_PORT;
    char *port_env = getenv("NET_PORT");
    if (port_env) port = (uint16_t)atoi(port_env);

    if (net_init(port) < 0) {
        ipc_close();
        return 1;
    }

    /* Enregistre chaque pair passé en argument */
    for (int i = 2; i < argc; i++) {
        char *arg = argv[i];
        char *colon = strchr(arg, ':');
        uint8_t peer_id;
        uint16_t peer_port = port; // Par défaut même port que nous
        char ip[64];

        if (colon) {
            /* Format IP:ID[:PORT] */
            size_t ip_len = colon - arg;
            if (ip_len >= sizeof(ip)) ip_len = sizeof(ip) - 1;
            strncpy(ip, arg, ip_len);
            ip[ip_len] = '\0';
            
            char *next_colon = strchr(colon + 1, ':');
            if (next_colon) {
                peer_id = (uint8_t)atoi(colon + 1);
                peer_port = (uint16_t)atoi(next_colon + 1);
            } else {
                peer_id = (uint8_t)atoi(colon + 1);
            }
        } else {
            /* Format IP seule */
            strncpy(ip, arg, sizeof(ip)-1);
            peer_id = (uint8_t)(i - 1);
            if (peer_id == my_peer_id) peer_id = 0;
        }

        if (net_add_peer(ip, peer_port, peer_id) < 0) {
            fprintf(stderr, "[main] Impossible d'ajouter le pair %s (id=%d, port=%d)\n", ip, peer_id, peer_port);
        }
    }

    /* ── Gestion de Ctrl+C ──────────────────── */
    signal(SIGINT, handle_sigint);

    /* ── Boucle principale V1 ───────────────── */
    printf("[main] Boucle démarrée (Ctrl+C pour arrêter)\n");

    GameState local_state;
    NetMessage incoming;

    while (g_running) {

        /* 1. Lit l'état depuis la shm (écrit par Python) */
        if (ipc_read_state(&local_state) < 0) {
            fprintf(stderr, "[main] Erreur lecture shm\n");
            break;
        }

        /* Garde my_peer_id cohérent (Python peut l'avoir mis) */
        local_state.my_peer_id = my_peer_id;

        /* 2. Envoie les unités modifiées sur le réseau */
        broadcast_dirty_units(&local_state);

        /* 3. Reçoit tous les messages disponibles (non-bloquant) */
        int ret;
        while ((ret = net_recv(&incoming)) == 1) {
            proto_handle_incoming(&incoming, &local_state);
        }
        if (ret < 0) {
            fprintf(stderr, "[main] Erreur réseau\n");
            break;
        }

        /* 4. Réécrit l'état dans la shm (Python lira les updates réseau) */
        if (ipc_write_state(&local_state) < 0) {
            fprintf(stderr, "[main] Erreur écriture shm\n");
            break;
        }

        /* 5. ~60 Hz */
        usleep(16000);
    }

    /* ── Nettoyage ──────────────────────────── */
    printf("[main] Fermeture propre\n");
    net_close();
    ipc_close();
    return 0;
}
