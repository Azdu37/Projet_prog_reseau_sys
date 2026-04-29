/*
 * protocol.h — Définitions du protocole réseau + structure IPC partagée
 *
 * CE FICHIER EST LA SOURCE DE VÉRITÉ.
 * Toute modification doit être répercutée dans network_bridge.py (ctypes).
 *
 * Handshake (V3) :
 *   1. Chaque pair envoie MSG_HELLO dès qu'il est prêt.
 *   2. Quand un pair a reçu MSG_HELLO de tous les pairs attendus,
 *      il répond MSG_READY et positionne both_ready=1 dans la SHM.
 *   3. Python attend both_ready==1 avant de lancer game_loop().
 */

#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

/* ── Constantes ────────────────────────────────────────────────────────────── */
#define PROTOCOL_MAGIC   0xBABA1234u
#define PROTOCOL_VERSION 1
#define MAX_UNITS        256
#define MAX_PEERS        8

/* Noms IPC — doivent correspondre à network_bridge.py */
#define SHM_NAME       "/battle_state"
#define SEM_WRITE_NAME "/battle_sem_w"
#define SEM_READ_NAME  "/battle_sem_r"

/* ── Types de messages réseau ──────────────────────────────────────────────── */
typedef enum {
    MSG_STATE_UPDATE = 0x01,   /* Mise à jour d'état d'une unité           */
    MSG_OWN_REQUEST  = 0x02,   /* Demande de propriété d'une unité         */
    MSG_OWN_GRANT    = 0x03,   /* Accord de propriété                      */
    MSG_OWN_DENY     = 0x04,   /* Refus de propriété                       */
    MSG_HELLO        = 0x10,   /* "Je suis prêt, attendez-moi"             */
    MSG_READY        = 0x11,   /* "J'ai reçu ton HELLO, on peut commencer" */
} MsgType;

/* ── État d'une unité (SHM + réseau) ───────────────────────────────────────── */
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

/* ── État global partagé via SHM ────────────────────────────────────────────
 *
 *  both_ready : mis à 1 par le processus C quand le handshake est terminé.
 *               Python le poll avant de lancer la boucle de jeu.
 *               Valeurs :
 *                 0 = en attente de connexion
 *                 1 = tous les pairs connectés, la partie peut commencer
 */
typedef struct __attribute__((packed)) {
    uint32_t  magic;
    uint16_t  version;
    uint8_t   unit_count;
    uint8_t   my_peer_id;
    uint32_t  tick;
    uint8_t   both_ready;   /* ← NOUVEAU : 0=attente, 1=go */
    uint8_t   _pad[3];
    UnitState units[MAX_UNITS];
} GameState;

/* ── Message réseau UDP ─────────────────────────────────────────────────────── */
typedef struct __attribute__((packed)) {
    uint32_t  magic;
    uint8_t   type;        /* MsgType */
    uint8_t   sender_id;
    uint16_t  unit_id;
    UnitState unit;
} NetMessage;

/* ── Prototypes ─────────────────────────────────────────────────────────────── */
void proto_handle_incoming(const NetMessage *msg, GameState *local_state);

/* Appelé par main.c pour savoir si le handshake est terminé */
int  proto_handshake_done(void);

/* Démarre la phase de handshake (envoie MSG_HELLO à tous les pairs) */
void proto_send_hello(uint8_t my_peer_id);

/* À appeler périodiquement jusqu'à ce que proto_handshake_done() == 1 */
void proto_tick_handshake(const NetMessage *msg, GameState *state);

#endif /* PROTOCOL_H */
