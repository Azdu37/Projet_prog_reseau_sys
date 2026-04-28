#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

/* ─────────────────────────────────────────────
 * Constantes globales
 * ───────────────────────────────────────────── */
#define PROTOCOL_MAGIC   0xBABA1234u
#define PROTOCOL_VERSION 1

#define MAX_UNITS        512
#define MAX_PEERS        8

/* Noms IPC (mémoire partagée + sémaphores)
 * SEM_WRITE_NAME est utilisé comme mutex unique de la SHM en V1.
 * SEM_READ_NAME reste créé pour compatibilité avec les scripts existants.
 */
#define SHM_NAME         "/battle_state"
#define SEM_WRITE_NAME   "/battle_sem_w"
#define SEM_READ_NAME    "/battle_sem_r"

/* Port UDP par défaut */
#define NET_PORT         9000

/* ─────────────────────────────────────────────
 * État d'une unité (une case / personnage)
 * ───────────────────────────────────────────── */
typedef struct {
    uint16_t id;           /* identifiant unique de l'unité          */
    uint8_t  team;         /* 0 = équipe A, 1 = équipe B, ...        */
    uint8_t  owner_peer;   /* index du PC qui pilote l'unité en V1   */
    uint8_t  alive;        /* 1 = vivant, 0 = mort                   */
    uint8_t  dirty;        /* 1 = modifié, à envoyer sur le réseau   */
    uint8_t  _pad[2];      /* alignement 8 octets                    */
    float    x;            /* position X                             */
    float    y;            /* position Y                             */
    uint16_t hp;           /* points de vie                          */
    uint16_t hp_max;       /* points de vie maximum                  */
} UnitState;               /* taille = 20 octets                     */

/* ─────────────────────────────────────────────
 * État global du jeu (dans la mémoire partagée)
 * ───────────────────────────────────────────── */
typedef struct {
    uint32_t  magic;                /* PROTOCOL_MAGIC : détecte corruption  */
    uint16_t  version;              /* PROTOCOL_VERSION                      */
    uint16_t  unit_count;           /* nombre d'unités actives               */
    uint8_t   my_peer_id;           /* index de ce PC dans la partie         */
    uint8_t   _pad0[3];
    uint32_t  tick;                 /* horloge logique du jeu                */
    UnitState units[MAX_UNITS];     /* tableau d'unités                      */
} GameState;

/* ─────────────────────────────────────────────
 * Messages réseau (envoyés en UDP entre les C)
 * ───────────────────────────────────────────── */
typedef enum {
    MSG_STATE_UPDATE = 1,   /* V1 : mise à jour d'une unité          */
    MSG_OWN_REQUEST  = 2,   /* réservé                               */
    MSG_OWN_GRANT    = 3,   /* réservé                               */
    MSG_OWN_DENY     = 4,   /* réservé                               */
} MsgType;

typedef struct {
    uint32_t  magic;        /* PROTOCOL_MAGIC                        */
    uint8_t   type;         /* MsgType                               */
    uint8_t   sender_id;    /* index du PC émetteur                  */
    uint16_t  unit_id;      /* unité concernée                       */
    UnitState unit;         /* payload (utilisé pour STATE_UPDATE)   */
} NetMessage;

#endif /* PROTOCOL_H */
