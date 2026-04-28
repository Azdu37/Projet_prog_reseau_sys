#ifndef NETWORK_H
#define NETWORK_H

#include <stdint.h>
#include <netinet/in.h>
#include "../shared/protocol.h"

typedef struct {
    struct sockaddr_in addr;
    uint8_t peer_id;
} Peer;

int  net_init(uint16_t port);
void net_close(void);
int  net_add_peer(const char *ip, uint16_t port, uint8_t peer_id);
int  net_send(const UnitState *unit, uint8_t peer_id, uint8_t sender_id);
int  net_broadcast(const UnitState *unit, uint8_t sender_id);
int  net_recv(NetMessage *msg_out);

#endif
