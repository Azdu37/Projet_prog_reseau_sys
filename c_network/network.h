#ifndef NETWORK_H
#define NETWORK_H

#include "protocol_def.h"
#include <arpa/inet.h>

extern int num_peers;
extern struct sockaddr_in peers[MAX_PEERS];

int network_init(int p2p_port);
void broadcast_to_peers(const NetworkMessage *msg);
int receive_from_remote(NetworkMessage *msg);
void network_cleanup(void);

#endif
