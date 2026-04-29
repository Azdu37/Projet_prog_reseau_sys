#include "network.h"
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/socket.h>

static int  g_sock = -1;
static Peer g_peers[MAX_PEERS];
static int  g_peer_count = 0;

int net_init(uint16_t port)
{
    g_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (g_sock < 0) { perror("socket"); return -1; }

    int opt = 1;
    setsockopt(g_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in local = {0};
    local.sin_family = AF_INET;
    local.sin_addr.s_addr = INADDR_ANY;
    local.sin_port = htons(port);

    if (bind(g_sock, (struct sockaddr *)&local, sizeof(local)) < 0) {
        perror("bind"); close(g_sock); g_sock = -1; return -1;
    }

    fcntl(g_sock, F_SETFL, fcntl(g_sock, F_GETFL, 0) | O_NONBLOCK);
    return 0;
}

void net_close(void)
{
    if (g_sock >= 0) { close(g_sock); g_sock = -1; }
}

int net_add_peer(const char *ip, uint16_t port, uint8_t peer_id)
{
    if (g_peer_count >= MAX_PEERS) return -1;
    Peer *p = &g_peers[g_peer_count];
    memset(p, 0, sizeof(Peer));
    p->addr.sin_family = AF_INET;
    p->addr.sin_port = htons(port);
    p->peer_id = peer_id;
    if (inet_pton(AF_INET, ip, &p->addr.sin_addr) <= 0) return -1;
    g_peer_count++;
    return 0;
}

int net_send(const UnitState *unit, uint8_t peer_id, uint8_t sender_id)
{
    if (g_sock < 0) return -1;

    Peer *dest = NULL;
    for (int i = 0; i < g_peer_count; i++)
        if (g_peers[i].peer_id == peer_id) { dest = &g_peers[i]; break; }
    if (!dest) return -1;

    NetMessage msg = {0};
    msg.magic = PROTOCOL_MAGIC;
    msg.type = MSG_STATE_UPDATE;
    msg.sender_id = sender_id;
    msg.unit_id = unit->id;
    msg.unit = *unit;
    msg.unit.dirty = 0;

    ssize_t s = sendto(g_sock, &msg, sizeof(msg), 0,
                       (struct sockaddr *)&dest->addr, sizeof(dest->addr));
    return (s < 0) ? -1 : 0;
}

static int net_send_request(uint16_t unit_id, uint8_t peer_id, uint8_t sender_id)
{
    if (g_sock < 0) return -1;

    Peer *dest = NULL;
    for (int i = 0; i < g_peer_count; i++)
        if (g_peers[i].peer_id == peer_id) { dest = &g_peers[i]; break; }
    if (!dest) return -1;

    NetMessage msg = {0};
    msg.magic = PROTOCOL_MAGIC;
    msg.type = MSG_OWNERSHIP_REQUEST;
    msg.sender_id = sender_id;
    msg.unit_id = unit_id;

    ssize_t s = sendto(g_sock, &msg, sizeof(msg), 0,
                       (struct sockaddr *)&dest->addr, sizeof(dest->addr));
    return (s < 0) ? -1 : 0;
}

int net_broadcast(const UnitState *unit, uint8_t sender_id)
{
    int ok = 0;
    for (int i = 0; i < g_peer_count; i++)
        if (net_send(unit, g_peers[i].peer_id, sender_id) == 0) ok++;
    return ok;
}

int net_broadcast_request(uint16_t unit_id, uint8_t sender_id)
{
    int ok = 0;
    for (int i = 0; i < g_peer_count; i++)
        if (net_send_request(unit_id, g_peers[i].peer_id, sender_id) == 0) ok++;
    return ok;
}

int net_recv(NetMessage *msg_out)
{
    if (g_sock < 0) return -1;
    struct sockaddr_in from;
    socklen_t len = sizeof(from);

    ssize_t n = recvfrom(g_sock, msg_out, sizeof(NetMessage), 0,
                         (struct sockaddr *)&from, &len);
    if (n < 0)
        return (errno == EAGAIN || errno == EWOULDBLOCK) ? 0 : -1;
    if (msg_out->magic != PROTOCOL_MAGIC) return 0;
    return 1;
}
