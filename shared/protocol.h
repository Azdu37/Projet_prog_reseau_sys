#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

#define PROTOCOL_MAGIC   0xBABA1234u
#define PROTOCOL_VERSION 1

#define MAX_UNITS        256
#define MAX_PEERS        8

#define SHM_NAME         "/battle_state"
#define SEM_WRITE_NAME   "/battle_sem_w"
#define SEM_READ_NAME    "/battle_sem_r"
#define NET_PORT         9000

typedef struct {
    uint8_t  id;           
    uint8_t  team;         
    uint8_t  owner_peer;   
    uint8_t  alive;        
    uint8_t  dirty;        
    uint8_t  pending_request_from; /* V2: ID du pair demandant la propriété (255 = aucun) */
    uint8_t  _pad[2];              /* Alignement restant pour faire 20 octets */
    float    x;            
    float    y;            
    uint16_t hp;           
    uint16_t hp_max;       
} UnitState;

typedef struct {
    uint32_t  magic;                
    uint16_t  version;              
    uint8_t   unit_count;           
    uint8_t   my_peer_id;           
    uint32_t  tick;                 
    uint8_t   _pad[4];
    UnitState units[MAX_UNITS];     
} GameState;

typedef enum {
    MSG_STATE_UPDATE = 1,
    MSG_OWN_REQUEST  = 2,
    MSG_OWN_GRANT    = 3,
    MSG_OWN_DENY     = 4,
} MsgType;

typedef struct {
    uint32_t  magic;        
    uint8_t   type;         
    uint8_t   sender_id;    
    uint16_t  unit_id;      
    UnitState unit;         
} NetMessage;

#endif /* PROTOCOL_H */