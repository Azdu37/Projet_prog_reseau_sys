// Ce fichier contient le point d'entrée du programme réseau.
// Il fait le lien entre la mémoire partagée et le réseau UDP en transmettant l'état du jeu en continu.

#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include "ipc.h"
#include "network.h"
#include "protocol.h"

static volatile int g_running = 1;
static void on_sigint(int s) { (void)s; g_running = 0; }

int main(int argc, char *argv[])
{
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <peer_id> <ip_pair> [...]\n", argv[0]);
        return 1;
    }

    uint8_t my_id = (uint8_t)atoi(argv[1]);

    if (ipc_init(SHM_NAME, SEM_WRITE_NAME, SEM_READ_NAME, 1) < 0) return 1;
    if (net_init(NET_PORT) < 0) { ipc_close(); return 1; }

    uint8_t pid = 0;
    for (int i = 2; i < argc; i++) {
        while (pid == my_id) pid++;
        net_add_peer(argv[i], NET_PORT, pid++);
    }

    signal(SIGINT, on_sigint);

    GameState state;
    NetMessage msg;

    while (g_running) {
        if (ipc_read_state(&state) < 0) break;
        state.my_peer_id = my_id;

        for (int i = 0; i < state.unit_count; i++) {
            if (state.units[i].dirty) {
                net_broadcast(&state.units[i], my_id);
                state.units[i].dirty = 0;
            }
        }

        int ret;
        while ((ret = net_recv(&msg)) == 1)
            proto_handle_incoming(&msg, &state);
        if (ret < 0) break;

        if (ipc_write_state(&state) < 0) break;
        usleep(16000);
    }

    net_close();
    ipc_close();
    return 0;
}
