#ifndef MBAI_SHARED_PROTOCOL_H
#define MBAI_SHARED_PROTOCOL_H

/*
 * Shared protocol between the C runtime and the Python battle engine.
 *
 * This file is the single source of truth for the in-memory snapshot exchanged
 * through shared memory. The Python side must mirror these definitions exactly
 * with ctypes structures using `_pack_ = 1`.
 *
 * Design goals for v1:
 * - fixed-size records only
 * - no pointers, no variable-length payloads
 * - explicit ownership fields to model "propriete reseau" from the project spec
 * - enough state to render and reason on remote units
 */

#include <stdint.h>

#define MBAI_PROTOCOL_MAGIC        0x4D424149u  /* "MBAI" */
#define MBAI_PROTOCOL_VERSION      1u

/* IPC objects shared by the C side and the Python side. */
#define MBAI_SHM_NAME              "/mbai_game_state"
#define MBAI_STATE_SEM_NAME        "/mbai_state_sem"

/*
 * Sizing choices:
 * - current scenarios top out at a few hundred mirrored units
 * - 1024 leaves headroom for multiplayer growth without exploding shared memory
 */
#define MBAI_MAX_UNITS             1024u
#define MBAI_INVALID_UNIT_ID       0xFFFFFFFFu
#define MBAI_NO_PEER               0xFFu

/* Unit kinds from the existing Python project. */
typedef enum mbai_unit_kind_e {
    MBAI_UNIT_UNKNOWN = 0,
    MBAI_UNIT_CROSSBOW = 'C',
    MBAI_UNIT_KNIGHT = 'K',
    MBAI_UNIT_LIGHT_CAVALRY = 'L',
    MBAI_UNIT_PIKEMAN = 'P',
    MBAI_UNIT_SKIRMISHER = 'S'
} mbai_unit_kind_t;

/* Coarse gameplay state mirrored from the Python engine. */
typedef enum mbai_unit_state_e {
    MBAI_STATE_IDLE = 0,
    MBAI_STATE_MOVING = 1,
    MBAI_STATE_ATTACKING = 2,
    MBAI_STATE_RELOADING = 3,
    MBAI_STATE_DEAD = 4
} mbai_unit_state_t;

/*
 * Unit flags:
 * - ALIVE: slot contains a living unit
 * - DIRTY: local owner changed this unit since the last publication
 * - REMOTE: unit state was last refreshed from another peer
 * - OWNERSHIP_PENDING: critical handoff in progress (v2)
 */
typedef enum mbai_unit_flags_e {
    MBAI_FLAG_NONE = 0u,
    MBAI_FLAG_ALIVE = 1u << 0,
    MBAI_FLAG_DIRTY = 1u << 1,
    MBAI_FLAG_REMOTE = 1u << 2,
    MBAI_FLAG_OWNERSHIP_PENDING = 1u << 3
} mbai_unit_flags_t;

#if defined(_MSC_VER)
#pragma pack(push, 1)
#endif

#if defined(__GNUC__) || defined(__clang__)
#define MBAI_PACKED __attribute__((packed))
#else
#define MBAI_PACKED
#endif

/*
 * One network-visible unit snapshot.
 * Business ownership is represented by `team_id`.
 * Network ownership is represented by `network_owner_peer`.
 */
typedef struct MBAI_PACKED mbai_unit_state_s {
    uint32_t unit_id;
    uint32_t revision;
    uint32_t last_update_tick;
    uint32_t target_unit_id;

    float x;
    float y;
    float dest_x;
    float dest_y;

    float hp;
    float max_hp;
    float attack_cooldown_s;

    uint8_t unit_kind;
    uint8_t team_id;
    uint8_t network_owner_peer;
    uint8_t state;

    uint8_t orientation;
    uint8_t reserved0;
    uint16_t flags;
} mbai_unit_state_t;

/*
 * Whole shared-memory snapshot.
 * The header fields allow sanity checks before reading the arrays.
 */
typedef struct MBAI_PACKED mbai_game_state_s {
    uint32_t magic;
    uint16_t version;
    uint16_t header_size;
    uint32_t total_size;

    uint32_t snapshot_revision;
    uint32_t tick;
    uint32_t unit_count;
    uint32_t max_units;

    uint32_t map_width;
    uint32_t map_height;
    uint32_t local_peer_id;
    uint32_t reserved1;

    mbai_unit_state_t units[MBAI_MAX_UNITS];
} mbai_game_state_t;

#if defined(_MSC_VER)
#pragma pack(pop)
#endif

#undef MBAI_PACKED

/*
 * Expected sizes are part of the contract.
 * If one side changes the layout accidentally, compilation should fail.
 */
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
_Static_assert(sizeof(mbai_unit_state_t) == 48u, "mbai_unit_state_t size mismatch");
_Static_assert(sizeof(mbai_game_state_t) == (48u * MBAI_MAX_UNITS + 40u), "mbai_game_state_t size mismatch");
#endif

#endif /* MBAI_SHARED_PROTOCOL_H */
