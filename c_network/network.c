#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include "network.h"

int num_peers = 0;
struct sockaddr_in peers[MAX_PEERS];
static int p2p_fd = -1;

int network_init(int p2p_port) {
    p2p_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (p2p_fd < 0) {
        perror("p2p socket failed");
        return -1;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(p2p_port);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(p2p_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("p2p bind failed");
        close(p2p_fd);
        return -1;
    }

    return 0;
}

void broadcast_to_peers(const NetworkMessage *msg) {
    for (int i = 0; i < num_peers; i++) {
        sendto(p2p_fd, msg, sizeof(NetworkMessage), 0,
               (struct sockaddr *)&peers[i], sizeof(peers[i]));
    }
}

int receive_from_remote(NetworkMessage *msg) {
    ssize_t n = recvfrom(p2p_fd, msg, sizeof(NetworkMessage), 0, NULL, NULL);
    return (int)n;
}

void network_cleanup(void) {
    if (p2p_fd >= 0) close(p2p_fd);
}
