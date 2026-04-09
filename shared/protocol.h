#ifndef MBAI_SHARED_PROTOCOL_H
#define MBAI_SHARED_PROTOCOL_H

/*
 * Minimal shared protocol for the v1 IPC bridge.
 *
 * Keep this file simple:
 * - fixed-size arrays only
 * - no pointers
 * - only the fields needed to mirror units and ownership
 */

#include <stddef.h>
#include <stdint.h>

#if defined(__cplusplus)
#define MBAI_STATIC_ASSERT(cond, msg) static_assert((cond), msg)
#elif defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
#define MBAI_STATIC_ASSERT(cond, msg) _Static_assert((cond), msg)
#else
#define MBAI_STATIC_ASSERT(cond, msg)
#endif

#define MBAI_PROTOCOL_MAGIC   0x4D424149u  /* "MBAI" */
#define MBAI_PROTOCOL_VERSION 1u

#define MBAI_SHM_NAME         "/mbai_game_state"
#define MBAI_STATE_SEM_NAME   "/mbai_state_sem"

#define MBAI_MAX_UNITS        1024u
#define MBAI_NO_PEER          0xFFu

#define MBAI_UNIT_UNKNOWN     0u
#define MBAI_UNIT_CROSSBOW    'C'
#define MBAI_UNIT_KNIGHT      'K'
#define MBAI_UNIT_LIGHT_CAVALRY 'L'
#define MBAI_UNIT_PIKEMAN     'P'
#define MBAI_UNIT_SKIRMISHER  'S'

typedef struct mbai_unit_state_s {
    uint32_t unit_id;
    float x;
    float y;
    float hp;
    float max_hp;
    uint8_t unit_type;
    uint8_t team_id;
    uint8_t network_owner_peer;
    uint8_t alive;
} mbai_unit_state_t;

typedef struct mbai_game_state_s {
    uint32_t magic;
    uint32_t version;
    uint32_t header_size;
    uint32_t total_size;
    uint32_t unit_count;
    uint32_t max_units;
    uint32_t map_width;
    uint32_t map_height;
    uint32_t local_peer_id;
    mbai_unit_state_t units[MBAI_MAX_UNITS];
} mbai_game_state_t;

MBAI_STATIC_ASSERT(sizeof(mbai_unit_state_t) == 24u, "mbai_unit_state_t size mismatch");
MBAI_STATIC_ASSERT(offsetof(mbai_game_state_t, units) == 36u, "mbai_game_state_t header size mismatch");
MBAI_STATIC_ASSERT(sizeof(mbai_game_state_t) == (24u * MBAI_MAX_UNITS + 36u), "mbai_game_state_t size mismatch");

#undef MBAI_STATIC_ASSERT

#endif /* MBAI_SHARED_PROTOCOL_H */
