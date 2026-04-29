#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

/*
 * protocol.h — Définitions du protocole réseau + structure IPC partagée
 *
 * Ce fichier est partagé entre :
 * - le processus C réseau
 * - la couche IPC
 * - le bridge Python (ctypes)
 *
 * Toute modification ici doit rester synchronisée avec p_game/network_bridge.py.
 */

/* ── Constantes globales ─────────────────────────────────────────────────── */
#define PROTOCOL_MAGIC   0xBABA1234u
#define PROTOCOL_VERSION 1

#define MAX_UNITS        256
#define MAX_PEERS        8

/* Noms IPC (mémoire partagée + sémaphores) */
#define SHM_NAME         "/battle_state"
#define SEM_WRITE_NAME   "/battle_sem_w"
#define SEM_READ_NAME    "/battle_sem_r"

/* Port UDP par défaut */
#define NET_PORT         9000

/* ── Types de messages réseau ────────────────────────────────────────────── */
typedef enum {
    MSG_STATE_UPDATE = 0x01,
    MSG_OWN_REQUEST  = 0x02,
    MSG_OWN_GRANT    = 0x03,
    MSG_OWN_DENY     = 0x04,
    MSG_HELLO        = 0x10,
    MSG_READY        = 0x11,
} MsgType;

/* ── État d'une unité (SHM + réseau) ─────────────────────────────────────── */
typedef struct __attribute__((packed)) {
    uint8_t  id;
    uint8_t  team;
    uint8_t  owner_peer;
    uint8_t  alive;
    uint8_t  dirty;
    uint8_t  _pad[3];
    float    x;
    float    y;
    uint16_t hp;
    uint16_t hp_max;
} UnitState;

/* ── État global du jeu partagé via SHM ──────────────────────────────────── */
typedef struct __attribute__((packed)) {
    uint32_t  magic;
    uint16_t  version;
    uint8_t   unit_count;
    uint8_t   my_peer_id;
    uint32_t  tick;
    uint8_t   both_ready;    /* 0 = en attente, 1 = handshake terminé */
    uint8_t   python_ready;  /* 0 = Python pas prêt, 1 = Python prêt   */
    uint8_t   _pad[2];
    UnitState units[MAX_UNITS];
} GameState;

/* ── Message réseau UDP ──────────────────────────────────────────────────── */
typedef struct __attribute__((packed)) {
    uint32_t  magic;
    uint8_t   type;
    uint8_t   sender_id;
    uint16_t  unit_id;
    UnitState unit;
} NetMessage;

/* ── API protocole C ─────────────────────────────────────────────────────── */
void proto_set_expected_peers(int n);
void proto_handle_incoming(const NetMessage *msg, GameState *local_state);
int  proto_handshake_done(void);
void proto_send_hello(uint8_t my_peer_id);
void proto_tick_handshake(const NetMessage *msg, GameState *state);

#endif /* PROTOCOL_H */
