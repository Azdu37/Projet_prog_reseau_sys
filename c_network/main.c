#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <signal.h>
#include "protocol_def.h"
#include "network.h"
#include "ipc_local.h"

static int running = 1;

void handle_signal(int sig) {
    (void)sig;
    running = 0;
}

void *local_receiver_thread_fn(void *arg) {
    (void)arg;
    NetworkMessage msg;
    while (running) {
        int n = receive_from_python(&msg);
        if (n > 0) {
            broadcast_to_peers(&msg);
        }
    }
    return NULL;
}

void *remote_receiver_thread_fn(void *arg) {
    (void)arg;
    NetworkMessage msg;
    while (running) {
        int n = receive_from_remote(&msg);
        if (n > 0) {
            forward_to_python(&msg);
        }
    }
    return NULL;
}

int main(int argc, char **argv) {
    int p2p_port = PORT_P2P;
    uint32_t my_id = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--id") == 0 && i + 1 < argc) {
            my_id = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--p2p-port") == 0 && i + 1 < argc) {
            p2p_port = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--peers") == 0 && i + 1 < argc) {
            char *peers_str = strdup(argv[++i]);
            char *token = strtok(peers_str, ",");
            while (token && num_peers < MAX_PEERS) {
                char *colon = strchr(token, ':');
                if (colon) {
                    *colon = '\0';
                    peers[num_peers].sin_family = AF_INET;
                    peers[num_peers].sin_addr.s_addr = inet_addr(token);
                    peers[num_peers].sin_port = htons(atoi(colon + 1));
                    num_peers++;
                }
                token = strtok(NULL, ",");
            }
            free(peers_str);
        }
    }

    printf("[C_NETWORK] Starting: ID=%u, P2P_PORT=%d, PEERS=%d\n", my_id, p2p_port, num_peers);

    if (network_init(p2p_port) < 0) return 1;
    if (ipc_local_init() < 0) return 1;

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    pthread_t local_thread, remote_thread;
    pthread_create(&local_thread, NULL, local_receiver_thread_fn, NULL);
    pthread_create(&remote_thread, NULL, remote_receiver_thread_fn, NULL);

    // Send HELLO
    NetworkMessage hello;
    memset(&hello, 0, sizeof(hello));
    hello.msg_type = MSG_HELLO;
    hello.sender_id = my_id;
    broadcast_to_peers(&hello);

    while (running) {
        sleep(1);
    }

    pthread_cancel(local_thread);
    pthread_cancel(remote_thread);
    pthread_join(local_thread, NULL);
    pthread_join(remote_thread, NULL);

    network_cleanup();
    ipc_local_cleanup();

    return 0;
}
