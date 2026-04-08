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

        /* N'envoie que les unités qu'on possède ET qui ont changé */
        if (u->dirty && u->owner_peer == state->my_peer_id) {
            net_broadcast_state_update(u, state->my_peer_id);
            u->dirty = 0;   /* acquitté localement */
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
    /*
     * create=0 : on suppose que Python a déjà créé la shm.
     * create=1 : si on veut tester sans Python, mettre 1.
     */
    if (ipc_init(SHM_NAME, SEM_WRITE_NAME, SEM_READ_NAME, 1) < 0) {
        fprintf(stderr, "[main] Erreur IPC (la shm Python est-elle lancée ?)\n");
        return 1;
    }

    /* ── Initialisation réseau ──────────────── */
    if (net_init(NET_PORT) < 0) {
        ipc_close();
        return 1;
    }

    /* Enregistre chaque pair passé en argument */
    for (int i = 2; i < argc; i++) {
        uint8_t peer_id = (uint8_t)(i - 1); /* peer 1, 2, 3... */
        if (net_add_peer(argv[i], NET_PORT, peer_id) < 0) {
            fprintf(stderr, "[main] Impossible d'ajouter le pair %s\n", argv[i]);
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
