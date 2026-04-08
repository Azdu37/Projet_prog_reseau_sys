/*
 * network.c — Sockets UDP entre les processus C
 *
 * V1 : envoi/réception de NetMessage (MSG_STATE_UPDATE) en UDP.
 *      Le socket est NON-BLOQUANT : net_recv() retourne immédiatement
 *      s'il n'y a rien à lire.
 *
 * Compilation : gcc ... (Linux/WSL, pas de lib supplémentaire nécessaire)
 */

#include "network.h"

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/socket.h>

/* ─────────────────────────────────────────────
 * État interne
 * ───────────────────────────────────────────── */
static int    g_sock = -1;              /* socket UDP                 */
static Peer   g_peers[MAX_PEERS];      /* liste des pairs connus     */
static int    g_peer_count = 0;

/* ─────────────────────────────────────────────
 * net_init
 * Crée le socket UDP, le lie sur le port local
 * et le place en mode non-bloquant.
 * ───────────────────────────────────────────── */
int net_init(uint16_t port)
{
    g_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (g_sock < 0) {
        perror("[net] socket");
        return -1;
    }

    /* Option : réutiliser le port si le process précédent a crashé */
    int opt = 1;
    setsockopt(g_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    /* Bind sur toutes les interfaces, port donné */
    struct sockaddr_in local = {0};
    local.sin_family      = AF_INET;
    local.sin_addr.s_addr = INADDR_ANY;
    local.sin_port        = htons(port);

    if (bind(g_sock, (struct sockaddr *)&local, sizeof(local)) < 0) {
        perror("[net] bind");
        close(g_sock);
        g_sock = -1;
        return -1;
    }

    /* Mode non-bloquant : net_recv ne bloque jamais */
    int flags = fcntl(g_sock, F_GETFL, 0);
    fcntl(g_sock, F_SETFL, flags | O_NONBLOCK);

    printf("[net] socket UDP prêt sur le port %d\n", port);
    return 0;
}

/* ─────────────────────────────────────────────
 * net_close
 * ───────────────────────────────────────────── */
void net_close(void)
{
    if (g_sock >= 0) {
        close(g_sock);
        g_sock = -1;
    }
}

/* ─────────────────────────────────────────────
 * net_add_peer
 * Enregistre l'adresse d'un pair distant.
 * ───────────────────────────────────────────── */
int net_add_peer(const char *ip_str, uint16_t port, uint8_t peer_id)
{
    if (g_peer_count >= MAX_PEERS) {
        fprintf(stderr, "[net] trop de pairs (max %d)\n", MAX_PEERS);
        return -1;
    }

    Peer *p = &g_peers[g_peer_count];
    memset(p, 0, sizeof(Peer));

    p->addr.sin_family = AF_INET;
    p->addr.sin_port   = htons(port);
    p->peer_id         = peer_id;

    if (inet_pton(AF_INET, ip_str, &p->addr.sin_addr) <= 0) {
        fprintf(stderr, "[net] adresse IP invalide: %s\n", ip_str);
        return -1;
    }

    g_peer_count++;
    printf("[net] pair %d ajouté : %s:%d\n", peer_id, ip_str, port);
    return 0;
}

/* ─────────────────────────────────────────────
 * net_send_state_update
 * Envoie l'état d'une unité à un pair précis.
 * ───────────────────────────────────────────── */
int net_send_state_update(const UnitState *unit,
                          uint8_t peer_id,
                          uint8_t sender_id)
{
    if (g_sock < 0) return -1;

    /* Trouve le pair dans la liste */
    Peer *dest = NULL;
    for (int i = 0; i < g_peer_count; i++) {
        if (g_peers[i].peer_id == peer_id) {
            dest = &g_peers[i];
            break;
        }
    }
    if (!dest) {
        fprintf(stderr, "[net] pair %d inconnu\n", peer_id);
        return -1;
    }

    /* Construit le message */
    NetMessage msg = {0};
    msg.magic     = PROTOCOL_MAGIC;
    msg.type      = MSG_STATE_UPDATE;
    msg.sender_id = sender_id;
    msg.unit_id   = unit->id;
    msg.unit      = *unit;
    msg.unit.dirty = 0;   /* Le destinataire ne reçoit pas le flag dirty */

    ssize_t sent = sendto(g_sock,
                          &msg, sizeof(NetMessage), 0,
                          (struct sockaddr *)&dest->addr,
                          sizeof(dest->addr));
    if (sent < 0) {
        perror("[net] sendto");
        return -1;
    }
    return 0;
}

/* ─────────────────────────────────────────────
 * net_broadcast_state_update
 * Envoie à TOUS les pairs enregistrés.
 * ───────────────────────────────────────────── */
int net_broadcast_state_update(const UnitState *unit, uint8_t sender_id)
{
    int ok = 0;
    for (int i = 0; i < g_peer_count; i++) {
        if (net_send_state_update(unit, g_peers[i].peer_id, sender_id) == 0)
            ok++;
    }
    return ok;
}

/* ─────────────────────────────────────────────
 * net_recv
 * Tente de recevoir un message (NON-BLOQUANT).
 *  Retourne :  1 → message reçu dans *msg_out*
 *              0 → aucun message disponible
 *             -1 → erreur réseau
 * ───────────────────────────────────────────── */
int net_recv(NetMessage *msg_out)
{
    if (g_sock < 0) return -1;

    struct sockaddr_in sender_addr;
    socklen_t addr_len = sizeof(sender_addr);

    ssize_t n = recvfrom(g_sock,
                         msg_out, sizeof(NetMessage), 0,
                         (struct sockaddr *)&sender_addr,
                         &addr_len);

    if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return 0;   /* aucun message, tout va bien */
        perror("[net] recvfrom");
        return -1;
    }

    /* Vérifie le magic number pour ignorer les paquets parasites */
    if (msg_out->magic != PROTOCOL_MAGIC) {
        fprintf(stderr, "[net] magic invalide, paquet ignoré\n");
        return 0;
    }

    return 1;
}
