#ifndef NETWORK_H
#define NETWORK_H

/*
 * network.h — Interface des sockets UDP entre les processus C
 *
 * V1 : chaque pair envoie les mises à jour de ses unités (dirty=1)
 *      à tous les autres pairs en UDP.
 */

#include <stdint.h>
#include <netinet/in.h>    /* struct sockaddr_in */
#include "../shared/protocol.h"

/* ─────────────────────────────────────────────
 * Gestion des pairs (peers)
 * ───────────────────────────────────────────── */

/** Adresse IP + port d'un pair */
typedef struct {
    struct sockaddr_in addr;
    uint8_t            peer_id;
} Peer;

/* ─────────────────────────────────────────────
 * Initialisation / fermeture
 * ───────────────────────────────────────────── */

/**
 * net_init - Crée et lie le socket UDP sur le port donné.
 *            Place le socket en mode non-bloquant.
 * @param port   Port d'écoute local (ex: NET_PORT = 9000)
 * @return 0 si succès, -1 si erreur
 */
int net_init(uint16_t port);

/**
 * net_close - Ferme le socket.
 */
void net_close(void);

/* ─────────────────────────────────────────────
 * Gestion des pairs
 * ───────────────────────────────────────────── */

/**
 * net_add_peer - Enregistre un pair (IP en string + port).
 * @param ip_str    Ex: "192.168.1.2"
 * @param port      Ex: NET_PORT
 * @param peer_id   Index logique du pair
 * @return 0 si succès, -1 si erreur ou trop de pairs
 */
int net_add_peer(const char *ip_str, uint16_t port, uint8_t peer_id);

/* ─────────────────────────────────────────────
 * Envoi / réception
 * ───────────────────────────────────────────── */

/**
 * net_send_state_update - Sérialise une UnitState dans un NetMessage
 *                          et l'envoie à un pair précis.
 * @param unit       L'unité dont l'état a changé
 * @param peer_id    Index du pair destinataire
 * @param sender_id  Notre propre index de pair
 * @return 0 si succès, -1 si erreur
 */
int net_send_state_update(const UnitState *unit,
                          uint8_t peer_id,
                          uint8_t sender_id);

/**
 * net_broadcast_state_update - Envoie à TOUS les pairs enregistrés.
 * @return nombre de pairs atteints, -1 si erreur
 */
int net_broadcast_state_update(const UnitState *unit, uint8_t sender_id);

/**
 * net_recv - Essaie de recevoir un message (NON-BLOQUANT).
 *            Retourne 0 si aucun message disponible,
 *            1 si un message a été reçu dans *msg_out*,
 *           -1 si erreur réseau.
 */
int net_recv(NetMessage *msg_out);

#endif /* NETWORK_H */
